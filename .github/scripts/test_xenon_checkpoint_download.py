#!/usr/bin/env python3
"""Run checkpoint downloads in the same copied-script layout as macOS CI."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


HELPER = Path(__file__).with_name('github_xenon_fresh_checkpoint.py').resolve()


class CheckpointDownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        # Nested checkout catches the former parents[2] calculation escaping it.
        self.root = self.base / 'work/repo/repo'
        self.scripts = self.root / '.github/scripts'
        self.scripts.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        shutil.copyfile(HELPER, self.scripts / HELPER.name)
        shutil.copyfile(HELPER, self.root / HELPER.name)
        self.bundle = self.base / 'artifact.zip'
        self.payload = b'checkpoint contents'
        self.make_zip()
        self.policy = {
            'source_run': '123', 'checkpoint_artifact_id': '456',
            'checkpoint_artifact_sha256': hashlib.sha256(self.bundle.read_bytes()).hexdigest(),
        }
        self.write_policy()
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        gh = self.bin / 'gh'
        gh.write_text('#!/bin/sh\n'
                      'if [ "$CHECKPOINT_TEST_FAIL" = 1 ]; then exit 9; fi\n'
                      'if [ "$1" = api ]; then cat "$CHECKPOINT_TEST_ZIP"; else\n'
                      'pwd > "$CHECKPOINT_TEST_CWD"\n'
                      'printf "%s\\n" "$@" > "$CHECKPOINT_TEST_ARGS"\nfi\n')
        gh.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        GITHUB_REPOSITORY='example/repo', SOURCE_RUN='123', TARGET_ARCH='arm64',
                        CHECKPOINT_TEST_ZIP=str(self.bundle), CHECKPOINT_TEST_FAIL='0',
                        CHECKPOINT_TEST_CWD=str(self.base / 'cwd'),
                        CHECKPOINT_TEST_ARGS=str(self.base / 'args'),
                        PYTHONDONTWRITEBYTECODE='1')

    def make_zip(self, names=('build_src.tar.zst', 'sums.txt')):
        with zipfile.ZipFile(self.bundle, 'w') as bundle:
            for name in names:
                bundle.writestr(name, self.payload)

    def write_policy(self):
        (self.root / '.github/arc-checkpoint-delta.json').write_text(json.dumps(self.policy))

    def run_download(self, inline=False):
        if inline:
            command = [sys.executable, '-c',
                       'from github_xenon_fresh_checkpoint import download_arc; '
                       'download_arc("123", "arm64")']
        else:
            command = [sys.executable, str(self.scripts / HELPER.name), 'download-arc']
        return subprocess.run(command, cwd=self.root, env=self.env,
                              text=True, capture_output=True)

    def assert_extracted_in_checkout(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ('build_src.tar.zst', 'sums.txt'):
            self.assertEqual((self.root / name).read_bytes(), self.payload)
            self.assertFalse((self.root.parent / name).exists())
            self.assertFalse((self.root.parent.parent / name).exists())

    def test_workflow_cli_extracts_into_checkout(self):
        self.assert_extracted_in_checkout(self.run_download())

    def test_inline_import_of_root_copy_extracts_into_same_checkout(self):
        self.env['PYTHONPATH'] = str(self.scripts)
        self.assert_extracted_in_checkout(self.run_download(inline=True))

    def test_wrong_zip_digest_leaves_existing_checkpoint_untouched(self):
        (self.root / 'sums.txt').write_bytes(b'existing')
        self.policy['checkpoint_artifact_sha256'] = '0' * 64
        self.write_policy()
        result = self.run_download()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ZIP hash differs', result.stderr)
        self.assertEqual((self.root / 'sums.txt').read_bytes(), b'existing')
        self.assertFalse((self.root / 'build_src.tar.zst').exists())

    def test_incomplete_zip_does_not_publish_partial_checkpoint(self):
        self.make_zip(('build_src.tar.zst',))
        self.policy['checkpoint_artifact_sha256'] = hashlib.sha256(self.bundle.read_bytes()).hexdigest()
        self.write_policy()
        result = self.run_download()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('exactly one sums.txt', result.stderr)
        self.assertFalse((self.root / 'build_src.tar.zst').exists())

    def test_unrelated_archive_members_are_never_extracted(self):
        self.make_zip(('build_src.tar.zst', 'sums.txt', '../escaped', 'other'))
        self.policy['checkpoint_artifact_sha256'] = hashlib.sha256(self.bundle.read_bytes()).hexdigest()
        self.write_policy()
        self.assert_extracted_in_checkout(self.run_download())
        self.assertFalse((self.root.parent / 'escaped').exists())
        self.assertFalse((self.root / 'other').exists())

    def test_download_error_fails_before_extraction(self):
        self.env['CHECKPOINT_TEST_FAIL'] = '1'
        result = self.run_download()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('exit status 9', result.stderr)
        self.assertFalse((self.root / 'sums.txt').exists())

    def test_unpinned_run_downloads_in_checkout(self):
        self.env['SOURCE_RUN'] = '789'
        result = self.run_download()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path((self.base / 'cwd').read_text().strip()).resolve(), self.root.resolve())
        self.assertEqual((self.base / 'args').read_text().splitlines(),
                         ['run', 'download', '789', '--name', 'github_build_artifact_arm64'])


if __name__ == '__main__':
    unittest.main()
