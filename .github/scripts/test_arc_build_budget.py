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
    def run_phase(self, elapsed, result, advance_deadline=False, plan=None, stamp_result=1, restore_result=0):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / 'devutils').mkdir()
        (root / 'src').mkdir()
        (root / 'bin').mkdir()
        shutil.copyfile(SCRIPT, root / 'github_build.sh')
        (root / 'epoch_job_start.txt').write_text('1000')
        if plan is not None:
            import json
            (root / '.github/scripts').mkdir(parents=True)
            (root / '.github/arc-checkpoint-delta.json').write_text(json.dumps({'test_plan': plan}))
            (root / '.github/scripts/github_run_xenon_tests.py').write_text(
                'import sys\n'
                'sys.exit(' + str(stamp_result) + ' if "--check-stamp" in sys.argv else 0)\n')
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
        programs['timeout'] = programs['timeout'].replace(
            '#!/bin/sh\n',
            '#!/bin/sh\ncase "$*" in *github_restore_xenon_test_inputs.py*) '
            'echo restored > "' + str(root / 'restoration-called') + '"; exit ' + str(restore_result) + ';; esac\n')
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

    def test_fresh_test_compilation_deadline_saves_without_browser_build(self):
        root, result = self.run_phase(0, 124, plan='xenon-native-v1')
        self.assertEqual(0, result.returncode)
        targets = (root / 'timeout-args').read_text()
        self.assertIn('browser_tests', targets)
        self.assertIn('ui/views:arc_bubble_lifecycle_tests', targets)
        self.assertNotIn('chrome/installer/mac', targets)
        self.assertFalse((root / 'build_finished_arm64.log').exists())

    def test_test_input_restore_failure_stops_compilation(self):
        root, result = self.run_phase(0, 0, plan='xenon-native-v1', restore_result=42)
        self.assertEqual(42, result.returncode)
        self.assertTrue((root / 'restoration-called').exists())
        self.assertFalse((root / 'timeout-args').exists())
        self.assertFalse((root / 'build_finished_arm64.log').exists())

    def test_test_input_restore_deadline_remains_resumable(self):
        root, result = self.run_phase(0, 0, plan='xenon-native-v1', restore_result=124)
        self.assertEqual(0, result.returncode)
        self.assertFalse((root / 'build_finished_arm64.log').exists())

    def test_fresh_test_compiler_failure_stops_browser_build(self):
        root, result = self.run_phase(0, 42, plan='xenon-native-v1')
        self.assertEqual(42, result.returncode)
        self.assertFalse((root / 'build_finished_arm64.log').exists())

    def test_invalid_source_stamp_check_stops_before_compilation(self):
        root, result = self.run_phase(0, 0, plan='xenon-native-v1', stamp_result=2)
        self.assertEqual(2, result.returncode)
        self.assertFalse((root / 'timeout-args').exists())

    def test_matching_test_stamp_can_continue_browser_build(self):
        root, result = self.run_phase(0, 0, plan='xenon-native-v1', stamp_result=0)
        self.assertEqual(0, result.returncode)
        self.assertEqual(['chrome', 'chrome/installer/mac'],
                         (root / 'timeout-args').read_text().splitlines()[-2:])

    def test_runner_success_without_passing_stamp_cannot_build_browser(self):
        root, result = self.run_phase(0, 0, plan='xenon-native-v1', stamp_result=1)
        self.assertEqual(1, result.returncode)
        self.assertFalse((root / 'build_finished_arm64.log').exists())
        self.assertNotIn('chrome/installer/mac', (root / 'timeout-args').read_text())

    def test_unknown_validation_plan_cannot_bypass_tests(self):
        root, result = self.run_phase(0, 0, plan='skip-tests')
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((root / 'timeout-args').exists())


if __name__ == '__main__':
    unittest.main()
