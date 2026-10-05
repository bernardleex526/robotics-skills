#!/usr/bin/env python3
"""Read-only conservative command-gating audit, not a controller or safety proof."""
import argparse
import json
import math
from pathlib import Path
import sys


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('expected finite numeric value')
    return value


def check(data):
    if not isinstance(data, dict):
        raise ValueError('trace must be a JSON object')
    limits = [finite(data[k]) for k in ('max_age_s', 'max_speed_mps', 'max_abs_yaw_rate_rps')]
    if any(v <= 0 for v in limits):
        raise ValueError('limits must be positive')
    samples = data['samples']
    if not isinstance(samples, list) or not samples:
        raise ValueError('samples must be a nonempty array')
    findings = []
    previous = None
    for index, row in enumerate(samples):
        if not isinstance(row, dict):
            raise ValueError('sample must be a JSON object')
        t, vx, wz = (finite(row[k]) for k in ('t', 'vx', 'wz'))
        state = row['state']
        if state not in ('IDLE', 'ACQUIRING', 'TRACKING', 'LOST', 'STOPPED'):
            raise ValueError('unknown state')
        if not isinstance(row['safety_ok'], bool):
            raise ValueError('safety_ok must be boolean')
        target = row['target_id']
        if target is not None and (not isinstance(target, str) or not target.strip()):
            raise ValueError('target_id must be a nonempty string or null')
        observed = row['observation_t']
        age = t-finite(observed) if observed is not None else None
        reasons = []
        if previous is not None and t <= previous:
            reasons.append('nonmonotonic_time')
        previous = t
        if abs(vx) > limits[1] or abs(wz) > limits[2]:
            reasons.append('command_limit_exceeded')
        moving = vx != 0 or wz != 0
        allowed = state == 'TRACKING' and row['safety_ok'] and target is not None and age is not None and 0 <= age <= limits[0]
        if moving and not allowed:
            reasons.append('motion_without_valid_tracking_gate')
        if reasons:
            findings.append({'sample': index, 'reasons': reasons})
    return {'status': 'fail' if findings else 'pass', 'samples': len(samples), 'findings': findings,
            'limitations': ['Does not verify full state transitions, target identity, TF, braking, collision avoidance or hardware response.']}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace', type=Path)
    a = p.parse_args(argv)
    try:
        result = check(json.loads(a.trace.read_text(encoding='utf-8-sig')))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'pass' else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status':'invalid','error':str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    # Stable UTF-8 JSON even when a Windows coding agent captures pipes.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
