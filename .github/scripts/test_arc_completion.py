#!/usr/bin/env python3
"""Prevent skipped continuations from reporting a checkpoint as a completed app."""
import importlib.util
from pathlib import Path
import re
import unittest

spec = importlib.util.spec_from_file_location(
    'completion', Path(__file__).with_name('github_verify_arc_completion.py'))
completion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(completion)


def phase(result, status=None):
    return {'result': result, 'outputs': {'status': status} if status else {}}


class CompletionTest(unittest.TestCase):
    def test_first_phase_can_finish_and_skip_later_jobs(self):
        self.assertEqual('build_job_01', completion.verify_completion({
            'build_job_01': phase('success', 'finished'),
            'build_job_02': phase('skipped')}))

    def test_resumed_phase_can_finish(self):
        self.assertEqual('build_job_02', completion.verify_completion({
            'build_job_01': phase('success', 'running'),
            'build_job_02': phase('success', 'finished')}))

    def test_saved_checkpoint_without_continuation_is_not_success(self):
        with self.assertRaisesRegex(ValueError, 'no phase finished'):
            completion.verify_completion({'build_job_01': phase('success', 'running'),
                                          'build_job_02': phase('skipped')})

    def test_failed_phase_cannot_count_as_finished(self):
        with self.assertRaises(ValueError):
            completion.verify_completion({'build_job_01': phase('failure', 'finished')})

    def test_missing_outputs_cannot_count_as_finished(self):
        with self.assertRaises(ValueError):
            completion.verify_completion({'build_job_01': phase('success')})

    def test_every_continuation_has_explicit_status_and_result_guards(self):
        text = Path(__file__).parents[1].joinpath('workflows/building.yml').read_text()
        for number in range(2, 11):
            block = text.split(f'  build_job_{number:02d}:', 1)[1].split('    uses:', 1)[0]
            expression = re.search(r'    if: (.+)', block).group(1)
            previous = f'needs.build_job_{number - 1:02d}'
            self.assertIn('!cancelled()', expression)
            self.assertIn(previous + ".result == 'success'", expression)
            self.assertIn(previous + ".outputs.status == 'running'", expression)


if __name__ == '__main__':
    unittest.main()
