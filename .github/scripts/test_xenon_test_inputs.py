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

    def test_avatar_adaptation_matches_pinned_helium_interface_and_is_idempotent(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        item = data['adaptations'][0]
        original = (root / '.github/checkpoint-preimages/xenon-test-fixtures/cr_profile_avatar_selector_test.ts').read_bytes()
        self.assertEqual(item['before_sha256'], restore.digest(original))
        path = self.source / item['path']
        path.parent.mkdir(parents=True)
        path.write_bytes(original)
        records = restore.adapt_fixtures(self.source, [item])
        result = path.read_bytes()
        self.assertEqual(item['after_sha256'], restore.digest(result))
        self.assertEqual(5, result.count(b'isCustomAvatar: false,'))
        self.assertEqual(5, result.count(b'isPlaceholder: false,'))
        # Only add the two stock-avatar flags, preserving every assertion and
        # all selection values in the Chromium fixture.
        self.assertEqual(original, result.replace(
            b'        isCustomAvatar: false,\n        isPlaceholder: false,\n', b''))
        self.assertEqual(records, restore.adapt_fixtures(self.source, [item]))

    def test_all_avatar_fixtures_have_verified_preimages_and_preserve_selection(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        avatars = [item for item in data['adaptations'] if any(
            'isCustomAvatar: false,' in replacement['after']
            for replacement in item['replacements'])]
        self.assertEqual(4, len(avatars))
        for item in avatars:
            original = (root / item['preimage']).read_bytes()
            self.assertEqual(item['before_sha256'], restore.digest(original))
            path = self.source / item['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original)
        restore.adapt_fixtures(self.source, avatars)
        total = 0
        for item in avatars:
            before = (root / item['preimage']).read_text()
            after = (self.source / item['path']).read_text()
            self.assertEqual(item['after_sha256'], restore.digest(after.encode()))
            self.assertEqual(before.count('selected: true'), after.count('selected: true'))
            self.assertEqual(before.count('selected: false'), after.count('selected: false'))
            self.assertEqual(before.count('isGaiaAvatar: true'), after.count('isGaiaAvatar: true'))
            self.assertEqual(before.count('isGaiaAvatar:'), after.count('isCustomAvatar: false'))
            total += after.count('isCustomAvatar: false')
        self.assertEqual(14, total)
        settings = (self.source / 'chrome/test/data/webui/settings/people_page_manage_profile_test.ts').read_text()
        self.assertIn("this.methodCalled('setCustomAvatarFromFile', dataUrl)", settings)

    def test_history_fixture_checks_removed_control_and_keeps_route_assertions(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        item = next(item for item in data['adaptations'] if '/history/' in item['path'])
        original = (root / item['preimage']).read_bytes()
        self.assertEqual(item['before_sha256'], restore.digest(original))
        path = self.source / item['path']
        path.parent.mkdir(parents=True)
        path.write_bytes(original)
        restore.adapt_fixtures(self.source, [item])
        result = path.read_text()
        self.assertNotIn('sidebar.$.syncedTabs', result)
        self.assertEqual(4, result.count("assertNull(sidebar.shadowRoot.querySelector('#syncedTabs'))"))
        self.assertEqual(3, result.count("navigateTo('/syncedTabs' + window.location.search, app)"))
        self.assertEqual(original.count(b'test('), result.count('test('))
        self.assertEqual(original.count(b'assertEquals('), result.count('assertEquals('))
        self.assertIn("'chrome://history/syncedTabs?q=' + searchTerm", result)
        self.assertIn("'chrome://history/?q=' + searchTerm", result)
        self.assertEqual(item['after_sha256'], restore.digest(result.encode()))

    def test_extensions_fixture_checks_removed_promotion_and_keeps_navigation(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        item = next(item for item in data['adaptations'] if '/extensions/' in item['path'])
        original = (root / item['preimage']).read_bytes()
        self.assertEqual(item['before_sha256'], restore.digest(original))
        path = self.source / item['path']
        path.parent.mkdir(parents=True)
        path.write_bytes(original)
        records = restore.adapt_fixtures(self.source, [item])
        result = path.read_text()
        self.assertNotIn('sidebar.$.moreExtensions', result)
        self.assertEqual(2, result.count("assertFalse(!!sidebar.shadowRoot.querySelector('#moreExtensions'))"))
        for marker in ('test(', 'assertEquals(', 'assertDeepEquals(', "eventToPromise('close-drawer'"):
            self.assertEqual(original.decode().count(marker), result.count(marker))
        for route in ('Page.SHORTCUTS', 'Page.LIST', 'Page.SITE_PERMISSIONS'):
            self.assertIn(route, result)
        self.assertEqual(item['after_sha256'], restore.digest(result.encode()))
        self.assertEqual(records, restore.adapt_fixtures(self.source, [item]))

    def test_adaptation_rejects_unknown_source_without_replacing_it(self):
        path = self.source / 'example.ts'
        path.write_bytes(b'unexpected')
        with self.assertRaisesRegex(ValueError, 'preimage'):
            restore.adapt_fixtures(self.source, [dict(path='example.ts',
                before_sha256=restore.digest(b'before'), after_sha256=restore.digest(b'after'))])
        self.assertEqual(b'unexpected', path.read_bytes())

    def test_all_pinned_fixtures_and_intermediate_checkpoint_migrate_exactly(self):
        root = Path(__file__).resolve().parents[2]
        items = json.loads((root / '.github/xenon-test-inputs.json').read_text())['adaptations']
        for item in items:
            original = (root / item['preimage']).read_bytes()
            self.assertEqual(item['before_sha256'], restore.digest(original))
            path = self.source / item['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            intermediate = item.get('intermediate')
            if intermediate:
                # Reproduce the exact previously committed adaptation retained
                # by the checkpoint, rather than trusting an arbitrary stamp.
                for change in item['replacements'][:intermediate['replacements_applied']]:
                    original = original.replace(change['before'].encode(), change['after'].encode())
                self.assertEqual(intermediate['sha256'], restore.digest(original))
            path.write_bytes(original)
        records = restore.adapt_fixtures(self.source, items)
        for item in items:
            result = (self.source / item['path']).read_bytes()
            self.assertEqual(item['after_sha256'], restore.digest(result))
            self.assertTrue(result.startswith((b'// Copyright', b'/*\n * Copyright', b'/*\r\n * Copyright')))
        self.assertEqual(records, restore.adapt_fixtures(self.source, items))

    def test_appearance_fixture_uses_supported_upload_and_preserves_theme_cases(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        item = next(item for item in data['adaptations'] if item['path'].endswith('/appearance_test.ts'))
        original = (root / item['preimage']).read_bytes()
        self.assertEqual(item['before_sha256'], restore.digest(original))
        path = self.source / item['path']
        path.parent.mkdir(parents=True)
        path.write_bytes(original)
        records = restore.adapt_fixtures(self.source, [item])
        result = path.read_text()
        for member in ('uploadedImageButton', 'searchedImageButton'):
            self.assertNotIn('appearanceElement.$.' + member, result)
            self.assertIn("querySelector('#" + member + "')", result)
        self.assertEqual(original.count(b'test('), result.count('test('))
        self.assertEqual(3, result.count("assertEquals(1, handler.getCallCount('chooseLocalCustomBackground'))"))
        for member in ('themeSnapshot', 'chromeColors', 'setClassicChromeButton'):
            self.assertEqual(original.decode().count('appearanceElement.$.' + member),
                             result.count('appearanceElement.$.' + member))
        self.assertEqual(records, restore.adapt_fixtures(self.source, [item]))

    def test_sync_test_support_fixtures_remove_obsolete_virtual_override(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        sync_items = [item for item in data['adaptations'] if 'components/sync/test/' in item['path']]
        self.assertEqual(2, len(sync_items))
        for item in sync_items:
            original = (root / item['preimage']).read_bytes()
            self.assertEqual(item['before_sha256'], restore.digest(original))
            path = self.source / item['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original)
        restore.adapt_fixtures(self.source, sync_items)
        test_h = (self.source / 'components/sync/test/test_sync_service.h').read_text()
        self.assertNotIn('bool IsLocalSyncEnabled() const override;', test_h)
        self.assertIn('bool IsLocalSyncEnabled() const;', test_h)
        mock_h = (self.source / 'components/sync/test/mock_sync_service.h').read_text()
        self.assertNotIn('MOCK_METHOD(bool, IsLocalSyncEnabled, (), (const override));', mock_h)
        self.assertIn('MOCK_METHOD(bool, IsLocalSyncEnabled, (), (const));', mock_h)

    def test_dummy_page_holder_passes_noise_tokens(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        item = next(item for item in data['adaptations'] if item['path'].endswith('dummy_page_holder.cc'))
        original = (root / item['preimage']).read_bytes()
        self.assertEqual(item['before_sha256'], restore.digest(original))
        path = self.source / item['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original)
        restore.adapt_fixtures(self.source, [item])
        result = path.read_text()
        self.assertIn('/*noise_tokens=*/{}', result)
        self.assertEqual(item['after_sha256'], restore.digest(result.encode()))

    def test_test_page_broadcast_implements_noise_tokens(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        for path_suffix in ('test_page_broadcast.h', 'test_page_broadcast.cc'):
            item = next(item for item in data['adaptations'] if item['path'].endswith(path_suffix))
            original = (root / item['preimage']).read_bytes()
            self.assertEqual(item['before_sha256'], restore.digest(original))
            path = self.source / item['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original)
            restore.adapt_fixtures(self.source, [item])
            result = path.read_text()
            self.assertIn('UpdateHeliumNoiseTokens', result)
            self.assertEqual(item['after_sha256'], restore.digest(result.encode()))

    def test_testing_browser_process_guards_safe_browsing_and_drops_override(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        for path_suffix in ('testing_browser_process.h', 'testing_browser_process.cc'):
            item = next(item for item in data['adaptations'] if item['path'].endswith(path_suffix))
            original = (root / item['preimage']).read_bytes()
            self.assertEqual(item['before_sha256'], restore.digest(original))
            path = self.source / item['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original)
            restore.adapt_fixtures(self.source, [item])
            result = path.read_text()
            self.assertIn('#if BUILDFLAG(SAFE_BROWSING_AVAILABLE)', result)
            self.assertEqual(item['after_sha256'], restore.digest(result.encode()))
        h_text = (self.source / 'chrome/test/base/testing_browser_process.h').read_text()
        self.assertNotIn('speech_recognition_small_expert_model_installer() override;', h_text)
        self.assertIn('speech_recognition_small_expert_model_installer();', h_text)

    def test_adaptation_validates_all_results_before_any_write(self):
        for name in ('first.ts', 'second.ts'):
            (self.source / name).write_bytes(b'before')
        valid = dict(path='first.ts', before_sha256=restore.digest(b'before'),
                     after_sha256=restore.digest(b'after'),
                     replacements=[dict(before='before', after='after', count=1)])
        invalid = dict(valid, path='second.ts', after_sha256=restore.digest(b'wrong'))
        with self.assertRaisesRegex(ValueError, 'postimage'):
            restore.adapt_fixtures(self.source, [valid, invalid])
        self.assertEqual(b'before', (self.source / 'first.ts').read_bytes())

    def test_adaptation_rejects_wrong_occurrence_count(self):
        (self.source / 'example.ts').write_bytes(b'before')
        with self.assertRaisesRegex(ValueError, 'occurrence'):
            restore.adapt_fixtures(self.source, [dict(path='example.ts',
                before_sha256=restore.digest(b'before'), after_sha256=restore.digest(b'after'),
                replacements=[dict(before='before', after='after', count=2)])])

    def test_legacy_fixture_stamp_migrates_and_resumes_without_downloads(self):
        root = self.source / 'ci'
        source = root / 'build/src'
        output = source / 'out/Default'
        output.mkdir(parents=True)
        (source / 'example.ts').write_bytes(b'before')
        (root / 'helium-chromium').mkdir()
        (root / 'helium-chromium/chromium_version.txt').write_text('test-version')
        manifest = dict(chromium_version='test-version', packages=[])
        old_signature = restore.digest((json.dumps(manifest, indent=2) + '\n').encode())
        item = dict(path='example.ts', before_sha256=restore.digest(b'before'),
                    after_sha256=restore.digest(b'after'),
                    replacements=[dict(before='before', after='after', count=1)])
        manifest['previous_policy_sha256'] = restore.digest(json.dumps(dict(manifest, adaptations=[])).encode())
        manifest['adaptations'] = [item]
        (root / '.github/scripts').mkdir(parents=True)
        (root / '.github/xenon-test-inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')
        stamp = output / 'xenon-test-inputs.json'
        stamp.write_text(json.dumps(dict(signature=old_signature,
            files={'example.ts': restore.digest(b'before')})))
        with mock.patch.object(restore, '__file__', str(root / '.github/scripts/restore.py')), \
             mock.patch.object(restore.urllib.request, 'urlopen') as download, \
             mock.patch.object(restore, 'missing_inputs'):
            restore.main()
            self.assertEqual(b'after', (source / 'example.ts').read_bytes())
            migrated = json.loads(stamp.read_text())
            self.assertEqual(item['after_sha256'], migrated['files']['example.ts'])
            restore.main()
            download.assert_not_called()
            self.assertEqual(migrated, json.loads(stamp.read_text()))
            # A specifically pinned previous adaptation policy also migrates
            # only after all retained files match their recorded hashes.
            (source / 'example.ts').write_bytes(b'before')
            stamp.write_text(json.dumps(dict(signature=manifest['previous_policy_sha256'],
                files={'example.ts': restore.digest(b'before')})))
            restore.main()
            self.assertEqual(migrated, json.loads(stamp.read_text()))
            for unknown in ('unknown policy', None):
                stamp.write_text(json.dumps(dict(migrated, signature=unknown)))
                with self.assertRaisesRegex(ValueError, 'Unknown retained fixture policy'):
                    restore.main()
            stamp.write_text(json.dumps(migrated))
            (source / 'example.ts').write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError, 'Retained test inputs changed'):
                restore.main()

    def test_manifest_matches_current_version_and_pins_every_package(self):
        root = Path(__file__).resolve().parents[2]
        data = json.loads((root / '.github/xenon-test-inputs.json').read_text())
        self.assertEqual((root / 'helium-chromium/chromium_version.txt').read_text().strip(), data['chromium_version'])
        for package in data['packages']:
            self.assertRegex(package['content_sha256'], r'^[a-f0-9]{64}$')
            self.assertTrue(data['chromium_revision'] in package['url'] or package['name'] == 'fonts')


if __name__ == '__main__':
    unittest.main()
