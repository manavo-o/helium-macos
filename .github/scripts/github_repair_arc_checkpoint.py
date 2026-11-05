#!/usr/bin/env python3
"""Resume a verified Arc checkpoint and apply an exact, audited source delta."""

import argparse
import hashlib
import json
import os
import re
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



class DomainSubstitution:
    """Use the pinned Helium rules, scoped to its existing source-file list."""
    def __init__(self, root):
        tree = root / 'helium-chromium'
        self.paths = set((tree / 'domain_substitution.list').read_text().splitlines())
        self.rules = [tuple(line.split('#')) for line in
                      (tree / 'domain_regex.list').read_text().splitlines() if line]
        self.rules = [(re.compile(pattern), replacement) for pattern, replacement in self.rules]

    def source(self, path, content):
        if content is None or path not in self.paths:
            return content
        try:
            text = content.decode('utf-8')
            encoding = 'utf-8'
        except UnicodeDecodeError:
            text = content.decode('iso-8859-1')
            encoding = 'iso-8859-1'
        for pattern, replacement in self.rules:
            text = pattern.sub(replacement, text)
        return text.encode(encoding)

    def patch(self, content):
        # Normalize only hunk payloads for listed files; keep the raw patch on
        # disk unchanged so fresh builds still patch before substitution.
        output = []
        path = None
        in_hunk = False
        for line in content.splitlines(keepends=True):
            if line.startswith('Index: src/'):
                path = line.removeprefix('Index: src/').rstrip('\r\n')
                in_hunk = False
            elif line.startswith('@@ '):
                in_hunk = True
            if in_hunk and line[:1] in (' ', '+', '-'):
                line = line[0] + self.source(path, line[1:].encode()).decode()
            output.append(line)
        return ''.join(output)


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
    for path, expected in data.get('domain_inputs', {}).items():
        if file_hash(root / path) != expected:
            return None
    return data


def check_sources(source, records, key):
    return all(file_hash(source / path) == record[key]
               for path, record in records.items())


def patch_tree(root, source, data):
    executable = shutil.which('gpatch') or shutil.which('patch')
    if not executable:
        raise SystemExit('A patch executable is required for checkpoint reuse.')
    substitution = DomainSubstitution(root)
    for patch in data['patches']:
        content = substitution.patch((root / patch['path']).read_text())
        subprocess.run([executable, '--batch', '--forward', '-p1', '-F0'],
                       input=content, text=True, cwd=source, check=True)


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
    parser.add_argument('--require-checkpoint', action='store_true')
    args = parser.parse_args()
    root = Path(subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    delta = compatible_delta(root)
    if args.select:
        compatible = delta is not None or source_fingerprint(root) == INPUT_SHA256
        if args.require_checkpoint and not compatible:
            raise SystemExit('No verified incremental checkpoint matches these inputs; refusing a full rebuild.')
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
