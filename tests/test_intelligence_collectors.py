"""Fixture-only read-only evidence retrieval with fail-closed validation."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from devobs_intelligence.collectors import CollectorError, collect_pipeline, _NoRedirect, _http_get

NOW = '2026-10-25T12:00:00Z'


def gitlab(path, token):
    if path == 'projects/42':
        return {'id': 42, 'default_branch': 'main'}
    if path == 'projects/42/repository/branches/main':
        return {'name': 'main', 'commit': {'id': 'a' * 40}}
    if path == 'projects/42/pipelines?ref=main&per_page=1&order_by=id&sort=desc':
        return [{'id': 100, 'project_id': 42, 'ref': 'main', 'sha': 'a'*40, 'status': 'success'}]
    raise AssertionError(path)


def github(path, token):
    if path == 'repos/sample/demo':
        return {'full_name':'sample/demo', 'default_branch':'main'}
    if path == 'repos/sample/demo/branches/main':
        return {'name':'main', 'commit': {'sha':'a'*40}}
    if path == 'repos/sample/demo/actions/runs?branch=main&per_page=20':
        return {'workflow_runs':[{'id':200, 'name':'CI', 'head_branch':'main', 'head_sha':'a'*40,
                                  'status':'completed', 'conclusion':'success'}]}
    raise AssertionError(path)


class CollectorTests(unittest.TestCase):
    def test_gitlab_success_sha_pinned_and_private(self):
        report = collect_pipeline('gitlab', '42', NOW, fetcher=gitlab, token='synthetic-only')
        self.assertEqual(report.ci_state, 'success')
        self.assertEqual(report.event.source_sha, 'a'*40)
        self.assertNotIn('"project_ref":"42"', report.to_json())
        self.assertNotIn('synthetic-only', report.to_json())

    def test_github_success_sha_pinned(self):
        report = collect_pipeline('github','sample/demo',NOW,fetcher=github)
        self.assertEqual(report.ci_state,'success')
        self.assertEqual(report.event.provider,'github')
        self.assertNotIn('sample/demo',report.to_json())

    def test_stale_pipeline_not_success(self):
        def fake(path, token):
            value=gitlab(path,token)
            if 'pipelines?' in path: return [{**value[0],'sha':'b'*40}]
            return value
        self.assertEqual(collect_pipeline('gitlab','42',NOW,fetcher=fake,token='token').ci_state,'stale')

    def test_missing_pipeline_no_false_success(self):
        def fake(path, token):
            return [] if 'pipelines?' in path else gitlab(path,token)
        self.assertEqual(collect_pipeline('gitlab','42',NOW,fetcher=fake,token='token').ci_state,'missing')

    def test_github_stale_run_not_success(self):
        def fake(path, token):
            obj=github(path,token)
            if '/actions/runs' in path: return {'workflow_runs':[{**obj['workflow_runs'][0],'head_sha':'b'*40}]}
            return obj
        self.assertEqual(collect_pipeline('github','sample/demo',NOW,fetcher=fake).ci_state,'stale')

    def test_untrusted_project_and_broken_responses(self):
        for provider,project,token in [('github','../passwd',None),('github','other/a?x=1',None),('gitlab','../../42','token'),('gitlab','42','')]:
            with self.subTest(project=project), self.assertRaises(CollectorError):
                collect_pipeline(provider,project,NOW,fetcher=lambda *a:None,token=token)
        with self.assertRaises(CollectorError):
            collect_pipeline('gitlab','42',NOW,fetcher=lambda *a: {'password':'not logged'},token='token')

    def test_transport_failure_has_safe_message(self):
        for error in (RuntimeError('PRIVATE-SECRET'), TimeoutError('PRIVATE-SECRET')):
            with self.subTest(error=type(error).__name__), self.assertRaises(CollectorError) as caught:
                collect_pipeline('github','sample/demo',NOW,fetcher=lambda *_: (_ for _ in ()).throw(error))
            self.assertNotIn('PRIVATE-SECRET',str(caught.exception))

    def test_unknown_provider_type_is_rejected(self):
        with self.assertRaises(CollectorError):
            collect_pipeline([], 'sample/demo', NOW)

    def test_invalid_gitlab_status_rejected_even_when_stale(self):
        def fake(path, token):
            obj=gitlab(path,token)
            return [{**obj[0], 'sha':'b'*40, 'status':'unrecognized'}] if 'pipelines?' in path else obj
        with self.assertRaises(CollectorError):
            collect_pipeline('gitlab','42',NOW,fetcher=fake,token='token')

    def test_transport_rejects_http_error_and_oversize(self):
        from unittest import mock
        from urllib.error import HTTPError
        with mock.patch('devobs_intelligence.collectors.build_opener') as opener:
            opener.return_value.open.side_effect=HTTPError('https://gitlab.com',429,'rate limited',{},None)
            with self.assertRaisesRegex(CollectorError,'upstream_unavailable'):
                _http_get('gitlab','projects/42','fake-token')

        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*_): return False
            def geturl(self): return 'https://gitlab.com/api/v4/projects/42'
            def read(self, n): return b'x'*n
        with mock.patch('devobs_intelligence.collectors.build_opener') as opener:
            opener.return_value.open.return_value=Response()
            with self.assertRaisesRegex(CollectorError,'oversized_response'):
                _http_get('gitlab','projects/42','fake-token')

    def test_no_redirect(self):
        self.assertIsNone(_NoRedirect().redirect_request(None,None,302,'',{},'https://example.org'))

    def test_mismatched_identity_rejected(self):
        def fake(path, token):
            obj=gitlab(path,token)
            return {'id':99,'default_branch':'main'} if path=='projects/42' else obj
        with self.assertRaises(CollectorError):
            collect_pipeline('gitlab','42',NOW,fetcher=fake,token='token')

if __name__=='__main__': unittest.main()
