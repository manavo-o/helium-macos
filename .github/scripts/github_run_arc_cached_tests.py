#!/usr/bin/env python3
"""Run retained, previously passing tests only for the audited link-only delta."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

BASELINE_RUN = '42042324498'
LINK_ONLY_OUTPUTS = {
    'chrome/browser/ui/views/tabs/vertical/BUILD.gn':
        'd9522ba7392ed8c16277107db80766dea81f433ee946d8509c0126315e78aeef',
    'chrome/browser/ui/views/tabs/vertical/compile_arc_swift.py':
        '6607a43abe8552c19788d281dc19d80dc94dd2bc9a0d624858af6de5b120a9fd',
}


def validate_reuse(root, data):
    if data['source_run'] != BASELINE_RUN:
        raise ValueError('Cached test evidence belongs to checkpoint ' + BASELINE_RUN)
    changed = {path for path, record in data['sources'].items()
               if record['before'] != record['after']}
    if not changed or not changed <= LINK_ONLY_OUTPUTS.keys():
        raise ValueError('Source changes require fresh regression tests; cached tests cannot validate them.')
    for path, record in data['sources'].items():
        if path in changed and record['after'] != LINK_ONLY_OUTPUTS[path]:
            raise ValueError('This is not the previously audited native-link-only repair.')
        actual = hashlib.sha256((root / 'build/src' / path).read_bytes()).hexdigest()
        if actual != record['after']:
            raise ValueError('Restored source does not match the audited link-only delta: ' + path)


def validate_test_count(text, expected):
    passed = re.search(r'\[\s*PASSED\s*\]\s+(\d+)\s+tests?', text)
    if not passed or int(passed.group(1)) != expected:
        raise ValueError('The retained binary did not report the expected passing test count.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / '.github/arc-checkpoint-delta.json').read_text())
    validate_reuse(root, data)
    output = root / 'build/src/out/Default'
    tests = [('arc_routing_tests', 'ArcQuestionRoutingTest.*', 'routing', 5),
             ('arc_bubble_lifecycle_tests', 'ArcBubbleLifecycleTest.*', 'bubble', 2)]
    # Check both launchers before running anything. Never invoke Ninja here.
    for binary, _, _, _ in tests:
        if not (output / binary).is_file():
            raise ValueError('Missing retained test binary: ' + binary)
    print('Reusing the seven passing tests from checkpoint ' + BASELINE_RUN +
          '; this delta changes only native linking and a build-helper comment.', flush=True)
    for binary, filter_name, log_name, expected in tests:
        command = ['timeout', '-k', '10s', '90s', str(output / binary),
                   '--gtest_filter=' + filter_name]
        result = subprocess.run(command, cwd=output, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=110)
        text = result.stdout
        (root / f'github_actions_arc_{log_name}_tests_{args.arch}.log').write_text(text)
        print(text, flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
        validate_test_count(text, expected)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
