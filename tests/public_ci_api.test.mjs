import assert from 'node:assert/strict';
import test from 'node:test';

let api;
try { api = await import('../assets/public-ci/api.mjs'); }
catch (error) { if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error; }
const OWNER = 'hamedonassar95/Devobs';
const HEAD_URL = 'https://api.github.com/repos/' + OWNER + '/branches/main';
const RUNS_URL = 'https://api.github.com/repos/' + OWNER + '/actions/workflows/ci.yml/runs?branch=main&event=push&per_page=1';
const SHA = 'a'.repeat(40);
const head = () => ({ name: 'main', commit: { sha: SHA } });
function runs() {
  return { total_count: 1, workflow_runs: [{ id: 123, run_number: 4, workflow_id: 374991651,
    name: 'CI', path: '.github/workflows/ci.yml', event: 'push', head_branch: 'main', head_sha: SHA,
    status: 'completed', conclusion: 'success', updated_at: '2026-11-16T01:02:03Z',
    html_url: 'https://untrusted.example.invalid/PRIVATE_SENTINEL',
    repository: { full_name: OWNER, private: false }, head_repository: { full_name: OWNER, private: false } }] };
}
function normalize(h = head(), r = runs()) {
  assert.equal(typeof api?.normalizePublicCiEvidence, 'function', 'public CI reader must be implemented');
  return api.normalizePublicCiEvidence(h, r);
}
function response(value, url, options = {}) {
  const r = new Response(typeof value === 'string' || value instanceof Uint8Array || value instanceof ReadableStream
    ? value : JSON.stringify(value), { status: options.status ?? 200,
  headers: { 'Content-Type': 'application/json; charset=utf-8', ...options.headers } });
  Object.defineProperty(r, 'url', { value: url });
  if (options.redirected) Object.defineProperty(r, 'redirected', { value: true });
  return r;
}
const fetchGood = async url => response(url === HEAD_URL ? head() : runs(), url);
async function read(fetcher = fetchGood) {
  assert.equal(typeof api?.fetchPublicCi, 'function', 'public CI transport must be implemented');
  return api.fetchPublicCi(fetcher);
}

test('public matching CI evidence is bounded and links only to the fixed GitHub run', () => {
  assert.deepEqual(normalize(), { state: 'success', mainSha: SHA, runSha: SHA, runId: 123, runNumber: 4,
    updatedAt: '2026-11-16T01:02:03Z', runUrl: 'https://github.com/' + OWNER + '/actions/runs/123',
    status: 'completed', conclusion: 'success', matchesHead: true });
  assert.doesNotMatch(JSON.stringify(normalize()), /PRIVATE_SENTINEL|untrusted/);
});

test('old successful revisions are stale and cannot appear as current successful CI', () => {
  const r = runs(); r.workflow_runs[0].head_sha = 'b'.repeat(40);
  const result = normalize(head(), r); assert.equal(result.state, 'stale'); assert.equal(result.matchesHead, false);
});

test('pending, running and non-success conclusions remain distinct', () => {
  for (const status of ['queued', 'waiting', 'pending', 'requested']) {
    const r = runs(); Object.assign(r.workflow_runs[0], { status, conclusion: null });
    assert.equal(normalize(head(), r).state, 'pending');
  }
  const r = runs(); Object.assign(r.workflow_runs[0], { status: 'in_progress', conclusion: null });
  assert.equal(normalize(head(), r).state, 'running');
  for (const conclusion of ['failure', 'cancelled', 'timed_out', 'neutral', 'skipped', 'action_required', 'stale', 'startup_failure']) {
    const x = runs(); x.workflow_runs[0].conclusion = conclusion;
    assert.equal(normalize(head(), x).state, conclusion);
  }
  assert.deepEqual(normalize(head(), { total_count: 0, workflow_runs: [] }), { state: 'missing', mainSha: SHA });
});

test('wrong public scope, malformed revisions and contradictory responses fail closed', () => {
  const mutations = [r => r.repository.full_name = 'other/repo', r => r.head_repository.private = true,
    r => r.repository.private = 'false', r => r.workflow_id++, r => r.path = '.github/workflows/other.yml',
    r => r.head_branch = 'feature', r => r.event = 'pull_request', r => r.id = 0,
    r => r.id = Number.MAX_SAFE_INTEGER + 1, r => r.run_number = -1,
    r => r.head_sha = 'bad', r => r.status = null, r => r.status = 'future_state',
    r => r.conclusion = null, r => r.conclusion = 'future_result',
    r => r.status = 'queued', r => r.updated_at = '2026-02-30T00:00:00Z'];
  for (const mutate of mutations) {
    const r = runs(); mutate(r.workflow_runs[0]);
    assert.throws(() => normalize(head(), r), { code: 'invalid_response' });
  }
  for (const h of [{ name: 'feature', commit: { sha: SHA } }, { name: 'main', commit: { sha: 'bad' } }, null]) {
    assert.throws(() => normalize(h), { code: 'invalid_response' });
  }
  assert.throws(() => normalize(head(), { total_count: 1, workflow_runs: [] }), { code: 'invalid_response' });
});

test('transport performs exactly the two fixed anonymous GETs with one abort signal', async () => {
  const calls = [];
  const result = await read(async (url, options) => { calls.push({ url, options }); return fetchGood(url); });
  assert.equal(result.state, 'success'); assert.deepEqual(new Set(calls.map(c => c.url)), new Set([HEAD_URL, RUNS_URL]));
  assert.equal(calls.length, 2); assert.equal(calls[0].options.signal, calls[1].options.signal);
  for (const { options } of calls) {
    assert.equal(options.method, 'GET'); assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error'); assert.equal(options.referrerPolicy, 'no-referrer');
    assert.equal(options.cache, 'no-store'); assert.ok(options.signal instanceof AbortSignal);
    assert.deepEqual(options.headers, { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' });
  }
});

test('HTTP failures and redirect/URL changes never return evidence or upstream messages', async () => {
  for (const [status, headers, code] of [[403, { 'X-RateLimit-Remaining': '0' }, 'rate_limited'],
    [429, {}, 'rate_limited'], [403, {}, 'unavailable'], [404, {}, 'not_available'], [500, {}, 'unavailable']]) {
    await assert.rejects(read(async url => response('PRIVATE_SENTINEL', url, { status, headers })), { code });
  }
  await assert.rejects(read(async url => response({}, url, { redirected: true })), { code: 'invalid_response' });
  await assert.rejects(read(async () => response({}, 'https://other.example.invalid')), { code: 'invalid_response' });
  await assert.rejects(read(async () => { throw new Error('PRIVATE_SENTINEL'); }), { code: 'unavailable' });
});

test('JSON MIME, strict UTF-8, syntax and streaming byte limits are enforced', async () => {
  const bad = [
    url => response('{}', url, { headers: { 'Content-Type': 'text/html' } }),
    url => response(new Uint8Array([0xff]), url), url => response('{bad', url),
    url => response('{}', url, { headers: { 'Content-Length': '65537' } }),
    url => response(new ReadableStream({ start(c) { c.enqueue(new Uint8Array(32768)); c.enqueue(new Uint8Array(32769)); c.close(); } }), url),
  ];
  for (const factory of bad) await assert.rejects(read(async url => factory(url)), { code: 'invalid_response' });
});

test('one overall deadline aborts hanging requests without a retry', async () => {
  let calls = 0;
  await assert.rejects(read((_url, { signal }) => new Promise((_resolve, reject) => {
    calls++; signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), { once: true });
  })), { code: 'timeout' });
  assert.equal(calls, 2);
});

test('the same deadline also cancels stalled response streams', async () => {
  let cancelled = 0;
  await assert.rejects(read(async url => response(new ReadableStream({ cancel() { cancelled++; } }), url)), { code: 'timeout' });
  assert.equal(cancelled, 2);
});
