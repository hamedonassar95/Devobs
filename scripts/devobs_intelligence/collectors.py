"""Bounded read-only, SHA-pinned GitHub/GitLab CI evidence collector."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .contracts import EventEnvelopeV1, EvidenceError, parse_event

ORIGINS = {'github': 'https://api.github.com/', 'gitlab': 'https://gitlab.com/api/v4/'}
_MAX_RESPONSE = 65536
_STATUS = frozenset({'created','waiting_for_resource','preparing','pending','running','success','failed','canceled','skipped','manual','scheduled'})
_REPO = re.compile(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z')


class CollectorError(ValueError):
    """Fixed diagnostic code with no upstream data."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _http_get(provider: str, path: str, token: str | None):
    url = ORIGINS[provider] + path
    headers = {'Accept':'application/json'}
    if token:
        if provider == 'gitlab':
            headers['PRIVATE-TOKEN'] = token
        else:
            headers['Authorization'] = 'Bearer ' + token
    req = Request(url, headers=headers, method='GET')
    try:
        with build_opener(_NoRedirect()).open(req, timeout=10) as response:
            if response.status != 200 or response.geturl() != url:
                raise CollectorError('upstream_rejected')
            body = response.read(_MAX_RESPONSE + 1)
    except (HTTPError, URLError, TimeoutError, OSError):
        raise CollectorError('upstream_unavailable') from None
    if len(body) > _MAX_RESPONSE:
        raise CollectorError('oversized_response')
    try:
        return json.loads(body.decode('utf-8'))
    except (ValueError, UnicodeError):
        raise CollectorError('invalid_response') from None


@dataclass(frozen=True)
class CollectorResultV1:
    ci_state: str
    event: EventEnvelopeV1

    def to_json(self) -> str:
        return json.dumps({'ci_state':self.ci_state,'event':asdict(self.event)},sort_keys=True,separators=(',',':'))


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CollectorError(code)


def _status(raw: str) -> str:
    _require(type(raw) is str and raw in _STATUS, 'invalid_pipeline')
    return raw


def collect_pipeline(provider: str, project: str, observed_at: str, *, fetcher=None,
                     token: str | None = None) -> CollectorResultV1:
    """Collect one default-branch status, not trigger or authorize CI."""
    _require(type(provider) is str and provider in ORIGINS and type(project) is str, 'invalid_scope')
    if provider == 'gitlab':
        _require(project.isascii() and project.isdecimal() and int(project) > 0 and len(project) <= 18, 'invalid_scope')
        _require(type(token) is str and bool(token.strip()), 'missing_auth')
    else:
        _require(_REPO.fullmatch(project) is not None and '..' not in project, 'invalid_scope')
    fetch = _http_get if fetcher is None else (lambda source, path, auth: fetcher(path, auth))

    def get(path: str):
        try:
            return fetch(provider, path, token)
        except CollectorError:
            raise
        except Exception:
            raise CollectorError('upstream_unavailable') from None

    if provider == 'gitlab':
        p = get(f'projects/{project}')
        _require(type(p) is dict and p.get('id') == int(project), 'invalid_project')
        branch = p.get('default_branch')
        _require(type(branch) is str and 0 < len(branch) <= 100, 'invalid_branch')
        ref = quote(branch, safe='')
        b = get(f'projects/{project}/repository/branches/{ref}')
        _require(type(b) is dict and b.get('name') == branch, 'invalid_branch')
        commit = b.get('commit')
        sha = commit.get('id') if type(commit) is dict else None
        runs = get(f'projects/{project}/pipelines?ref={ref}&per_page=1&order_by=id&sort=desc')
        _require(type(runs) is list and len(runs) <= 1, 'invalid_pipeline')
        run = runs[0] if runs else None
        if run is not None:
            _require(type(run) is dict and run.get('project_id') == int(project)
                     and run.get('ref') == branch and type(run.get('id')) is int,
                     'invalid_pipeline')
            status = _status(run.get('status'))
            state = status if run.get('sha') == sha else 'stale'
    else:
        p = get(f'repos/{project}')
        _require(type(p) is dict and p.get('full_name') == project, 'invalid_project')
        branch = p.get('default_branch')
        _require(type(branch) is str and 0 < len(branch) <= 100, 'invalid_branch')
        ref = quote(branch, safe='')
        b = get(f'repos/{project}/branches/{ref}')
        _require(type(b) is dict and b.get('name') == branch, 'invalid_branch')
        commit = b.get('commit')
        sha = commit.get('sha') if type(commit) is dict else None
        results = get(f'repos/{project}/actions/runs?branch={ref}&per_page=20')
        _require(type(results) is dict and type(results.get('workflow_runs')) is list
                 and len(results['workflow_runs']) <= 20, 'invalid_pipeline')
        matches = [r for r in results['workflow_runs'] if type(r) is dict and r.get('name') == 'CI']
        run = matches[0] if matches else None
        if run is not None:
            _require(type(run.get('id')) is int and run.get('head_branch') == branch
                     and run.get('status') in {'completed','queued','in_progress','waiting','pending','requested'}
                     and type(run.get('head_sha')) is str, 'invalid_pipeline')
            state = ('stale' if run.get('head_sha') != sha else
                     ('success' if run.get('status') == 'completed' and run.get('conclusion') == 'success' else
                      'failed' if run.get('status') == 'completed' and run.get('conclusion') in {'failure','timed_out','cancelled'} else
                      'running'))
    _require(type(sha) is str and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',sha) is not None,
             'invalid_source_sha')
    if run is None:
        state = 'missing'
    digest = hashlib.sha256(json.dumps({'provider':provider, 'project':project, 'sha':sha, 'ci_state':state},
                                       sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    try:
        event = parse_event({'schema_version':1,'event_id':'ci-'+digest[:40], 'provider':provider,
                             'project_ref':project,'source_sha':sha,
                             'kind':'pipeline' if provider=='gitlab' else 'workflow_run',
                             'observed_at':observed_at,'evidence_digests':[digest]})
    except EvidenceError:
        raise CollectorError('invalid_event') from None
    return CollectorResultV1(ci_state=state,event=event)
