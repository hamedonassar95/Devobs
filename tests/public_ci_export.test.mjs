import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import * as api from '../assets/public-ci/api.mjs';
import { convertText } from '../scripts/integrations/cloudevents_ci_adapter.mjs';
import { ingestText, readEventStore } from '../scripts/ai_intelligence/event_ingest.mjs';
import { buildDashboardSnapshot } from '../scripts/ai_intelligence/dashboard_server.mjs';

const SHA = 'a'.repeat(40);
function payload() {
  return { total_count: 1, workflow_runs: [{ id: 123, run_number: 4, run_attempt: 1,
    workflow_id: 374991651, path: '.github/workflows/ci.yml', event: 'push',
    head_branch: 'main', head_sha: SHA, status: 'completed', conclusion: 'success',
    created_at: '2026-11-16T01:00:00Z', updated_at: '2026-11-16T01:02:03Z',
    name: 'PRIVATE_SENTINEL', html_url: 'https://untrusted.example.invalid/',
    repository: { full_name: 'hamedonassar95/Devobs', private: false },
    head_repository: { full_name: 'hamedonassar95/Devobs', private: false } }] };
}
const normalize = runs => api.normalizePublicCiEvidence({ name: 'main', commit: { sha: SHA } }, runs);
function exportEvent(evidence) {
  assert.equal(typeof api.buildPublicCiCloudEvent, 'function', 'CI CloudEvents export must be implemented');
  return api.buildPublicCiCloudEvent(evidence);
}

test('a completed matching run exports only fixed public CloudEvents fields', () => {
  const text = exportEvent(normalize(payload()));
  assert.equal(text.split('\n').length, 2);
  assert.deepEqual(JSON.parse(text), { specversion: '1.0', id: 'github-ci-123-attempt-1',
    source: 'https://github.com/hamedonassar95/Devobs', type: 'devobs.ci.result.v1',
    time: '2026-11-16T01:00:00.000Z', datacontenttype: 'application/json',
    data: { workflow: 'CI', job: 'workflow-summary-run-123-attempt-1',
      conclusion: 'success', commit_sha: SHA } });
  assert.doesNotMatch(text, /PRIVATE_SENTINEL|untrusted|updated_at|mainSha|runUrl/);
  assert.equal(JSON.parse(convertText(text)).data.workflow, 'Devobs - CI');
});

test('matching supported terminal outcomes retain their exact conclusion', () => {
  for (const conclusion of ['success', 'failure', 'cancelled', 'timed_out', 'neutral', 'skipped', 'action_required']) {
    const p = payload(); p.workflow_runs[0].conclusion = conclusion;
    assert.equal(JSON.parse(exportEvent(normalize(p))).data.conclusion, conclusion);
  }
});

test('missing, nonterminal, unmatched and unsupported results cannot export', () => {
  for (const fields of [{ status: 'queued', conclusion: null },
    { status: 'in_progress', conclusion: null }, { head_sha: 'b'.repeat(40) },
    { conclusion: 'stale' }, { conclusion: 'startup_failure' }]) {
    const p = payload(); Object.assign(p.workflow_runs[0], fields);
    assert.equal(exportEvent(normalize(p)), null);
  }
  assert.equal(exportEvent(normalize({ total_count: 0, workflow_runs: [] })), null);
  assert.equal(exportEvent(null), null);
  const noAttempt = payload(); delete noAttempt.workflow_runs[0].run_attempt;
  assert.equal(normalize(noAttempt).state, 'success');
  assert.equal(normalize(noAttempt).runAttempt, null);
  assert.equal(exportEvent(normalize(noAttempt)), null);
});

test('attempt and creation-time metadata fail closed before display or export', () => {
  for (const fields of [{ run_attempt: 0 }, { run_attempt: 1.5 }, { run_attempt: '1' },
    { run_attempt: Number.MAX_SAFE_INTEGER + 1 }, { run_attempt: undefined }, { run_attempt: null },
    { created_at: '2026-02-30T00:00:00Z' }, { created_at: '2026-11-17T00:00:00Z' }]) {
    const p = payload(); Object.assign(p.workflow_runs[0], fields);
    assert.throws(() => normalize(p), { code: 'invalid_response' });
  }
  const evidence = normalize(payload());
  for (const fields of [{ runId: 0 }, { runAttempt: '1' }, { runSha: 'bad' },
    { createdAt: 'bad' }, { mainSha: 'b'.repeat(40) }]) {
    assert.throws(() => exportEvent({ ...evidence, ...fields }), { code: 'invalid_response' });
  }
  const p = payload();
  p.workflow_runs[0].created_at = '2026-11-16T01:02:03Z';
  p.workflow_runs[0].updated_at = '2026-11-16T01:02:03.001Z';
  assert.ok(exportEvent(normalize(p)), 'Timestamp ordering must compare instants, not strings');
});

test('same attempt replays identically even if update time changes', async t => {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'devobs-ci-export-'));
  t.after(() => rm(folder, { recursive: true, force: true }));
  const store = path.join(folder, 'events.jsonl');
  const p = payload(); const first = exportEvent(normalize(p));
  p.workflow_runs[0].updated_at = '2026-11-16T02:00:00Z';
  const replay = exportEvent(normalize(p));
  assert.equal(replay, first, 'observation/update time must not change event identity');
  assert.equal((await ingestText(convertText(first), store)).accepted, 1);
  assert.equal((await ingestText(convertText(replay), store)).duplicateIgnored, 1);
  p.workflow_runs[0].run_attempt = 2;
  const second = exportEvent(normalize(p));
  assert.equal((await ingestText(convertText(second), store)).accepted, 1);
  const repeated = await ingestText(convertText(first + second), store);
  assert.equal(repeated.accepted, 0); assert.equal(repeated.duplicateIgnored, 2);
  const events = await readEventStore(store);
  assert.equal(events.length, 2); assert.notEqual(events[0].event_id, events[1].event_id);
  const snapshot = buildDashboardSnapshot(events);
  assert.equal(snapshot.summary.kind_counts.ci_result, 2);
  assert.equal(snapshot.pipeline.mode, 'local_advisory_only');
  assert.equal(snapshot.recommendations.length, 0);
});
