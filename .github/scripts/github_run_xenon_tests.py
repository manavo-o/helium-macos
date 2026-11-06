#!/usr/bin/env python3
"""Run fresh Xenon regressions after their targets compile within a CI phase."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

PLAN = 'xenon-native-v1'
REQUIRED_BROWSER_TESTS = {
    'ArcCommandBarBrowserTest.EditAddressReplacesOriginalTab',
    'ArcCommandBarBrowserTest.HomeSubmissionReusesEmptySlot',
    'ArcCommandBarBrowserTest.FinalTabCloseReturnsHome',
    'ArcCommandBarBrowserTest.HomeRevealsSidebarWithoutChangingPreference',
    'ArcCommandBarBrowserTest.CommandEnterSearchesRawQuestionAfterSelectionMoves',
    'SidePanelCoordinatorLoadingContentTest.ToggleCancelsPendingEntryBeforeFirstPanelIsVisible',
}
BROWSER_FILTER = ('ArcCommandBarBrowserTest.*:'
                  'SidePanelCoordinatorLoadingContentTest.'
                  'ToggleCancelsPendingEntryBeforeFirstPanelIsVisible')


def signature(root, data, arch):
    if data.get('test_plan') != PLAN:
        raise ValueError('This runner requires the explicit Xenon validation plan.')
    source = root / 'build/src'
    for path, record in data['sources'].items():
        file = source / path
        actual = hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None
        if actual != record['after']:
            raise ValueError('Source does not match the audited delta: ' + path)
    payload = dict(plan=PLAN, arch=arch, sources=data['sources'],
                   patches=data['patches'], required=sorted(REQUIRED_BROWSER_TESTS),
                   browser_filter=BROWSER_FILTER,
                   runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   test_inputs={path: hashlib.sha256((root / path).read_bytes()).hexdigest()
                                for path in ('.github/xenon-test-inputs.json',
                                             '.github/scripts/github_restore_xenon_test_inputs.py')})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def verify_browser_summary(path):
    data = json.loads(path.read_text())
    iterations = data.get('per_iteration_data', [])
    if len(iterations) != 1:
        raise ValueError('Expected one complete browser-test iteration.')
    results = iterations[0]
    if not REQUIRED_BROWSER_TESTS <= results.keys():
        raise ValueError('Required navigation or loading-panel regression did not run.')
    for name, attempts in results.items():
        if len(attempts) != 1 or attempts[0].get('status') != 'SUCCESS':
            raise ValueError('Browser regression did not pass on its first attempt: ' + name)
    return len(results)


def valid_stamp(path, expected):
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text())
        return (isinstance(data, dict) and data.get('signature') == expected and
                data.get('routing') == 5 and data.get('bubble') == 2 and
                data.get('browser', 0) >= len(REQUIRED_BROWSER_TESTS))
    except (ValueError, TypeError):
        return False


def run_tests(root, arch, expected, stamp):
    output = root / 'build/src/out/Default'
    log = root / ('github_actions_xenon_tests_' + arch + '.log')
    commands = [
        ('routing', 'arc_routing_tests', 'ArcQuestionRoutingTest.*', 5),
        ('bubble', 'arc_bubble_lifecycle_tests', 'ArcBubbleLifecycleTest.*', 2),
        ('browser', 'browser_tests', BROWSER_FILTER, None),
    ]
    results = dict(signature=expected)
    stamp.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='xenon-regressions-') as tmp:
        for name, binary, test_filter, count in commands:
            executable = output / binary
            if not executable.is_file():
                raise ValueError('Missing freshly built test executable: ' + binary)
            summary = Path(tmp) / (name + '.json')
            command = [str(executable), '--gtest_filter=' + test_filter,
                       '--test-launcher-jobs=1', '--test-launcher-retry-limit=0',
                       '--test-launcher-summary-output=' + str(summary)]
            try:
                completed = subprocess.run(command, cwd=output, capture_output=True,
                                           text=True, errors='replace', timeout=900)
            except subprocess.TimeoutExpired as error:
                raise ValueError('Regression suite timed out: ' + name) from error
            text = completed.stdout + completed.stderr
            print(text, flush=True)
            with log.open('a') as stream:
                stream.write('\nSUITE: ' + name + '\n' + text)
            if completed.returncode:
                raise ValueError('Regression suite failed: ' + name)
            if count is None:
                results[name] = verify_browser_summary(summary)
            else:
                matches = re.findall(r'\[\s*PASSED\s*\]\s+(\d+)\s+tests?', text)
                if not matches or int(matches[-1]) != count:
                    raise ValueError('Unexpected passing-test count for ' + name)
                results[name] = count
    stamp.write_text(json.dumps(results, indent=2, sort_keys=True) + '\n')
    print('Fresh Xenon regressions passed; browser build may proceed.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch', required=True)
    parser.add_argument('--check-stamp', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / '.github/arc-checkpoint-delta.json').read_text())
    try:
        expected = signature(root, data, args.arch)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    stamp = root / 'build/src/out/Default/xenon-regressions.json'
    if args.check_stamp:
        return 0 if valid_stamp(stamp, expected) else 1
    try:
        run_tests(root, args.arch, expected, stamp)
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
