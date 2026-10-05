#!/usr/bin/env python3
"""Check cross-agent packaging, all local documentation links and routing fixtures."""
import json
from pathlib import Path
import re
import sys
from install_skills import inventory, TARGETS, PROFILES

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    problems = []
    skills = inventory(root)
    for profile, selected in PROFILES.items():
        for name in selected:
            if name not in skills:
                problems.append(f'{profile}: missing {name}')
    for name in skills:
        entry = root / name / 'SKILL.md'
        # Budget is a project convention, not a tokenizer measurement.
        if len(entry.read_bytes()) > 16000:
            problems.append(f'{name}: entrypoint exceeds 16 KB; move conditional content to references')
        for script in (root/name/'scripts').glob('*.py'):
            text = script.read_text(encoding='utf-8-sig')
            if re.search(r'^\s*(?:from|import) (?:tools|robotics_)', text, re.M):
                problems.append(f'{script}: cross-repository runtime dependency')
    for path in [root/'README.md', *root.glob('docs/*.md')]:
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if target.startswith(('http:', 'https:', '#', 'mailto:')):
                continue
            rel = target.split('#')[0]
            if rel and not (path.parent/rel).exists():
                problems.append(f'{path.name}: missing link {target}')
    cases = json.loads((root/'tests/routing_cases.json').read_text(encoding='utf-8'))['cases']
    ids = set()
    for case in cases:
        if case['id'] in ids:
            problems.append('duplicate routing ID')
        ids.add(case['id'])
        if any(s not in skills for s in case['acceptable_skills']):
            problems.append(f"{case['id']}: unknown routed skill")
    return problems


def main():
    issues = check()
    skills = inventory()
    print(json.dumps({'status': 'fail' if issues else 'pass', 'skills': len(skills),
                      'installer_targets': len(TARGETS), 'discovery_description_characters': sum(len(k)+len(v) for k,v in skills.items()),
                      'limitations': ['Description characters are not token measurements.', 'Native client discovery and behavioral routing require client tests.'],
                      'findings': issues}, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == '__main__':
    # Stable UTF-8 JSON even when a Windows coding agent captures pipes.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    sys.exit(main())
