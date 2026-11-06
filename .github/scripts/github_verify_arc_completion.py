#!/usr/bin/env python3
"""A checkpointed phase is resumable work, not a finished browser artifact."""
import json
import os
import sys


def verify_completion(phases):
    if any(item.get('result') in ('failure', 'cancelled') for item in phases.values()):
        raise ValueError('A build phase failed or was cancelled; the browser is not complete.')
    finished = [name for name, item in phases.items()
                if item.get('result') == 'success'
                and item.get('outputs', {}).get('status') == 'finished']
    if finished:
        return sorted(finished)[-1]
    running = [name for name, item in phases.items()
               if item.get('result') == 'success'
               and item.get('outputs', {}).get('status') == 'running']
    if running:
        raise ValueError('Checkpoint saved by ' + sorted(running)[-1] +
                         ', but no phase finished. Resume its checkpoint; do not report success.')
    raise ValueError('No successful browser-completion output was produced.')


if __name__ == '__main__':
    try:
        phases = json.loads(os.environ['HELIUM_PHASE_RESULTS'])
        print(json.dumps(phases, sort_keys=True))
        phase = verify_completion(phases)
        print('Browser compilation and artifact preparation completed in ' + phase)
    except (ValueError, KeyError) as error:
        print('::error::' + str(error), file=sys.stderr)
        raise SystemExit(1)
