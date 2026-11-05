#!/usr/bin/env python3
"""Check that cache reuse cannot silently validate changed application code."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    'cached', Path(__file__).with_name('github_run_arc_cached_tests.py'))
cached = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cached)


class CachedTestPolicy(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = next(iter(cached.LINK_ONLY_OUTPUTS))
        source = self.root / 'build/src' / self.path
        source.parent.mkdir(parents=True)
        source.write_bytes(b'known link-only input')
        self.digest = hashlib.sha256(source.read_bytes()).hexdigest()
        self.policy = mock.patch.object(cached, 'LINK_ONLY_OUTPUTS', {self.path: self.digest})
        self.policy.start()
        self.addCleanup(self.policy.stop)
        self.data = {'source_run': cached.BASELINE_RUN, 'sources': {
            self.path: {'before': 'old', 'after': self.digest}}}

    def test_accepts_known_unchanged_test_checkpoint(self):
        cached.validate_reuse(self.root, self.data)

    def test_rejects_changed_cpp_source(self):
        self.data['sources']['chrome/browser/new.cc'] = {'before': 'old', 'after': 'new'}
        with self.assertRaisesRegex(ValueError, 'fresh regression tests'):
            cached.validate_reuse(self.root, self.data)

    def test_rejects_different_gn_change(self):
        self.data['sources'][self.path]['after'] = 'unreviewed'
        with self.assertRaisesRegex(ValueError, 'previously audited'):
            cached.validate_reuse(self.root, self.data)

    def test_rejects_changed_restored_file(self):
        (self.root / 'build/src' / self.path).write_bytes(b'wrong source')
        with self.assertRaisesRegex(ValueError, 'Restored source'):
            cached.validate_reuse(self.root, self.data)

    def test_rejects_unproven_checkpoint(self):
        self.data['source_run'] = 'different-run'
        with self.assertRaisesRegex(ValueError, 'evidence belongs'):
            cached.validate_reuse(self.root, self.data)

    def test_accepts_expected_passing_summary(self):
        cached.validate_test_count('[  PASSED  ] 5 tests.', 5)

    def test_rejects_success_with_zero_tests(self):
        with self.assertRaises(ValueError):
            cached.validate_test_count('[  PASSED  ] 0 tests.', 5)

    def test_rejects_missing_test_results(self):
        with self.assertRaises(ValueError):
            cached.validate_test_count('launcher exited without running tests', 5)


if __name__ == '__main__':
    unittest.main()
