#!/usr/bin/env python3
"""Exercise diagnostic aggregation without browser compilation or network."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('checker', Path(__file__).with_name('github_check_webui_types.py'))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class WebUITypeCheckTest(unittest.TestCase):
    def test_graph_preparation_never_runs_compilers_or_other_actions(self):
        commands = '\n'.join([
            'clang++ huge_browser.cc',
            'python3 ../../tools/other_build_action.py chrome/test/data/webui/file.ts',
            'python3 ../../tools/grit/preprocess_if_expr.py --in-folder ../../chrome/test/data/webui/example --in-files test.ts',
            'python3 ../../tools/typescript/ts_library.py --gen_dir gen/chrome/test/data/webui/example --in_files test.ts',
            'python3 ../../tools/typescript/ts_library.py --gen_dir gen/ui/webui/resources --in_files product.ts',
        ])
        with mock.patch.object(checker.subprocess, 'check_output', return_value=commands.encode() + b'\nclang++ invalid-\xc3-path') as graph, \
             mock.patch.object(checker.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
            checker.prepare_projects(Path('/diagnostic/src'))
        self.assertEqual(['-t', 'commands', 'browser_tests'], graph.call_args.args[0][-3:])
        self.assertEqual(2, run.call_count)
        self.assertEqual('../../tools/grit/preprocess_if_expr.py', run.call_args_list[0].args[0][1])
        self.assertIn('--generate-config', run.call_args_list[1].args[0])

    def test_checks_all_projects_without_emitting_or_invoking_build_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = root / 'policy.json'
            policy.write_text('{"adaptations": []}')
            configs = []
            for name in ('first', 'second'):
                p = root / 'out/Default/gen/chrome/test/data/webui' / name / 'tsconfig_build_ts.json'
                p.parent.mkdir(parents=True)
                p.write_text(json.dumps(dict(files=['preprocessed/test.ts'], references=[dict(path='dependency.json')],
                    compilerOptions=dict(paths={'chrome://example/*': ['types/*']}, composite=True,
                                         tsBuildInfoFile='retained.tsbuildinfo'))))
                configs.append(p)
            originals = [p.read_bytes() for p in configs]
            commands = []

            def run(command, **kwargs):
                commands.append(command)
                self.assertEqual(['pinned-tsc', '--project'], command[:2])
                data = json.loads(Path(command[2]).read_text())
                self.assertTrue(data['compilerOptions']['noEmit'])
                self.assertFalse(data['compilerOptions']['incremental'])
                self.assertNotIn('tsBuildInfoFile', data['compilerOptions'])
                self.assertEqual([dict(path='dependency.json')], data['references'])
                self.assertEqual({'chrome://example/*': ['types/*']}, data['compilerOptions']['paths'])
                self.assertEqual(['preprocessed/test.ts'], data['files'])
                self.assertEqual(90, kwargs['timeout'])
                return subprocess.CompletedProcess(command, 1 if len(commands) == 1 else 0,
                                                   'fixture.ts: error TS2339\n' if len(commands) == 1 else '', '')

            report = root / 'report'
            with mock.patch.object(checker.subprocess, 'run', side_effect=run), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(1, checker.check(root, policy, Path('pinned-tsc'), report))
            self.assertEqual(2, len(commands))
            self.assertEqual(originals, [p.read_bytes() for p in configs])
            self.assertFalse(list(root.rglob('typecheck-*.json')))
            self.assertEqual([1, 0], [r['exit_code'] for r in json.loads((report / 'summary.json').read_text())])

    def test_missing_projects_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = root / 'policy.json'
            policy.write_text('{"adaptations": []}')
            with self.assertRaisesRegex(ValueError, 'No retained'):
                checker.check(root, policy, Path('compiler'), root / 'report')


if __name__ == '__main__':
    unittest.main()
