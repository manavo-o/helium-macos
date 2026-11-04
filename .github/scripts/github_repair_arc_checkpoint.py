#!/usr/bin/env python3
"""Resume a verified Arc checkpoint and apply an exact, audited source delta."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile

SOURCE_RUN = '41707908336'
INPUT_SHA256 = '8836d513f6790ff1a6b88f533f1f5e269be5c9f0d50d6cb38ec69a80e89eaac3'
OLD_SOURCE_SHA256 = 'c47084af04a6cc8fb24ad57ed879f5c6de874106cf3d6cc305c1fad8a119a831'
NEW_SOURCE_SHA256 = 'd5eb98d075cc705d09b4c7754d5845e193ce57c8241bda2cdbf8a50dc2a0209c'
SOURCE_PATH = 'build/src/chrome/browser/ui/views/tabs/vertical/arc_command_bar_view.cc'


def source_fingerprint(root):
    digest = hashlib.sha256()
    entries = subprocess.check_output(
        ['git', 'ls-files', '--stage', '-z'], cwd=root).split(b'\0')
    for entry in entries:
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        mode, object_id, _ = metadata.split()
        if path.startswith((b'.github/', b'docs/')):
            continue
        content = object_id if mode == b'160000' else hashlib.sha256(
            (root / os.fsdecode(path)).read_bytes()).hexdigest().encode()
        digest.update(mode + b' ' + path + b'\0' + content + b'\0')
    return digest.hexdigest()



def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def compatible_delta(root):
    manifest = root / '.github/arc-checkpoint-delta.json'
    if not manifest.is_file():
        return None
    data = json.loads(manifest.read_text())
    if source_fingerprint(root) != data['input_sha256']:
        return None
    for patch in data['patches']:
        if file_hash(root / patch['path']) != patch['sha256']:
            return None
    return data


def check_sources(source, records, key):
    return all(file_hash(source / path) == record[key]
               for path, record in records.items())


def patch_tree(root, source, data):
    executable = shutil.which('gpatch') or shutil.which('patch')
    if not executable:
        raise SystemExit('A patch executable is required for checkpoint reuse.')
    for patch in data['patches']:
        subprocess.run([executable, '--batch', '--forward', '-p1', '-F0',
                        '-i', str(root / patch['path'])], cwd=source, check=True)


def apply_delta(root, data):
    source = root / 'build/src'
    records = data['sources']
    if check_sources(source, records, 'after'):
        print('Checkpoint already contains the verified native UI delta.')
        return
    if not check_sources(source, records, 'before'):
        for path, record in records.items():
            actual = file_hash(source / path)
            if actual != record['before']:
                print(f"Source mismatch: {path} expected={record['before']} actual={actual}", flush=True)
        raise SystemExit('Checkpoint source hashes differ; refusing reuse.')
    # Validate the full ordered patch chain without modifying the checkpoint.
    # This handles overlapping changes and newly added files.
    with tempfile.TemporaryDirectory(prefix='arc-checkpoint-') as temporary:
        mirror = Path(temporary)
        for path, record in records.items():
            if record['before'] is not None:
                destination = mirror / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / path, destination)
        patch_tree(root, mirror, data)
        if not check_sources(mirror, records, 'after'):
            raise SystemExit('Patch output differs from the verified manifest.')
    patch_tree(root, source, data)
    if not check_sources(source, records, 'after'):
        raise SystemExit('Checkpoint delta verification failed after patching.')
    print('Applied verified native UI patches; retained compiled build outputs.')


def repair(root):
    if source_fingerprint(root) != INPUT_SHA256:
        raise SystemExit('Build inputs changed: refusing this checkpoint repair.')
    source = root / SOURCE_PATH
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if digest == NEW_SOURCE_SHA256:
        print('Arc checkpoint already contains the verified repair.')
        return
    if digest != OLD_SOURCE_SHA256:
        raise SystemExit('Unexpected checkpoint source: refusing to modify it.')
    updated = original.replace(b'void Submit(const std::u16string& text)',
                               b'void Submit(std::u16string_view text)')
    if hashlib.sha256(updated).hexdigest() != NEW_SOURCE_SHA256:
        raise SystemExit('Checkpoint repair did not match the expected source.')
    source.write_bytes(updated)
    print('Applied Arc string-view fix; preserved all existing build outputs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--select', action='store_true')
    args = parser.parse_args()
    root = Path(subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    delta = compatible_delta(root)
    if args.select:
        compatible = delta is not None or source_fingerprint(root) == INPUT_SHA256
        selected_run = delta['source_run'] if delta else SOURCE_RUN
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write(f'source_run={selected_run if compatible else ""}\n')
            output.write(f'repair_arc_checkpoint={str(compatible).lower()}\n')
        print(f'Using pinned Arc checkpoint {selected_run}.' if compatible else
              'Source inputs differ; using a fresh build.')
    elif delta:
        apply_delta(root, delta)
    else:
        repair(root)


if __name__ == '__main__':
    main()
