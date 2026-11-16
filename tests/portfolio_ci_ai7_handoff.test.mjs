import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { PUBLIC_TARGETS, normalizePublicRun } from '../assets/public-ci/portfolio-api.mjs';
import { buildPortfolioCloudEvents } from '../assets/public-ci/portfolio-export.mjs';
import { analyzePortfolioCiJsonl } from '../scripts/portfolio_ci_ai7.mjs';
import { convertText, CI_ALLOWED_SOURCES } from '../scripts/integrations/cloudevents_ci_adapter.mjs';
import { ALLOWED_SOURCES } from '../scripts/integrations/project_sources.mjs';
import { ingestText, readEventStore } from '../scripts/ai_intelligence/event_ingest.mjs';
import { buildDashboardSnapshot } from '../scripts/ai_intelligence/dashboard_server.mjs';

const SHA = 'a'.repeat(40);
const created = '2026-11-16T17:00:00Z';
const outcomes = ['success', 'failure', 'timed_out', 'cancelled'];
function report() {
  return {
    schema_version: 1, scope: 'public_ci_only', read_only: true,
    production_ready: false, private_repositories_queried: false,
    checked_count: 4,
    results: PUBLIC_TARGETS.map((target, i) => normalizePublicRun(target,
      { name: 'main', commit: { sha: SHA } },
      { total_count: 1, workflow_runs: [{
        id: 100 + i, run_attempt: 2, created_at: created,
        path: '.github/workflows/ci.yml', head_branch: 'main', event: 'push',
        head_sha: SHA, status: 'completed', conclusion: outcomes[i],
        repository: { full_name: target.repo, private: false },
        head_repository: { full_name: target.repo, private: false },
        name: 'UNTRUSTED_TITLE_NEVER_EXPORTED',
      }] })),
  };
}

test('ops CI source does not authorize ops for unrelated provider adapters', () => {
  const source = 'https://github.com/hamedonassar95/ops';
  assert.equal(Object.hasOwn(ALLOWED_SOURCES, source), false);
  assert.equal(CI_ALLOWED_SOURCES[source], 'ops');
  assert.equal(Object.keys(ALLOWED_SOURCES).length, 7);
});

test('four source-bound CloudEvents pass the real converter and AI-7 analysis', async t => {
  const exported = buildPortfolioCloudEvents(report());
  assert.deepEqual({ included: exported.included, excluded: exported.excluded, total: exported.total },
    { included: 4, excluded: 0, total: 4 });
  assert.equal(exported.jsonl.trim().split('\n').length, 4);
  assert.doesNotMatch(exported.jsonl, /UNTRUSTED_TITLE_NEVER_EXPORTED/);
  const decoded = exported.jsonl.trim().split('\n').map(JSON.parse);
  assert.deepEqual(decoded.map(x => x.data.conclusion), outcomes);
  assert.deepEqual(decoded.map(x => x.source), PUBLIC_TARGETS.map(x => 'https://github.com/' + x.repo));
  assert.ok(decoded.every(x => x.id.includes('-attempt-2') && x.time === '2026-11-16T17:00:00.000Z'));
  const analysis = analyzePortfolioCiJsonl(exported.jsonl);
  assert.equal(analysis.summary.ci_event_count, 4);
  assert.equal(analysis.summary.failed_ci_count, 2);
  assert.equal(analysis.summary.recommendation_count, 0);
  assert.equal(analysis.summary.missing_project_count, 0);
  assert.equal(analysis.read_only, true);
  assert.equal(analysis.production_ready, false);
  assert.equal(analysis.external_provenance_verified, false);
  assert.deepEqual(analysis.pipeline.map(x => x.id),
    ['AI-1','AI-2','AI-3','AI-4','AI-5','AI-6','AI-7']);
  assert.equal(analysis.pipeline[2].status, 'no_logs');
  assert.equal(analysis.pipeline[3].status, 'no_matches');
  assert.doesNotMatch(JSON.stringify(analysis), /UNTRUSTED_TITLE_NEVER_EXPORTED|PRIVATE/);

  // The generated file is accepted by the existing persisted AI-1 engine
  // without duplicate events, proving the standalone local handoff path.
  const folder = await mkdtemp(path.join(os.tmpdir(), 'devobs-public-portfolio-'));
  t.after(() => rm(folder, { recursive: true, force: true }));
  const store = path.join(folder, 'events.jsonl');
  const ai1 = convertText(exported.jsonl);
  assert.equal((await ingestText(ai1, store)).accepted, 4);
  assert.equal((await ingestText(ai1, store)).duplicateIgnored, 4);
  const events = await readEventStore(store);
  const snapshot = buildDashboardSnapshot(events);
  assert.equal(snapshot.summary.kind_counts.ci_result, 4);
  assert.equal(snapshot.summary.recommendation_count, 0);
});

test('missing attempt/time, pending, stale and provider errors never produce fabricated events', () => {
  const source = report();
  source.results[0].run_attempt = null;
  source.results[1].run_attempt = null;
  source.results[2].status = 'stale';
  source.results[3] = { repository: PUBLIC_TARGETS[3].repo, branch: 'main',
    status: 'unverified', error: 'rate_limited' };
  const x = buildPortfolioCloudEvents(source);
  assert.equal(x.jsonl, null);
  assert.equal(x.included, 0);
  assert.equal(x.excluded, 4);
  assert.throws(() => analyzePortfolioCiJsonl(''), /empty_input/);
});

test('ineligible results are excluded, but valid partial CI reports remain explicitly partial', () => {
  const source = report();
  source.results[1].status = 'stale';
  source.results[2].created_at = null;
  source.results[3].run_attempt = null;
  const exportResult = buildPortfolioCloudEvents(source);
  assert.equal(exportResult.included, 1);
  assert.equal(exportResult.excluded, 3);
  const data = analyzePortfolioCiJsonl(exportResult.jsonl);
  assert.equal(data.summary.ci_event_count, 1);
  assert.equal(data.summary.missing_project_count, 3);
  assert.equal(data.projects[0].project, 'Devobs');
});

test('tampered source, unsupported conclusions and invalid timestamps fail closed', () => {
  const variants = [
    p => { p.results[0].repository = 'other/fake'; },
    p => { p.private_repositories_queried = true; },
    p => { p.results[0].main_sha = 'b'.repeat(40); },
    p => { p.results[0].run_attempt = 0; },
    p => { p.results[0].created_at = '2026-02-30T00:00:00.000Z'; },
    p => { p.results[0].status = 'startup_failure'; p.results[0].run_sha = SHA; },
    p => { p.results[0].status = 'future-state'; },
  ];
  for (const change of variants) {
    const p = report();
    change(p);
    if (p.results[0].status === 'startup_failure') {
      assert.equal(buildPortfolioCloudEvents(p).included, 3);
    } else assert.throws(() => buildPortfolioCloudEvents(p));
  }
});

test('local AI-7 never accepts arbitrary GitHub source, unknown project or forged workflow', () => {
  const lines = buildPortfolioCloudEvents(report()).jsonl.trim().split('\n');
  for (const mutate of [
    event => { event.source = 'https://github.com/other/private-repo'; },
    event => { event.data.workflow = 'Release'; },
    event => { event.data.job = 'untrusted-job'; },
    event => { event.data.conclusion = 'unknown'; },
  ]) {
    const events = lines.map(JSON.parse);
    mutate(events[0]);
    assert.throws(() => analyzePortfolioCiJsonl(events.map(JSON.stringify).join('\n') + '\n'));
  }
});
