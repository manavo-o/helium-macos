#!/usr/bin/env python3
"""Exercise the actual UI patch chain, idempotence and fail-closed checks."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    'checkpoint', Path(__file__).with_name('github_repair_arc_checkpoint.py'))
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)
ROOT = Path(subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip())
DATA = json.loads((ROOT / '.github/arc-checkpoint-delta.json').read_text())


class CheckpointDeltaTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'build/src').mkdir(parents=True)
        (self.root / '.github').mkdir()
        (self.root / '.github/arc-checkpoint-delta.json').write_text(json.dumps(DATA))
        for patch in DATA['patches']:
            destination = self.root / patch['path']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / patch['path'], destination)
        for path, record in DATA['sources'].items():
            if record['before'] is None:
                continue
            candidates = [ROOT / 'build/src/.pc' / patch['path'].removeprefix('patches/') / path
                          for patch in DATA['patches']]
            original = next(p for p in candidates if p.is_file())
            self.assertEqual(record['before'], checkpoint.file_hash(original))
            destination = self.root / 'build/src' / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, destination)

    def test_full_patch_chain_and_idempotence_preserve_existing_outputs(self):
        output = self.root / 'build/src/out/Default/retained-object.o'
        output.parent.mkdir(parents=True)
        output.write_bytes(b'existing compiler output')
        checkpoint.apply_delta(self.root, DATA)
        self.assertTrue(checkpoint.check_sources(self.root / 'build/src', DATA['sources'], 'after'))
        checkpoint.apply_delta(self.root, DATA)
        self.assertEqual(output.read_bytes(), b'existing compiler output')

    def test_unexpected_source_fails_before_modifying_any_file(self):
        path = next(p for p, value in DATA['sources'].items() if value['before'])
        source = self.root / 'build/src' / path
        source.write_bytes(b'unexpected source')
        with self.assertRaises(SystemExit):
            checkpoint.apply_delta(self.root, DATA)
        self.assertEqual(source.read_bytes(), b'unexpected source')
        new_path = next(p for p, value in DATA['sources'].items() if value['before'] is None)
        self.assertFalse((self.root / 'build/src' / new_path).exists())

    def test_selector_rejects_changed_patch_even_when_other_inputs_match(self):
        with mock.patch.object(checkpoint, 'source_fingerprint', return_value=DATA['input_sha256']):
            self.assertIsNotNone(checkpoint.compatible_delta(self.root))
            patch = self.root / DATA['patches'][0]['path']
            patch.write_text(patch.read_text() + '\n')
            self.assertIsNone(checkpoint.compatible_delta(self.root))


if __name__ == '__main__':
    unittest.main()
