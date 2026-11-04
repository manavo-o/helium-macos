#!/usr/bin/env python3
"""Reuse the pinned Arc checkpoint only for its verified one-line repair."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess

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
    if args.select:
        compatible = source_fingerprint(root) == INPUT_SHA256
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write(f'source_run={SOURCE_RUN if compatible else ""}\n')
            output.write(f'repair_arc_checkpoint={str(compatible).lower()}\n')
        print('Using pinned Arc checkpoint.' if compatible else
              'Source inputs differ; using a fresh build.')
    else:
        repair(root)


if __name__ == '__main__':
    main()
