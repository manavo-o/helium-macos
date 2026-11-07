#!/usr/bin/env python3
"""Check retained WebUI projects without Ninja, GN, C++ compilation or emitting JS.

Run only in a diagnostic copy of a verified checkpoint. Aggregate all project
errors rather than stopping at the first incompatible upstream fixture.
"""
import argparse
import importlib.util
import json
import shlex
import sys
from pathlib import Path
import subprocess
import tempfile


def check(source, policy, compiler, report_dir, ninja="ninja"):
    spec = importlib.util.spec_from_file_location(
        'restore', Path(__file__).with_name('github_restore_xenon_test_inputs.py'))
    restore = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(restore)
    adaptations = json.loads(policy.read_text())['adaptations']
    restore.adapt_fixtures(source, adaptations)
    gen = source / 'out/Default/gen'
    if (source / 'out/Default/build.ninja').is_file():
        prepare_projects(source, ninja)
    else:
        # Unit-test mirrors need not contain a build graph.
        if adaptations:
            raise ValueError('Retained build graph required to preprocess adapted fixtures')
    configs = sorted(path for path in (gen / 'chrome/test/data/webui').rglob('tsconfig_*.json')
                     if 'files' in json.loads(path.read_text()))
    if not configs:
        raise ValueError('No retained WebUI TypeScript projects found')
    report_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for config in configs:
        data = json.loads(config.read_text())
        # Keep project references: Chromium's module resolution uses each
        # dependency's paths. This is plain tsc, never build mode, so references
        # do not trigger compilation or emitting dependency outputs.
        options = data.setdefault('compilerOptions', {})
        options.update(noEmit=True, incremental=False, composite=False)
        options.pop('tsBuildInfoFile', None)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', prefix='typecheck-',
                                         dir=config.parent, delete=False) as output:
            json.dump(data, output)
            diagnostic_config = Path(output.name)
        name = str(config.parent.relative_to(gen))
        if config.name != 'tsconfig_build_ts.json':
            name += '/' + config.stem
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


def prepare_projects(source, ninja="ninja"):
    """Read the graph, then run only fixture preprocessing/config generation."""
    output = source / 'out/Default'
    # Compiler commands elsewhere in Chromium can contain non-UTF-8 paths.
    # Select our ASCII Python actions before decoding; do not corrupt paths in
    # actions that we actually intend to execute.
    graph = subprocess.check_output([ninja, '-C', str(output), '-t', 'commands', 'browser_tests'])
    commands = b'\n'.join(line for line in graph.splitlines()
                          if b'chrome/test/data/webui' in line and
                          any(script in line for script in (
                              b'../../tools/grit/preprocess_if_expr.py',
                              b'../../tools/typescript/ts_library.py'))).decode('utf-8')
    count = 0
    for line in commands.splitlines():
        if 'chrome/test/data/webui' not in line:
            continue
        args = shlex.split(line)
        if len(args) < 2 or args[0] != 'python3':
            continue
        if args[1] == '../../tools/grit/preprocess_if_expr.py':
            if '--in-folder' not in args or not args[args.index('--in-folder') + 1].startswith('../../chrome/test/data/webui'):
                continue
            if not any(value.endswith(('.ts', '.js')) for value in args):
                continue
            subprocess.run(args, cwd=output, check=True, timeout=60)
        elif args[1] == '../../tools/typescript/ts_library.py':
            if '--gen_dir' not in args or not args[args.index('--gen_dir') + 1].startswith('gen/chrome/test/data/webui'):
                continue
            subprocess.run([sys.executable, str(Path(__file__).resolve()),
                            '--generate-config', str(source), *args[2:]],
                           cwd=output, check=True, timeout=60)
            count += 1
    if not count:
        raise ValueError('No WebUI TypeScript actions found in retained graph')
    print('Prepared', count, 'WebUI project configurations without compiling.', flush=True)


def generate_config(source, arguments):
    # Stop the pinned config generator at its compiler call. No TS compiler,
    # Ninja action or browser compiler is invoked by this mode.
    directory = source / 'tools/typescript'
    sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location('ts_library', directory / 'ts_library.py')
    library = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(library)

    class ConfigReady(Exception):
        pass

    def stop(*args, **kwargs):
        raise ConfigReady()

    library.typescript.RunTypeScript = stop
    try:
        library.main(arguments)
    except ConfigReady:
        return
    raise ValueError('Config generator did not reach its compiler boundary')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--generate-config':
        generate_config(Path(sys.argv[2]), sys.argv[3:])
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--policy', default='.github/xenon-test-inputs.json', type=Path)
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--report-dir', default='webui-typecheck-report', type=Path)
    parser.add_argument('--ninja', default='ninja')
    args = parser.parse_args()
    raise SystemExit(check(args.source.resolve(), args.policy, args.compiler.resolve(), args.report_dir, args.ninja))
