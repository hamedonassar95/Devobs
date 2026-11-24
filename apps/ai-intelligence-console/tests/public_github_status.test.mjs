import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createPublicGithubStatusHandler, ALLOWED_GITHUB_REPOSITORIES } from '../publicGithubStatus.ts';

const REPO = 'hamedonassar95/Devobs';
const SHA = 'a'.repeat(40);
const BRANCH_URL = `https://api.github.com/repos/${REPO}/branches/main`;
const RUNS_URL = `https://api.github.com/repos/${REPO}/actions/workflows/ci.yml/runs?branch=main&event=push&per_page=1`;
const OBSERVED_AT = '2026-11-24T10:00:00.000Z';
const APP_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
let vite;
let RepositoryDatabaseMapPanel;

before(async () => {
  vite = await createServer({ configFile: false, root: APP_ROOT, envDir: false,
    server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ RepositoryDatabaseMapPanel } = await vite.ssrLoadModule('/src/components/github/RepositoryDatabaseMapPanel.tsx'));
});
after(async () => vite?.close());

function branch(sha = SHA) { return { name: 'main', commit: { sha } }; }
function run(fields = {}) {
  return { id: 123, workflow_id: 456, path: '.github/workflows/ci.yml', event: 'push', head_branch: 'main', head_sha: SHA,
    status: 'completed', conclusion: 'success', repository: { full_name: REPO, private: false },
    head_repository: { full_name: REPO, private: false }, ...fields };
}
function response(value, url, { status = 200, headers = {} } = {}) {
  const body = typeof value === 'string' ? value : JSON.stringify(value);
  const result = new Response(body, { status, headers: { 'Content-Type': 'application/json; charset=utf-8', ...headers } });
  Object.defineProperty(result, 'url', { value: url });
  return result;
}
function request({ method = 'GET', repository = REPO, extras = {}, host = '127.0.0.1:3000',
  origin, site, localAddress = '127.0.0.1' } = {}) {
  const query = { ...extras };
  if (repository !== undefined) query.repository = repository;
  const headers = { host, origin, 'sec-fetch-site': site };
  return { method, query, socket: { localAddress }, get: name => headers[name.toLowerCase()] };
}
async function invoke(handler, req = request()) {
  const res = {
    statusCode: 200, headers: {}, body: undefined,
    set(name, value) { if (typeof name === 'object') Object.assign(this.headers, name); else this.headers[name] = value; return this; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
  };
  await handler(req, res);
  return res;
}
function successfulFetcher({ branchPayload = branch(), runsPayload = { total_count: 1, workflow_runs: [run()] } } = {}) {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    if (url === BRANCH_URL) return response(branchPayload, url);
    if (url === RUNS_URL) return response(runsPayload, url);
    throw new Error('unexpected_fixed_url');
  };
  return { fetchImpl, calls };
}
function handler(fetchImpl, extra = {}) {
  return createPublicGithubStatusHandler({ enabled: true, fetchImpl, clock: () => new Date(OBSERVED_AT), ...extra });
}

test('matching public CI result is observed with fixed anonymous GETs and timestamp', async () => {
  const { fetchImpl, calls } = successfulFetcher();
  const result = await invoke(handler(fetchImpl));
  assert.equal(result.statusCode, 200);
  assert.deepEqual(result.body, { repository: REPO, status: 'OBSERVED', branch: 'main', commitSha: SHA,
    ciConclusion: 'success', runStatus: 'completed', observedAt: OBSERVED_AT, cached: false, reason: null });
  assert.deepEqual(calls.map(call => call.url), [BRANCH_URL, RUNS_URL]);
  for (const { options } of calls) {
    assert.equal(options.method, 'GET');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.referrerPolicy, 'no-referrer');
    assert.ok(options.signal instanceof AbortSignal);
    assert.deepEqual(options.headers, {
      Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
    });
  }
  assert.equal(result.headers['Cache-Control'], 'no-store');
});

test('repository without verified public visibility stays visible but is never queried', async () => {
  let calls = 0;
  const result = await invoke(handler(async () => { calls++; throw new Error(); }),
    request({ repository: 'hamedonassar95/DevObs-ai-Intelligence-' }));
  assert.equal(result.statusCode, 503);
  assert.equal(result.body.status, 'UNVERIFIED');
  assert.equal(result.body.reason, 'public_visibility_unverified');
  assert.equal(calls, 0);
});

test('disabled, non-loopback and foreign-origin requests never reach GitHub', async () => {
  let calls = 0;
  const fetchImpl = async () => { calls++; throw new Error(); };
  const disabled = await invoke(createPublicGithubStatusHandler({ enabled: false, fetchImpl }));
  assert.equal(disabled.body.reason, 'disabled');
  const exposed = await invoke(createPublicGithubStatusHandler({ enabled: true, bindHost: '0.0.0.0', fetchImpl }));
  assert.equal(exposed.body.status, 'UNVERIFIED');
  assert.equal(exposed.body.reason, 'non_loopback_bind');
  const foreign = await invoke(handler(fetchImpl), request({ origin: 'http://attacker.invalid', site: 'cross-site' }));
  assert.equal(foreign.statusCode, 403);
  assert.equal(foreign.body.status, 'UNVERIFIED');
  assert.equal(foreign.body.reason, 'request_denied');
  assert.equal(calls, 0);
});

test('failed conclusions stay failed and pending runs never become success', async () => {
  const failure = successfulFetcher({ runsPayload: { total_count: 1, workflow_runs: [run({ conclusion: 'failure' })] } });
  const failed = await invoke(handler(failure.fetchImpl));
  assert.equal(failed.body.status, 'OBSERVED');
  assert.equal(failed.body.ciConclusion, 'failure');
  for (const status of ['queued', 'in_progress']) {
    const pending = successfulFetcher({ runsPayload: { total_count: 1, workflow_runs: [run({ status, conclusion: null })] } });
    const result = await invoke(handler(pending.fetchImpl));
    assert.equal(result.body.status, 'PENDING');
    assert.equal(result.body.ciConclusion, 'pending');
    assert.equal(result.body.runStatus, status === 'in_progress' ? 'in_progress' : 'pending');
  }
});

test('empty runs, stale runs, and incomplete results are UNVERIFIED', async () => {
  const empty = successfulFetcher({ runsPayload: { total_count: 0, workflow_runs: [] } });
  const noRuns = await invoke(handler(empty.fetchImpl));
  assert.equal(noRuns.body.status, 'UNVERIFIED');
  assert.equal(noRuns.body.reason, 'no_runs');
  assert.equal(noRuns.body.ciConclusion, null);
  const stale = successfulFetcher({ runsPayload: { total_count: 1, workflow_runs: [run({ head_sha: 'b'.repeat(40) })] } });
  const staleResult = await invoke(handler(stale.fetchImpl));
  assert.equal(staleResult.body.status, 'UNVERIFIED');
  assert.equal(staleResult.body.reason, 'no_matching_ci_run');
});

test('HTTP errors and rate limits become UNVERIFIED without exposing upstream bodies', async () => {
  const result = await invoke(handler(async url => response('PRIVATE_SENTINEL', url, { status: 500 })));
  assert.equal(result.statusCode, 503);
  assert.equal(result.body.status, 'UNVERIFIED');
  assert.equal(result.body.reason, 'upstream_unavailable');
  assert.doesNotMatch(JSON.stringify(result.body), /PRIVATE_SENTINEL/);
  for (const options of [
    { status: 429 }, { status: 403, headers: { 'X-RateLimit-Remaining': '0' } },
  ]) {
    const result = await invoke(handler(async url => response({}, url, options)));
    assert.equal(result.statusCode, 429);
    assert.equal(result.body.status, 'UNVERIFIED');
    assert.equal(result.body.reason, 'rate_limited');
  }
});

test('timeouts abort requests and return UNVERIFIED', async () => {
  const fetchImpl = (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), { once: true });
  });
  const result = await invoke(handler(fetchImpl, { timeoutMs: 5 }));
  assert.equal(result.statusCode, 504);
  assert.equal(result.body.status, 'UNVERIFIED');
  assert.equal(result.body.reason, 'timeout');
});

test('malformed JSON and unexpected schemas are UNVERIFIED', async () => {
  const malformed = await invoke(handler(async url => response('{bad', url)));
  assert.equal(malformed.statusCode, 502);
  assert.equal(malformed.body.status, 'UNVERIFIED');
  assert.equal(malformed.body.reason, 'invalid_response');
  const incomplete = successfulFetcher({ runsPayload: { total_count: 1, workflow_runs: [] } });
  const result = await invoke(handler(incomplete.fetchImpl));
  assert.equal(result.body.status, 'UNVERIFIED');
  assert.equal(result.body.reason, 'invalid_response');
});

test('arbitrary repository names, URLs, extra query data and non-GET methods are rejected', async () => {
  assert.deepEqual([...ALLOWED_GITHUB_REPOSITORIES], ['hamedonassar95/Devobs', 'hamedonassar95/ops',
    'hamedonassar95/DevObs-ai-Intelligence-', 'hamedonassar95/devobs-saas']);
  let calls = 0;
  const requestHandler = handler(async () => { calls++; throw new Error(); });
  for (const req of [
    request({ repository: 'https://api.github.com/repos/owner/repo' }),
    request({ repository: 'other/repo' }),
    request({ repository: REPO, extras: { url: 'https://example.invalid' } }),
    request({ repository: REPO, method: 'POST' }),
  ]) {
    const result = await invoke(requestHandler, req);
    assert.ok([400, 405].includes(result.statusCode));
    assert.equal(result.body.status, 'UNVERIFIED');
  }
  assert.equal(calls, 0);
});

test('same allowlisted result is cached for repeated manual checks', async () => {
  const { fetchImpl, calls } = successfulFetcher();
  const requestHandler = handler(fetchImpl);
  const first = await invoke(requestHandler);
  const second = await invoke(requestHandler);
  assert.equal(first.body.cached, false);
  assert.equal(second.body.cached, true);
  assert.equal(second.body.observedAt, first.body.observedAt);
  assert.equal(calls.length, 2);
});

test('topology panel labels its static snapshot and does not poll during render', t => {
  let calls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { calls++; throw new Error('unexpected_auto_request'); };
  t.after(() => { globalThis.fetch = originalFetch; });
  const html = renderToStaticMarkup(React.createElement(RepositoryDatabaseMapPanel));
  assert.equal((html.match(/Check GitHub CI/g) ?? []).length, 4);
  assert.match(html, /checked-in snapshot/);
  assert.match(html, /Not real-time/);
  assert.match(html, /UNVERIFIED · Not checked in this session/);
  assert.equal(calls, 0);
});
