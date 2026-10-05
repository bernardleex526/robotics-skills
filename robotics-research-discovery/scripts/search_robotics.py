#!/usr/bin/env python3
"""Bounded public discovery, not a ranking engine or proof of reproducibility."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import math
import tempfile
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

MAX_BYTES = 4 * 1024 * 1024
ATOM = {'a': 'http://www.w3.org/2005/Atom'}


def utcnow():
    return datetime.now(timezone.utc)


def request_bytes(url, *, token=None, opener=urlopen, sleep=time.sleep):
    headers = {'User-Agent': 'robotics-skills-discovery/1.0', 'Accept': 'application/json, application/atom+xml'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    for attempt in range(3):
        try:
            with opener(Request(url, headers=headers), timeout=20) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError('response exceeds size limit')
                return data
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                # Deliberately bounded; do not sleep arbitrarily from a server header.
                sleep(3 * (attempt + 1))
                continue
            raise ValueError('HTTP ' + str(exc.code)) from None
        except (URLError, TimeoutError, OSError):
            if attempt < 2:
                sleep(3 * (attempt + 1))
                continue
            raise ValueError('network unavailable or timed out') from None
    raise ValueError('request failed')


def parse_arxiv(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('XML declarations not accepted')
    root = ET.fromstring(data)
    if root.tag != '{http://www.w3.org/2005/Atom}feed':
        raise ValueError('unexpected arXiv feed')
    result = []
    for entry in root.findall('a:entry', ATOM):
        def text(key):
            return ' '.join((entry.findtext('a:' + key, default='', namespaces=ATOM)).split())
        identifier = text('id')
        if '/api/errors' in identifier:
            raise ValueError('arXiv rejected query')
        result.append({'id': identifier, 'title': text('title'), 'url': identifier,
                       'first_published': text('published'), 'updated': text('updated'),
                       'authors': [a.findtext('a:name', default='', namespaces=ATOM) for a in entry.findall('a:author', ATOM)],
                       'abstract': text('summary')[:3000], 'kind': 'paper'})
    return result


def parse_github(data):
    payload = json.loads(data)
    if not isinstance(payload, dict) or not isinstance(payload.get('items'), list):
        raise ValueError('unexpected GitHub payload')
    result = []
    for item in payload['items']:
        if not isinstance(item, dict) or not isinstance(item.get('full_name'), str) or not isinstance(item.get('html_url'), str):
            raise ValueError('invalid GitHub repository record')
        license_info = item.get('license') or {}
        if not isinstance(license_info, dict):
            raise ValueError('invalid GitHub license record')
        result.append({'id': str(item['id']), 'title': item['full_name'], 'url': item['html_url'],
                       'description': (item.get('description') or '')[:1500],
                       'pushed_at': item.get('pushed_at'), 'updated_at': item.get('updated_at'),
                       'archived': item.get('archived'), 'stars': item.get('stargazers_count'),
                       'license_spdx': license_info.get('spdx_id'), 'kind': 'repository',
                       'officiality': 'unverified', 'build_status': 'not_tested'})
    return result, bool(payload.get('incomplete_results', False))


def urls(query, limit, days, now, paper_sort="submitted"):
    if paper_sort not in ("submitted", "updated"):
        raise ValueError("invalid paper sort")
    # Treat user input as words, not provider query syntax.
    words = ['"' + word.replace('"', '').replace('\\', '') + '"' for word in query.split()]
    arxiv = ' AND '.join('all:' + word for word in words)
    github = ' '.join(words) + ' archived:false'
    if days is not None:
        since = now - timedelta(days=days)
        arxiv += ' AND submittedDate:[' + since.strftime('%Y%m%d0000') + ' TO ' + now.strftime('%Y%m%d2359') + ']'
        github += ' pushed:>=' + since.strftime('%Y-%m-%d')
    return {
        'arxiv': 'https://export.arxiv.org/api/query?' + urlencode({'search_query': arxiv, 'start': 0, 'max_results': limit, 'sortBy': 'submittedDate' if paper_sort == 'submitted' else 'lastUpdatedDate', 'sortOrder': 'descending'}),
        'github': 'https://api.github.com/search/repositories?' + urlencode({'q': github, 'sort': 'updated', 'order': 'desc', 'per_page': limit})}


def discover(query, *, limit=10, days=None, cache_dir=None, offline=False, refresh=False, ttl_hours=24, fetch=request_bytes, now=None, paper_sort="submitted"):
    now = now or utcnow()
    query = query.strip()
    if not query or len(query) > 300 or not 1 <= limit <= 50 or (days is not None and not 1 <= days <= 36500) or not math.isfinite(ttl_hours) or not 0 <= ttl_hours <= 8760:
        raise ValueError('invalid query, result limit, date window or cache TTL')
    if offline and refresh:
        raise ValueError('offline and refresh are mutually exclusive')
    request_urls = urls(query, limit, days, now, paper_sort)
    parameters = {'query': query, 'limit': limit, 'days': days, 'paper_sort': paper_sort}
    # Stable key permits offline access across dates; retain original URLs and fetched_at.
    key = hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
    cache = Path(cache_dir) / (key + '.json') if cache_dir else None
    if offline and cache is None:
        raise ValueError('offline requires cache directory')
    if cache and cache.is_file() and not refresh:
        try:
            old = json.loads(cache.read_text(encoding='utf-8'))
            age = (now - datetime.fromisoformat(old['fetched_at'])).total_seconds()
            if old.get('schema_version') == 1 and old.get('parameters') == parameters and old.get('status') == 'ok' and (offline or 0 <= age <= ttl_hours * 3600):
                old.update(cache_hit=True, offline=offline, observed_at=now.isoformat())
                return old
        except (ValueError, KeyError, TypeError, OSError):
            pass
    result = {'schema_version': 1, 'query': query, 'parameters': parameters, 'request_urls': request_urls,
              'fetched_at': now.isoformat(), 'observed_at': now.isoformat(), 'cache_hit': False,
              'offline': offline, 'sources': {}, 'status': 'ok',
              'limitations': ['Bounded discovery, not exhaustive or quality-ranked.', 'Paper/code officiality, license terms and buildability require human/agent review.', 'days filters first submission, even when sorting updated; omit days to discover revisions of older papers.']}
    for name, url in request_urls.items():
        try:
            if offline:
                raise ValueError('no valid cached result; network disabled')
            data = fetch(url, token=os.environ.get('GITHUB_TOKEN') if name == 'github' else None)
            if name == 'github':
                items, incomplete = parse_github(data)
            else:
                items, incomplete = parse_arxiv(data), False
            # Deduplicate provider IDs and bound output even if API ignores the limit.
            unique = {item['id']: item for item in items}
            result['sources'][name] = {'status': 'ok', 'items': list(unique.values())[:limit], 'incomplete_results': incomplete}
        except (ValueError, ET.ParseError, KeyError, TypeError, OSError) as exc:
            result['sources'][name] = {'status': 'error', 'error': str(exc)[:200], 'items': []}
    failures = sum(s['status'] != 'ok' for s in result['sources'].values())
    result['status'] = 'error' if failures == 2 else 'partial' if failures else 'ok'
    # Cache successes only: failed refresh must not replace known-good evidence.
    if cache and result['status'] == 'ok':
        cache.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=cache.parent, suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        try:
            temporary.replace(cache)
        finally:
            temporary.unlink(missing_ok=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', required=True)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--days', type=int, help='First-submission window for papers; pushed window for repositories')
    parser.add_argument('--paper-sort', choices=['submitted', 'updated'], default='submitted')
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--ttl-hours', type=float, default=24)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    output = args.output
    try:
        if output and output.exists():
            raise ValueError('refusing to overwrite existing output')
        result = discover(args.query, limit=args.limit, days=args.days, cache_dir=args.cache_dir,
                          offline=args.offline, refresh=args.refresh, ttl_hours=args.ttl_hours, paper_sort=args.paper_sort)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        else:
            print(text)
        return 0 if result['status'] == 'ok' else 1
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'invalid', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    # Stable UTF-8 JSON even when a Windows coding agent captures pipes.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
