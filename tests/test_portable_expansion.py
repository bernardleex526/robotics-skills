from __future__ import annotations
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SEARCH = load('discovery_test', 'robotics-research-discovery/scripts/search_robotics.py')
INSTALL = load('installer_test', 'tools/install_skills.py')
STAMP = load('timestamp_test', 'robotics-data-replay/scripts/audit_timestamps.py')
FOLLOW = load('follow_test', 'robotics-target-following/scripts/check_follow_trace.py')
ATOM = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>https://arxiv.org/abs/2601.00001v1</id><title> Test Paper </title><published>2026-01-01T00:00:00Z</published><updated>2026-01-02T00:00:00Z</updated><author><name>Example Author</name></author><summary>Test summary</summary></entry></feed>'''
GITHUB = json.dumps({'incomplete_results':False,'items':[{'id':1,'full_name':'author/project','html_url':'https://github.com/author/project','license':None,'archived':False}]}).encode()
NOW = datetime(2026,10,5,tzinfo=timezone.utc)


def fetch(url, **kwargs):
    return GITHUB if 'api.github.com' in url else ATOM


class DiscoveryTests(unittest.TestCase):
    def test_both_sources_and_dates(self):
        result = SEARCH.discover('lidar inertial', fetch=fetch, now=NOW)
        self.assertEqual(result['status'], 'ok')
        paper = result['sources']['arxiv']['items'][0]
        self.assertNotEqual(paper['first_published'], paper['updated'])
        repo = result['sources']['github']['items'][0]
        self.assertIsNone(repo['license_spdx'])
        self.assertEqual(repo['officiality'], 'unverified')

    def test_partial_failure_is_not_empty_success(self):
        def fail_github(url, **kwargs):
            if 'github' in url:
                raise ValueError('HTTP 403')
            return ATOM
        result = SEARCH.discover('slam', fetch=fail_github, now=NOW)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['sources']['github']['status'], 'error')
        self.assertTrue(result['sources']['arxiv']['items'])

    def test_zero_hits_success_has_distinct_status(self):
        def empty(url, **kwargs):
            return b'{"items":[]}' if 'github' in url else b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
        result = SEARCH.discover('unlikely-query', fetch=empty)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['sources']['arxiv']['items'], [])

    def test_offline_without_cache_is_input_error(self):
        with self.assertRaises(ValueError):
            SEARCH.discover('slam', offline=True)

    def test_offline_miss_never_calls_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = SEARCH.discover('slam', offline=True, cache_dir=tmp,
                                     fetch=lambda *a,**k: self.fail('network called'))
            self.assertEqual(result['status'], 'error')

    def test_cache_preserves_original_dates_across_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = SEARCH.discover('slam', days=365, cache_dir=tmp, now=NOW, fetch=fetch)
            cached = SEARCH.discover('slam', days=365, cache_dir=tmp, now=NOW+timedelta(days=3), offline=True,
                                    fetch=lambda *a,**k: self.fail('network called'))
            self.assertTrue(cached['cache_hit'])
            self.assertEqual(cached['fetched_at'], original['fetched_at'])
            self.assertEqual(cached['request_urls'], original['request_urls'])
            self.assertNotEqual(cached['observed_at'], cached['fetched_at'])

    def test_expired_cache_refreshes(self):
        with tempfile.TemporaryDirectory() as tmp:
            SEARCH.discover('slam', cache_dir=tmp, now=NOW, fetch=fetch)
            newer = SEARCH.discover('slam', cache_dir=tmp, now=NOW+timedelta(days=2), fetch=fetch)
            self.assertFalse(newer['cache_hit'])

    def test_forced_refresh_does_not_use_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            SEARCH.discover('slam', cache_dir=tmp, now=NOW, fetch=fetch)
            newer = SEARCH.discover('slam', cache_dir=tmp, now=NOW, fetch=fetch, refresh=True)
            self.assertFalse(newer['cache_hit'])

    def test_failed_refresh_preserves_good_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            SEARCH.discover('slam', cache_dir=tmp, now=NOW, fetch=fetch)
            def failure(*args,**kwargs):
                raise ValueError('offline')
            bad = SEARCH.discover('slam', cache_dir=tmp, now=NOW, fetch=failure, refresh=True)
            cached = SEARCH.discover('slam', cache_dir=tmp, now=NOW, offline=True)
            self.assertEqual(bad['status'], 'error')
            self.assertEqual(cached['status'], 'ok')

    def test_invalid_arguments(self):
        for options in [{'query':''},{'query':'x','limit':0},{'query':'x','limit':51},
                        {'query':'x','days':-1},{'query':'x','ttl_hours':float('nan')},
                        {'query':'x','offline':True,'refresh':True}]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                SEARCH.discover(**options)

    def test_xml_error_and_entity_rejected(self):
        for data in [b'<html/>', b'<!DOCTYPE a><feed/>', b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#x</id></entry></feed>']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                SEARCH.parse_arxiv(data)

    def test_malformed_json_payload(self):
        for data in [b'[]', b'{}', b'{"items":{}}']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                SEARCH.parse_github(data)

    def test_date_filter_is_explicit_and_encoded(self):
        urls = SEARCH.urls('RGB-D SLAM', 3, 30, NOW)
        self.assertIn('submittedDate', urls['arxiv'])
        self.assertIn('pushed', urls['github'])
        self.assertNotIn(' ', urls['github'])

    def test_updated_sort_does_not_invent_search_field(self):
        urls = SEARCH.urls('slam', 3, None, NOW, paper_sort='updated')
        self.assertIn('sortBy=lastUpdatedDate', urls['arxiv'])
        self.assertNotIn('submittedDate', urls['arxiv'])
        self.assertNotIn('lastUpdatedDate%3A', urls['arxiv'])
        with self.assertRaises(ValueError):
            SEARCH.urls('slam', 3, None, NOW, paper_sort='unknown')

    def test_corrupt_cache_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            SEARCH.discover('slam', cache_dir=tmp, now=NOW, fetch=fetch)
            cached = next(Path(tmp).glob('*.json'))
            cached.write_text('{broken', encoding='utf-8')
            result = SEARCH.discover('slam', cache_dir=tmp, now=NOW, offline=True,
                                     fetch=lambda *a,**k: self.fail('network called'))
            self.assertEqual(result['status'], 'error')
            self.assertFalse(result['cache_hit'])

    def test_provider_records_are_validated(self):
        for item in [None, [], {'id':1,'full_name':'x','html_url':'x','license':['MIT']}]:
            with self.subTest(item=item), self.assertRaises(ValueError):
                SEARCH.parse_github(json.dumps({'items':[item]}).encode())

    def test_http_retry_is_bounded(self):
        count = []
        def fail(*a, **k):
            count.append(1)
            raise HTTPError('https://example.invalid',429,'limit',{},None)
        sleeps=[]
        with self.assertRaises(ValueError):
            SEARCH.request_bytes('https://example.invalid',opener=fail,sleep=sleeps.append)
        self.assertEqual(len(count),3)
        self.assertEqual(sleeps,[3,6])

    def test_http_403_not_retried(self):
        calls=[]
        def fail(*a,**k):
            calls.append(1)
            raise HTTPError('https://example.invalid',403,'denied',{},None)
        with self.assertRaises(ValueError):
            SEARCH.request_bytes('https://example.invalid',opener=fail,sleep=lambda x:self.fail('slept'))
        self.assertEqual(len(calls),1)

    def test_timeout_error_redacts_network_details(self):
        def fail(*a,**k):
            raise URLError('credential-like secret')
        with self.assertRaisesRegex(ValueError,'network unavailable') as cm:
            SEARCH.request_bytes('https://example.invalid',opener=fail,sleep=lambda x:None)
        self.assertNotIn('secret',str(cm.exception))

    def test_response_size_bounded(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,size):return b'x'*size
        with self.assertRaisesRegex(ValueError,'size limit'):
            SEARCH.request_bytes('https://example.invalid',opener=lambda *a,**k:Response())

    def test_github_token_never_sent_to_arxiv(self):
        calls=[]
        def capture(url,**kwargs):
            calls.append((url,kwargs.get('token')))
            return fetch(url)
        with patch.dict('os.environ',{'GITHUB_TOKEN':'unit-test-token'}):
            result=SEARCH.discover('slam',fetch=capture)
        self.assertIsNone(next(t for u,t in calls if 'arxiv' in u))
        self.assertEqual(next(t for u,t in calls if 'github' in u),'unit-test-token')
        self.assertNotIn('unit-test-token',json.dumps(result))

    def test_cli_unicode_output_is_utf8_under_ascii_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONIOENCODING='ascii')
            result = subprocess.run([sys.executable, str(ROOT/'robotics-research-discovery/scripts/search_robotics.py'),
                                     '--query', '\u673a\u5668\u4eba\u8ddf\u968f', '--offline', '--cache-dir', tmp],
                                    capture_output=True, env=env)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout.decode('utf-8'))['query'], '\u673a\u5668\u4eba\u8ddf\u968f')

    def test_output_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'result.json';out.write_text('keep')
            with patch.object(SEARCH,'discover',side_effect=AssertionError('network called')):
                self.assertEqual(SEARCH.main(['--query','slam','--output',str(out)]),2)
            self.assertEqual(out.read_text(),'keep')


class InstallerTests(unittest.TestCase):
    def test_inventory_has_complete_release(self):
        self.assertEqual(len(INSTALL.inventory()),24)

    def test_all_targets_dry_run_apply_idempotent(self):
        for target in INSTALL.TARGETS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                p=INSTALL.plan(tmp,target=target)
                self.assertEqual(list(Path(tmp).iterdir()),[])
                self.assertEqual(p['conflicts'],[])
                INSTALL.apply(p)
                again=INSTALL.plan(tmp,target=target)
                self.assertEqual(again['operations'],[])
                self.assertEqual(again['conflicts'],[])
                INSTALL.apply(again)
                self.assertEqual(len(list(p['destination'].glob('*/SKILL.md'))),24)

    def test_modified_skill_blocks_all_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=INSTALL.plan(tmp,skills=['robotics-vln'])
            dest=p['destination']/'robotics-vln/SKILL.md'
            dest.parent.mkdir(parents=True);dest.write_text('user edits')
            p=INSTALL.plan(tmp,skills=['robotics-vln','robotics-slam'])
            self.assertTrue(p['conflicts'])
            with self.assertRaises(ValueError):INSTALL.apply(p)
            self.assertEqual(dest.read_text(),'user edits')
            self.assertFalse((p['destination']/'robotics-slam').exists())

    def test_parent_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for dest in ['../escape',str(Path(tmp).resolve())]:
                with self.subTest(dest=dest),self.assertRaises(ValueError):
                    INSTALL.plan(tmp,destination=dest)

    def test_symlink_destination_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            link=Path(tmp)/'linked'
            try:link.symlink_to(other,target_is_directory=True)
            except OSError:self.skipTest('OS does not allow symlink creation')
            with self.assertRaises(ValueError):INSTALL.plan(tmp,destination='linked/skills')
            self.assertEqual(list(Path(other).iterdir()),[])

    def test_existing_rules_never_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            rule=Path(tmp)/'AGENTS.md';rule.write_text('user-owned instructions')
            INSTALL.apply(INSTALL.plan(tmp,target='generic',skills=['robotics-vln']))
            self.assertEqual(rule.read_text(),'user-owned instructions')

    def test_unknown_skill_and_empty_project_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):INSTALL.plan(tmp,skills=['../../x'])
            with self.assertRaises(ValueError):INSTALL.plan(Path(tmp)/'missing')

    def test_standalone_installed_script_runs_without_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=INSTALL.plan(tmp,target='generic',skills=['robotics-target-following','robotics-research-discovery'])
            INSTALL.apply(p)
            root=p['destination']/'robotics-target-following'
            result=subprocess.run([sys.executable,str(root/'scripts/check_follow_trace.py'),str(root/'assets/trace.example.json')],cwd=tmp,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'],'pass')
            search=p['destination']/'robotics-research-discovery/scripts/search_robotics.py'
            result=subprocess.run([sys.executable,str(search),'--query','slam','--offline','--cache-dir',str(Path(tmp)/'empty-cache')],cwd=tmp,capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'],'error')


class RuntimeTests(unittest.TestCase):
    def test_timestamp_valid_interleaved_topics(self):
        rows=[{'topic':'a','stamp':'1'},{'topic':'b','stamp':'0'},{'topic':'a','stamp':'2'}]
        result=STAMP.audit(rows)
        self.assertEqual(result['status'],'pass')
        self.assertEqual(result['topics']['a']['max_gap_s'],1)

    def test_timestamp_input_order_retained(self):
        result=STAMP.audit([{'topic':'a','stamp':str(t)} for t in [2,1,1,4]],max_gap=2)
        self.assertEqual(result['status'],'fail')
        for key in ['backwards','duplicates','over_threshold']:self.assertEqual(result['topics']['a'][key],1)

    def test_timestamp_future_and_invalid(self):
        self.assertEqual(STAMP.audit([{'topic':'a','stamp':'2','received':'1'}])['status'],'fail')
        for rows in [[],[{'topic':'','stamp':'1'}],[{'topic':'a','stamp':'nan'}]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):STAMP.audit(rows)

    def trace(self):
        return json.loads((ROOT/'robotics-target-following/assets/trace.example.json').read_text())

    def test_follow_valid(self):
        self.assertEqual(FOLLOW.check(self.trace())['status'],'pass')

    def test_follow_stale_future_and_missing_target(self):
        for update in [{'observation_t':0.0},{'observation_t':2.0},{'observation_t':None},{'target_id':None},{'safety_ok':False},{'state':'LOST'}]:
            trace=self.trace();trace['samples'][0].update(update)
            with self.subTest(update=update):self.assertEqual(FOLLOW.check(trace)['status'],'fail')

    def test_follow_reverse_speed_and_yaw_limits(self):
        for update in [{'vx':-2},{'wz':2}]:
            trace=self.trace();trace['samples'][0].update(update)
            self.assertEqual(FOLLOW.check(trace)['status'],'fail')

    def test_follow_invalid_type_and_time(self):
        for update in [{'t':float('nan')},{'safety_ok':'true'},{'state':'TYPO'},{'target_id':42},{'vx':True}]:
            trace=self.trace();trace['samples'][0].update(update)
            with self.subTest(update=update),self.assertRaises(ValueError):FOLLOW.check(trace)
        trace=self.trace();trace['samples'][1]['t']=0.5
        self.assertEqual(FOLLOW.check(trace)['status'],'fail')

    def test_cli_invalid_input_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'bad.json';file.write_text('{}')
            result=subprocess.run([sys.executable,str(ROOT/'robotics-target-following/scripts/check_follow_trace.py'),str(file)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(json.loads(result.stderr)['status'],'invalid')


if __name__ == '__main__':
    unittest.main()
