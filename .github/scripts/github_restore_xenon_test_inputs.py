#!/usr/bin/env python3
"""Restore pinned, pruned test inputs without overwriting prepared browser sources."""
import base64
import hashlib
import io
import json
import os
import shlex
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import urllib.request


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('Unsafe test-input path: ' + name)
    return path.as_posix()


def unpack(data, kind):
    if kind == 'base64':
        return {'payload': base64.b64decode(data, validate=True)}
    if kind != 'tar.gz':
        raise ValueError('Unknown test-input format: ' + kind)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive:
            name = safe_path(member.name)
            if member.isdir():
                continue
            if not member.isfile() or name in files:
                raise ValueError('Unexpected archive entry: ' + name)
            files[name] = archive.extractfile(member).read()
    return files


def tree_digest(files):
    # Gitiles tar headers contain request timestamps; bind the actual file names
    # and bytes instead. No tar metadata is trusted or extracted onto the tree.
    return digest(json.dumps({p: digest(b) for p, b in files.items()},
                             sort_keys=True).encode())


def install(source, package, files):
    if tree_digest(files) != package['content_sha256']:
        raise ValueError('Test-input content hash differs: ' + package['name'])
    destination = safe_path(package['destination'])
    restored = {}
    for name, data in files.items():
        relative = destination if package['format'] == 'base64' else destination + '/' + name
        path = source / relative
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError('Symlink in test-input destination: ' + relative)
        if path.exists():
            continue  # Never replace patched files, GN files, or retained outputs.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        restored[relative] = digest(data)
    return restored


def adapt_fixtures(source, adaptations):
    # Adapt only explicit, hashed test fixtures to the pinned Helium interface.
    # Validate every preimage and result before changing any fixture.
    pending = []
    records = {}
    for item in adaptations:
        relative = safe_path(item['path'])
        path = source / relative
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError('Symlink in fixture adaptation: ' + relative)
        original = path.read_bytes()
        if digest(original) == item['after_sha256']:
            records[relative] = item['after_sha256']
            continue
        intermediate = item.get('intermediate')
        start = 0
        if intermediate and digest(original) == intermediate['sha256']:
            start = intermediate['replacements_applied']
            if not 0 < start < len(item['replacements']):
                raise ValueError('Invalid intermediate fixture policy: ' + relative)
        elif digest(original) != item['before_sha256']:
            raise ValueError('Fixture adaptation preimage differs: ' + relative)
        updated = original
        for change in item['replacements'][start:]:
            before, after = change['before'].encode(), change['after'].encode()
            if updated.count(before) != change['count']:
                raise ValueError('Fixture adaptation occurrence count differs: ' + relative)
            updated = updated.replace(before, after)
        if digest(updated) != item['after_sha256']:
            raise ValueError('Fixture adaptation postimage differs: ' + relative)
        pending.append((path, updated))
        records[relative] = item['after_sha256']
    for path, updated in pending:
        path.write_bytes(updated)
    return records


def missing_inputs(source, targets):
    output = source / 'out/Default'
    # -t inputs only reads the existing build graph; it does not compile or run
    # GN. Ninja shell-quotes paths containing spaces or @; decode each line.
    result = subprocess.check_output([str(source / 'third_party/ninja/ninja'),
                                      '-C', str(output), '-t', 'inputs', *targets])
    missing = []
    for value in result.decode().splitlines():
        if not value:
            continue
        path = Path(os.path.abspath(output / shlex.split(value)[0]))
        if path.is_relative_to(source) and not path.is_relative_to(output) and not path.exists():
            missing.append(str(path.relative_to(source)))
    if missing:
        raise ValueError('Unrestored build inputs (refusing compilation): ' + ', '.join(missing[:30]))


def main():
    root = Path(__file__).resolve().parents[2]
    source = root / 'build/src'
    manifest_path = root / '.github/xenon-test-inputs.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['chromium_version'] != (root / 'helium-chromium/chromium_version.txt').read_text().strip():
        raise ValueError('Test fixtures do not match the pinned Chromium version.')
    stamp = source / 'out/Default/xenon-test-inputs.json'
    signature = digest(manifest_path.read_bytes())
    restored = {}
    if stamp.exists():
        prior = json.loads(stamp.read_text())
        # Accept the pre-adaptation stamp only when the package manifest is
        # byte-identical to the original pinned policy. Verify every retained
        # file before adapting it, then persist its new expected hash below.
        package_manifest = {k: v for k, v in manifest.items() if k not in ('adaptations', 'previous_policy_sha256')}
        legacy_signature = digest((json.dumps(package_manifest, indent=2) + '\n').encode())
        accepted_policies = {signature, legacy_signature}
        if manifest.get('previous_policy_sha256'):
            accepted_policies.add(manifest['previous_policy_sha256'])
        if prior.get('signature') in accepted_policies:
            restored = prior['files']
            if any(not (source / p).is_file() or digest((source / p).read_bytes()) != h
                   for p, h in restored.items()):
                raise ValueError('Retained test inputs changed; refusing reuse.')
        else:
            raise ValueError('Unknown retained fixture policy; refusing unchecked reuse.')
    if not restored:
        for package in manifest['packages']:
            with urllib.request.urlopen(package['url'], timeout=120) as response:
                data = response.read()
            if package.get('archive_sha256') and digest(data) != package['archive_sha256']:
                raise ValueError('Test-input archive hash differs: ' + package['name'])
            restored.update(install(source, package, unpack(data, package['format'])))
            print('Verified test-input package: ' + package['name'], flush=True)
    restored.update(adapt_fixtures(source, manifest.get('adaptations', [])))
    stamp.write_text(json.dumps(dict(signature=signature, files=restored), sort_keys=True) + '\n')
    missing_inputs(source, ['browser_tests',
                           'chrome/browser/ui/views/tabs/vertical:arc_routing_tests',
                           'ui/views:arc_bubble_lifecycle_tests'])
    print('Pinned test inputs verified; retained browser sources and build outputs.', flush=True)


if __name__ == '__main__':
    main()
