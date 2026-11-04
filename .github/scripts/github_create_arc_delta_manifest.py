#!/usr/bin/env python3
"""Record a bounded append-only patch delta from a locally prepared quilt tree."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    'arc_checkpoint', Path(__file__).with_name('github_repair_arc_checkpoint.py'))
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-commit', required=True)
    parser.add_argument('--source-run', required=True)
    args = parser.parse_args()
    root = Path(subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    base = subprocess.check_output(
        ['git', 'show', args.base_commit + ':patches/series'], cwd=root, text=True)
    series = (root / 'patches/series').read_text()
    if not series.startswith(base):
        raise SystemExit('Only an append-only patch series can reuse this checkpoint.')
    additions = [x.strip() for x in series[len(base):].splitlines()
                 if x.strip() and not x.startswith('#')]
    if not additions:
        raise SystemExit('No appended patches to record.')
    data = dict(base_commit=args.base_commit, source_run=args.source_run,
                input_sha256=checkpoint.source_fingerprint(root), patches=[], sources={})
    for name in additions:
        patch = root / 'patches' / name
        data['patches'].append(dict(path='patches/' + name,
                                   sha256=checkpoint.file_hash(patch)))
        for section in patch.read_text().split('Index: src/')[1:]:
            path = section.splitlines()[0]
            if path in data['sources']:
                continue
            old = root / 'build/src/.pc' / name / path
            if '--- /dev/null\n' in section:
                before = None
            else:
                if not old.is_file():
                    raise SystemExit('Missing quilt preimage: ' + str(old))
                before = checkpoint.file_hash(old)
            data['sources'][path] = dict(
                before=before, after=checkpoint.file_hash(root / 'build/src' / path))
    destination = root / '.github/arc-checkpoint-delta.json'
    destination.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    print(f'Recorded {len(additions)} patches and {len(data["sources"])} source preimages.')


if __name__ == '__main__':
    main()
