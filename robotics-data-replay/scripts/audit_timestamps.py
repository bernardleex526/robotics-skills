#!/usr/bin/env python3
"""Audit exported topic stamps; never interprets timestamp gaps as physical safety."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import sys


def number(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('timestamps and thresholds must be finite')
    return value


def audit(rows, max_gap=None):
    if max_gap is not None and number(max_gap) <= 0:
        raise ValueError('max_gap must be positive')
    groups = {}
    for row in rows:
        raw_topic = row.get('topic')
        if not isinstance(raw_topic, str):
            raise ValueError('topic must be text')
        topic = raw_topic.strip()
        if not topic:
            raise ValueError('topic must be nonempty')
        stamp = number(row['stamp'])
        raw_received = row.get('received')
        received = number(raw_received) if raw_received is not None and str(raw_received).strip() else None
        groups.setdefault(topic, []).append((stamp, received))
    if not groups:
        raise ValueError('no samples')
    results = {}
    for topic, values in groups.items():
        gaps = [b[0] - a[0] for a, b in zip(values, values[1:])]
        ages = [r-s for s, r in values if r is not None]
        results[topic] = {'count': len(values), 'duplicates': sum(g == 0 for g in gaps),
                          'backwards': sum(g < 0 for g in gaps),
                          'max_gap_s': max(gaps) if gaps else None,
                          'median_gap_s': statistics.median(gaps) if gaps else None,
                          'over_threshold': sum(g > max_gap for g in gaps) if max_gap is not None else None,
                          'min_age_s': min(ages) if ages else None,
                          'max_age_s': max(ages) if ages else None,
                          'future_stamps': sum(a < 0 for a in ages)}
    failed = any(r['duplicates'] or r['backwards'] or r['over_threshold'] or r['future_stamps'] for r in results.values())
    return {'status': 'fail' if failed else 'pass', 'topics': results,
            'limitations': ['Input-order audit only; no clock synchronization or TF validation.',
                            'Age is meaningful only when received and stamp share an aligned clock.']}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv', type=Path)
    p.add_argument('--max-gap-s', type=float)
    a = p.parse_args(argv)
    try:
        with a.csv.open(encoding='utf-8-sig', newline='') as f:
            result = audit(csv.DictReader(f), a.max_gap_s)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'pass' else 1
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        print(json.dumps({'status':'invalid', 'error':str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    # Stable UTF-8 JSON even when a Windows coding agent captures pipes.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
