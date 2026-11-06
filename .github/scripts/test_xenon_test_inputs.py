#!/usr/bin/env python3
"""Verify missing-fixture recovery without network access or compilation."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    'restore', Path(__file__).with_name('github_restore_xenon_test_inputs.py'))
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class TestInputRecoveryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.source = Path(tmp.name).resolve()
        self.package = dict(name='webui', destination='chrome/test/data/webui', format='tar.gz')
        self.files = {'chai_assert.ts': b'test source', 'BUILD.gn': b'upstream GN'}
        self.package['content_sha256'] = restore.tree_digest(self.files)

    def test_restores_original_missing_input_without_overwriting_prepared_files(self):
        gn = self.source / self.package['destination'] / 'BUILD.gn'
        gn.parent.mkdir(parents=True)
        gn.write_bytes(b'patched GN')
        obj = self.source / 'out/Default/retained.o'
        obj.parent.mkdir(parents=True)
        obj.write_bytes(b'compiled output')
        restored = restore.install(self.source, self.package, self.files)
        self.assertEqual(b'test source', gn.with_name('chai_assert.ts').read_bytes())
        self.assertEqual(b'patched GN', gn.read_bytes())
        self.assertEqual(b'compiled output', obj.read_bytes())
        self.assertEqual(1, len(restored))
        self.assertEqual({}, restore.install(self.source, self.package, self.files))

    def test_changed_archive_content_fails_before_any_write(self):
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            restore.install(self.source, self.package, dict(self.files, injected=b'other'))
        self.assertFalse((self.source / 'chrome').exists())

    def test_archive_digest_ignores_request_timestamp_but_binds_names_and_bytes(self):
        digests = []
        for timestamp in (1, 500):
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode='w:gz') as archive:
                member = tarfile.TarInfo('./chai_assert.ts')
                member.mtime = timestamp
                member.size = 4
                archive.addfile(member, io.BytesIO(b'test'))
            digests.append(restore.tree_digest(restore.unpack(data.getvalue(), 'tar.gz')))
        self.assertEqual(*digests)
        self.assertNotEqual(digests[0], restore.tree_digest({'other.ts': b'test'}))
        self.assertNotEqual(digests[0], restore.tree_digest({'chai_assert.ts': b'changed'}))

    def test_rejects_archive_traversal_and_symlink(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('link', tarfile.SYMTYPE)]:
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode='w:gz') as archive:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '/tmp/escape'
                archive.addfile(member)
            with self.assertRaises(ValueError):
                restore.unpack(data.getvalue(), 'tar.gz')

    def test_rejects_destination_symlink_and_traversal(self):
        (self.source / 'chrome').symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            restore.install(self.source, self.package, self.files)
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            restore.install(self.source, dict(self.package, destination='../escape'), self.files)

    def test_decodes_binary_file_without_changing_bytes(self):
        self.assertEqual({'payload': b'\x00\xff'}, restore.unpack(base64.b64encode(b'\x00\xff'), 'base64'))

    def test_graph_preflight_reports_missing_chai_and_does_not_compile(self):
        with mock.patch.object(subprocess, 'check_output', return_value=b'../../chrome/test/data/webui/chai_assert.ts\n') as command:
            with self.assertRaisesRegex(ValueError, 'chai_assert.ts'):
                restore.missing_inputs(self.source, ['browser_tests'])
            self.assertEqual(['-t', 'inputs', 'browser_tests'], command.call_args.args[0][-3:])

    def test_graph_preflight_handles_shell_quotes_and_generated_outputs(self):
        path = self.source / 'third_party/@test/with space.ts'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'present')
        with mock.patch.object(subprocess, 'check_output', return_value=b"'../../third_party/@test/with space.ts'\nobj/generated.o\n"):
            restore.missing_inputs(self.source, ['browser_tests'])

    def test_manifest_matches_current_version_and_pins_every_package(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        self.assertEqual((root / 'helium-chromium/chromium_version.txt').read_text().strip(), data['chromium_version'])
        for package in data['packages']:
            self.assertRegex(package['content_sha256'], r'^[a-f0-9]{64}$')
            self.assertTrue(data['chromium_revision'] in package['url'] or package['name'] == 'fonts')


if __name__ == '__main__':
    unittest.main()
