import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PUBLIC_TARGETS, normalizePublicRun, inspectPublicPortfolio,
} from '../scripts/portfolio_public_ci.mjs';

const SHA = 'a'.repeat(40);
const OLD_SHA = 'b'.repeat(40);
function branch(target, sha = SHA) {
  return { name: target.branch, commit: { sha } };
}
function runs(target, overrides = {}) {
  return {
    total_count: 1,
    workflow_runs: [{
      id: 123, path: '.github/workflows/ci.yml',
      head_branch: target.branch, event: 'push', head_sha: SHA,
      repository: { full_name: target.repo, private: false },
      head_repository: { full_name: target.repo, private: false },
      status: 'completed', conclusion: 'success',
      ...overrides,
    }],
  };
}
function response(url, data, status = 200) {
  const r = Response.json(data, { status });
  Object.defineProperty(r, 'url', { value: url });
  return r;
}
function fixture({ mutateRun, mutateBranch, onCall } = {}) {
  return async (url, options) => {
    onCall?.(url, options);
    const target = PUBLIC_TARGETS.find(t => url.startsWith('https://api.github.com/repos/' + t.repo + '/'));
    assert.ok(target, 'unexpected repository request');
    const isBranch = url.includes('/branches/');
    const data = isBranch ? (mutateBranch?.(target) ?? branch(target))
      : (mutateRun?.(target) ?? runs(target));
    return response(url, data);
  };
}

test('allowlist contains only reviewed public CI repositories', () => {
  assert.deepEqual(PUBLIC_TARGETS.map(x => x.repo), [
    'hamedonassar95/Devobs',
    'hamedonassar95/devobs-saas',
    'hamedonassar95/LiveOps-Integration',
    'hamedonassar95/ops',
  ]);
});

test('four verified public CI results are individually source-bound', async () => {
  const requested = [];
  const summary = await inspectPublicPortfolio(fixture({
    onCall(url, options) {
      requested.push(url);
      assert.equal(options.method, 'GET');
      assert.equal(options.credentials, 'omit');
      assert.equal(options.redirect, 'error');
    },
  }));
  assert.equal(requested.length, 8);
  assert.deepEqual(summary.results.map(r => r.status), Array(4).fill('success'));
  assert.deepEqual(summary.results.map(r => r.run_sha), Array(4).fill(SHA));
  assert.equal(summary.read_only, true);
  assert.equal(summary.private_repositories_queried, false);
  assert.equal(summary.production_ready, false);
  assert.equal(summary.checked_count, 4);
  assert.doesNotMatch(JSON.stringify(summary), /token|password|privatePayload/);
});

test('changed main SHA is stale, never a healthy result', () => {
  const target = PUBLIC_TARGETS[1];
  const row = normalizePublicRun(target, branch(target, OLD_SHA), runs(target));
  assert.equal(row.status, 'stale');
});

test('missing workflow reports missing without a fabricated green result', () => {
  const target = PUBLIC_TARGETS[0];
  const row = normalizePublicRun(target, branch(target), {
    total_count: 0, workflow_runs: [],
  });
  assert.equal(row.status, 'missing');
  assert.equal(row.run_id, null);
});

test('reject foreign repo, private repo, non-push, wrong workflow and invalid SHA', () => {
  const target = PUBLIC_TARGETS[2];
  for (const change of [
    { repository: { full_name: 'other/fork', private: false } },
    { repository: { full_name: target.repo, private: true } },
    { head_repository: { full_name: target.repo, private: true } },
    { event: 'pull_request' },
    { path: '.github/workflows/deploy.yml' },
    { head_sha: 'invalid' },
  ]) {
    assert.throws(() => normalizePublicRun(target, branch(target), runs(target, change)));
  }
});

test('unverified provider responses are isolated per repo without response leakage', async () => {
  const secretText = 'privatePayload';
  const summary = await inspectPublicPortfolio(async (url, options) => {
    if (url.includes('/devobs-saas/')) {
      return response(url, { error: secretText }, 503);
    }
    return fixture()(url, options);
  });
  assert.equal(summary.results[1].status, 'unverified');
  assert.equal(summary.results[1].error, 'invalid_response');
  assert.equal(summary.results[0].status, 'success');
  assert.equal(summary.results[2].status, 'success');
  assert.doesNotMatch(JSON.stringify(summary), /privatePayload/);
});

test('reject redirect, content-type mismatch, oversize and invalid data', async () => {
  const variants = [
    async url => { const r = Response.redirect('https://example.invalid'); Object.defineProperty(r, 'url', { value: url }); return r; },
    async url => {
      const r = new Response('bad', { status: 200, headers: { 'Content-Type': 'text/plain' } });
      Object.defineProperty(r, 'url', { value: url }); return r;
    },
    async url => response(url, { padding: 'x'.repeat(70_000) }),
    async url => response(url, { total_count: 1, workflow_runs: [{}] }),
  ];
  for (const bad of variants) {
    let next = true;
    const result = await inspectPublicPortfolio(async (url, options) => {
      if (next) { next = false; return bad(url); }
      return fixture()(url, options);
    });
    assert.equal(result.results[0].status, 'unverified');
    assert.equal(result.results[0].error, 'invalid_response');
  }
});
