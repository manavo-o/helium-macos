#!/usr/bin/env python3
"""Test the fresh-regression gate without compiling or launching a browser."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    'xenon_tests', Path(__file__).with_name('github_run_xenon_tests.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FreshRegressionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'build/src/out/Default'
        self.output.mkdir(parents=True)
        (self.root / 'build/src/example.cc').write_bytes(b'audited code')
        digest = hashlib.sha256(b'audited code').hexdigest()
        self.data = dict(test_plan=runner.PLAN, patches=[dict(sha256='patch')],
                         sources={'example.cc': dict(before='old', after=digest)})
        self.stamp = self.output / 'xenon-regressions.json'
        repo = Path(__file__).resolve().parents[2]
        for relative in ('.github/xenon-test-inputs.json',
                         '.github/scripts/github_restore_xenon_test_inputs.py'):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / relative, target)

    def summary(self):
        return {'per_iteration_data': [{name: [dict(status='SUCCESS')]
                                        for name in runner.REQUIRED_BROWSER_TESTS}]}

    def test_signature_rejects_changed_source(self):
        runner.signature(self.root, self.data, 'arm64')
        (self.root / 'build/src/example.cc').write_text('different')
        with self.assertRaisesRegex(ValueError, 'audited delta'):
            runner.signature(self.root, self.data, 'arm64')

    def test_signature_binds_test_input_manifest(self):
        before = runner.signature(self.root, self.data, 'arm64')
        (self.root / '.github/xenon-test-inputs.json').write_text('different fixture policy')
        self.assertNotEqual(before, runner.signature(self.root, self.data, 'arm64'))

    def test_signature_rejects_unknown_plan(self):
        self.data['test_plan'] = 'skip-tests'
        with self.assertRaises(ValueError):
            runner.signature(self.root, self.data, 'arm64')

    def test_signature_binds_architecture(self):
        self.assertNotEqual(runner.signature(self.root, self.data, 'arm64'),
                            runner.signature(self.root, self.data, 'x86_64'))

    def test_stamp_rejects_missing_corrupt_stale_or_empty_result(self):
        self.assertFalse(runner.valid_stamp(self.stamp, 'expected'))
        for content in ['invalid', '[]', '{}', '{"signature":"old"}',
                        '{"signature":"expected","routing":5,"bubble":1}']:
            self.stamp.write_text(content)
            self.assertFalse(runner.valid_stamp(self.stamp, 'expected'))

    def test_browser_summary_requires_every_critical_test(self):
        summary = self.summary()
        del summary['per_iteration_data'][0][next(iter(runner.REQUIRED_BROWSER_TESTS))]
        path = self.root / 'summary.json'
        path.write_text(json.dumps(summary))
        with self.assertRaisesRegex(ValueError, 'did not run'):
            runner.verify_browser_summary(path)

    def test_browser_summary_rejects_failures_and_retries(self):
        for attempts in [[dict(status='FAILURE')],
                         [dict(status='FAILURE'), dict(status='SUCCESS')]]:
            summary = self.summary()
            summary['per_iteration_data'][0][next(iter(runner.REQUIRED_BROWSER_TESTS))] = attempts
            path = self.root / 'summary.json'
            path.write_text(json.dumps(summary))
            with self.assertRaisesRegex(ValueError, 'first attempt'):
                runner.verify_browser_summary(path)

    def run_suite(self, fail=False):
        for name in ['browser_tests', 'arc_routing_tests', 'arc_bubble_lifecycle_tests']:
            (self.output / name).write_text('fixture executable')

        def execute(command, **kwargs):
            binary = Path(command[0]).name
            if binary == 'browser_tests':
                summary = next(arg.split('=', 1)[1] for arg in command
                               if arg.startswith('--test-launcher-summary-output='))
                Path(summary).write_text(json.dumps(self.summary()))
            count = 5 if binary == 'arc_routing_tests' else 2
            return subprocess.CompletedProcess(command, 1 if fail else 0,
                                               stdout=f'[  PASSED  ] {count} tests.\n', stderr='')

        with mock.patch.object(runner.subprocess, 'run', side_effect=execute):
            runner.run_tests(self.root, 'arm64', 'expected', self.stamp)

    def test_success_writes_bound_stamp_only_after_all_suites(self):
        self.run_suite()
        self.assertTrue(runner.valid_stamp(self.stamp, 'expected'))
        self.assertFalse(runner.valid_stamp(self.stamp, 'another-source'))

    def test_failure_removes_previous_stamp(self):
        self.stamp.write_text('{"signature":"old"}')
        with self.assertRaisesRegex(ValueError, 'failed'):
            self.run_suite(fail=True)
        self.assertFalse(self.stamp.exists())


if __name__ == '__main__':
    unittest.main()
