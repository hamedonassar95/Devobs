import test from 'node:test';
import assert from 'node:assert/strict';
import { PUBLIC_TARGETS } from '../assets/public-ci/portfolio-api.mjs';
import { inspectAndAnalyzePublicCi, main } from '../scripts/portfolio_ci_ai7_live.mjs';

const SHA = 'a'.repeat(40);
const BEFORE = 'b'.repeat(40);
const TIME = '2026-11-16T17:00:00Z';
const OUTCOMES = ['success', 'failure', 'timed_out', 'cancelled'];
function mockResponse(url, payload, code = 200, headers = {}) {
  const r = Response.json(payload, { status: code, headers });
  Object.defineProperty(r, 'url', { value: url });
  return r;
}
function makeFetcher({
  outcomes = OUTCOMES, missing = new Set(), stale = new Set(),
  noAttempt = new Set(), unavailable = new Set(), foreign = new Set(),
  requests = [],
} = {}) {
  return async (url, options) => {
    requests.push({ url, options });
    const target = PUBLIC_TARGETS.find(x => url.startsWith('https://api.github.com/repos/' + x.repo + '/'));
    assert.ok(target, 'no unapproved repository may be fetched');
    assert.equal(options.method, 'GET');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    const index = PUBLIC_TARGETS.indexOf(target);
    if (unavailable.has(index)) return mockResponse(url, { privatePayload: 'SECRET_NOT_EXPORTED' }, 403,
      { 'x-ratelimit-remaining': '0' });
    if (url.includes('/branches/')) return mockResponse(url, {
      name: target.branch, commit: { sha: stale.has(index) ? BEFORE : SHA },
    });
    if (missing.has(index)) return mockResponse(url, { total_count: 0, workflow_runs: [] });
    return mockResponse(url, {
      total_count: 1, workflow_runs: [{
        id: 400 + index,
        ...(noAttempt.has(index) ? {} : { run_attempt: 2 }),
        created_at: TIME,
        path: '.github/workflows/ci.yml',
        head_branch: target.branch,
        event: 'push',
        head_sha: SHA,
        status: 'completed',
        conclusion: outcomes[index],
        repository: { full_name: foreign.has(index) ? 'other/foreign' : target.repo, private: false },
        head_repository: { full_name: target.repo, private: false },
        name: 'SECRET_NOT_EXPORTED',
        privatePayload: 'SECRET_NOT_EXPORTED',
      }],
    });
  };
}

test('one explicit call fetches exactly four approved public repos and analyzes real AI-7', async () => {
  const requests = [];
  const output = await inspectAndAnalyzePublicCi(makeFetcher({ requests }));
  assert.equal(requests.length, 8);
  assert.equal(output.checked_count, 4);
  assert.equal(output.eligible_count, 4);
  assert.equal(output.excluded_count, 0);
  assert.equal(output.status, 'complete_observation');
  assert.equal(output.read_only, true);
  assert.equal(output.production_ready, false);
  assert.equal(output.external_provenance_verified, false);
  assert.deepEqual(output.observations.map(x => x.repository), PUBLIC_TARGETS.map(x => x.repo));
  assert.deepEqual(output.observations.map(x => x.status), OUTCOMES);
  assert.ok(output.observations.every(x => x.analysis_eligible));
  assert.equal(output.analysis.summary.ci_event_count, 4);
  assert.equal(output.analysis.summary.failed_ci_count, 2);
  assert.equal(output.analysis.summary.recommendation_count, 0);
  assert.deepEqual(output.analysis.pipeline.map(x => x.id),
    ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7']);
  assert.equal(output.analysis.pipeline[2].status, 'no_logs');
  assert.equal(output.analysis.pipeline[3].status, 'no_matches');
  assert.doesNotMatch(JSON.stringify(output), /SECRET_NOT_EXPORTED|privatePayload|token/);
});

test('stale, unavailable, and missing attempt are excluded but never reported green', async () => {
  const requests = [];
  const report = await inspectAndAnalyzePublicCi(makeFetcher({
    requests, stale: new Set([0]), unavailable: new Set([1]), noAttempt: new Set([2]),
  }));
  assert.equal(report.status, 'partial_observation');
  assert.equal(report.eligible_count, 1);
  assert.equal(report.excluded_count, 3);
  assert.deepEqual(report.observations.map(x => x.status), ['stale', 'unverified', 'timed_out', 'cancelled']);
  assert.deepEqual(report.observations.map(x => x.analysis_eligible), [false, false, false, true]);
  assert.equal(report.analysis.summary.ci_event_count, 1);
  assert.equal(report.analysis.summary.missing_project_count, 3);
  assert.equal(requests.length, 7, 'rate-limited repo stops after one GET');
  assert.doesNotMatch(JSON.stringify(report), /SECRET_NOT_EXPORTED/);
});

test('no eligible CI run produces explicit no-evidence report, never a fabricated AI-7 snapshot', async () => {
  const data = await inspectAndAnalyzePublicCi(makeFetcher({ missing: new Set([0, 1, 2, 3]) }));
  assert.equal(data.status, 'no_eligible_evidence');
  assert.equal(data.eligible_count, 0);
  assert.equal(data.excluded_count, 4);
  assert.equal(data.analysis, null);
  assert.deepEqual(data.observations.map(x => x.status), Array(4).fill('missing'));
});

test('foreign repository data fails closed for its project and does not leak provider contents', async () => {
  const data = await inspectAndAnalyzePublicCi(makeFetcher({ foreign: new Set([3]) }));
  assert.equal(data.status, 'partial_observation');
  assert.equal(data.observations[3].status, 'unverified');
  assert.equal(data.eligible_count, 3);
  assert.equal(data.analysis.summary.ci_event_count, 3);
  assert.doesNotMatch(JSON.stringify(data), /other\/foreign|SECRET_NOT_EXPORTED/);
});

test('help and unknown arguments never invoke GitHub or AI-7', async t => {
  const oldStdout = process.stdout.write;
  const oldStderr = process.stderr.write;
  const printed = [];
  process.stdout.write = s => { printed.push(s); return true; };
  process.stderr.write = s => { printed.push(s); return true; };
  t.after(() => {
    process.stdout.write = oldStdout;
    process.stderr.write = oldStderr;
  });
  const never = () => { throw Error('fetch must not be invoked'); };
  assert.equal(await main(['--help'], never), 0);
  assert.equal(await main(['--token', 'anything'], never), 2);
  assert.deepEqual(printed.map(x => x.includes('usage:') || x.includes('invalid_arguments')), [true, true]);
});
