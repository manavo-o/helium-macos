#!/usr/bin/env python3
"""Exercise phase deadlines without invoking a compiler or downloading tools."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('github_build.sh')


class PhaseBudgetTest(unittest.TestCase):
    def run_phase(self, elapsed, result, advance_deadline=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / 'devutils').mkdir()
        (root / 'src').mkdir()
        (root / 'bin').mkdir()
        shutil.copyfile(SCRIPT, root / 'github_build.sh')
        (root / 'epoch_job_start.txt').write_text('1000')
        (root / 'devutils/shared.sh').write_text(
            '_src_dir="$_root_dir/src"\n_out_dir="$_src_dir/out/Default"\n'
            '_depot_tools_dir="$_src_dir/third_party/depot_tools"\n'
            '_siso_path="$_src_dir/third_party/siso/cipd/siso"\n')
        (root / 'clock').write_text(str(1000 + elapsed))
        programs = {
            'greadlink': '#!/bin/sh\n' + 'echo "' + str(root / 'github_build.sh') + '"\n',
            'date': '#!/bin/sh\ncat "' + str(root / 'clock') + '"\n',
            'timeout': '#!/bin/sh\nprintf "%s\\n" "$@" > "' + str(root / 'timeout-args') + '"\nexit ' + str(result) + '\n',
        }
        if advance_deadline:
            programs['timeout'] = programs['timeout'].replace(
                'exit ' + str(result),
                'echo 17200 > "' + str(root / 'clock') + '"\nexit ' + str(result))
        for name, text in programs.items():
            path = root / 'bin' / name
            path.write_text(text)
            path.chmod(0o755)
        env = dict(os.environ, PATH=str(root / 'bin') + ':' + os.environ['PATH'],
                   GITHUB_OUTPUT=str(root / 'output'), SCCACHE_GHA_ENABLED='on')
        completed = subprocess.run(['bash', '-eux', str(root / 'github_build.sh'), 'arm64'],
                                   env=env, capture_output=True, text=True, timeout=5)
        return root, completed

    def test_expired_budget_saves_without_starting_compiler(self):
        root, result = self.run_phase(271 * 60, 0)
        self.assertEqual(0, result.returncode)
        self.assertFalse((root / 'timeout-args').exists())
        self.assertEqual('status=running\n', (root / 'output').read_text())

    def test_deadline_is_remaining_elapsed_time_not_another_full_phase(self):
        root, result = self.run_phase(60 * 60, 124)
        self.assertEqual(0, result.returncode)
        self.assertIn('12600s', (root / 'timeout-args').read_text())
        self.assertFalse((root / 'build_finished_arm64.log').exists())
        self.assertEqual('status=running\n', (root / 'output').read_text())

    def test_compiler_failure_remains_a_failure(self):
        root, result = self.run_phase(0, 42)
        self.assertEqual(42, result.returncode)
        self.assertFalse((root / 'build_finished_arm64.log').exists())

    def test_only_browser_and_packaging_targets_are_requested(self):
        root, _ = self.run_phase(0, 124)
        targets = (root / 'timeout-args').read_text().splitlines()
        self.assertEqual(['chrome', 'chrome/installer/mac'], targets[-2:])
        self.assertNotIn('chromedriver', targets)

    def test_forced_stop_at_deadline_remains_resumable(self):
        root, result = self.run_phase(0, 137, advance_deadline=True)
        self.assertEqual(0, result.returncode)
        self.assertEqual('status=running\n', (root / 'output').read_text())

    def test_early_killed_compiler_is_not_hidden_as_a_timeout(self):
        _, result = self.run_phase(0, 137)
        self.assertEqual(137, result.returncode)

    def test_completion_requires_successful_compilation(self):
        root, result = self.run_phase(0, 0)
        self.assertEqual(0, result.returncode)
        self.assertTrue((root / 'build_finished_arm64.log').exists())
        self.assertIn('status=finished', (root / 'output').read_text())


if __name__ == '__main__':
    unittest.main()
