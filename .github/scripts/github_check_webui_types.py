#!/usr/bin/env python3
"""Check retained WebUI projects without Ninja, GN, C++ compilation or emitting JS.

Run only in a diagnostic copy of a verified checkpoint. Aggregate all project
errors rather than stopping at the first incompatible upstream fixture.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


def check(source, policy, compiler, report_dir):
    spec = importlib.util.spec_from_file_location(
        'restore', Path(__file__).with_name('github_restore_xenon_test_inputs.py'))
    restore = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(restore)
    adaptations = json.loads(policy.read_text())['adaptations']
    changed = [item for item in adaptations
               if restore.digest((source / item['path']).read_bytes()) != item['after_sha256']]
    restore.adapt_fixtures(source, adaptations)
    # Preprocessed inputs are generated, isolated diagnostic copies. Apply only
    # the same exact replacements as the verified raw fixture adaptation.
    gen = source / 'out/Default/gen'
    for item in changed:
        relative = Path(item['path'])
        generated = gen / relative.parent / 'preprocessed' / relative.name
        text = generated.read_text()
        for replacement in item['replacements']:
            if text.count(replacement['before']) != replacement['count']:
                raise ValueError('Generated fixture replacement count differs: ' + str(generated))
            text = text.replace(replacement['before'], replacement['after'])
        generated.write_text(text)
    configs = sorted((gen / 'chrome/test/data/webui').rglob('tsconfig_build_ts.json'))
    if not configs:
        raise ValueError('No retained WebUI TypeScript projects found')
    report_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for config in configs:
        data = json.loads(config.read_text())
        # References require build-mode outputs and are unnecessary for this
        # standalone check: retain the exact files, paths and compiler settings,
        # and resolve dependencies through the checkpoint's generated types.
        data.pop('references', None)
        options = data.setdefault('compilerOptions', {})
        options.update(noEmit=True, incremental=False, composite=False)
        options.pop('tsBuildInfoFile', None)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', prefix='typecheck-',
                                         dir=config.parent, delete=False) as output:
            json.dump(data, output)
            diagnostic_config = Path(output.name)
        name = str(config.parent.relative_to(gen))
        try:
            run = subprocess.run([str(compiler), '--project', str(diagnostic_config), '--pretty', 'false'],
                                 capture_output=True, text=True, timeout=90)
            log = run.stdout + run.stderr
            code = run.returncode
        except subprocess.TimeoutExpired:
            code, log = 124, 'Type check exceeded the 90-second per-project diagnostic limit.\n'
        finally:
            diagnostic_config.unlink()
        (report_dir / (name.replace('/', '_') + '.log')).write_text(log)
        results.append(dict(project=name, exit_code=code))
        print(('PASS ' if code == 0 else 'FAIL ') + name, flush=True)
        if code:
            print(log, flush=True)
    (report_dir / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    failed = [item for item in results if item['exit_code']]
    print(f'{len(results)} projects checked; {len(failed)} failed.', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--policy', default='.github/xenon-test-inputs.json', type=Path)
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--report-dir', default='webui-typecheck-report', type=Path)
    args = parser.parse_args()
    raise SystemExit(check(args.source.resolve(), args.policy, args.compiler.resolve(), args.report_dir))
