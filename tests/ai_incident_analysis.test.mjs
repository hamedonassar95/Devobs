import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { ingestText, normalizeEvent } from '../scripts/ai_intelligence/event_ingest.mjs';
import { analyzeIncidentEvents, IncidentAnalysisError } from '../scripts/ai_intelligence/incident_analysis.mjs';

const REPORT_PATH = fileURLToPath(new URL('../scripts/ai_intelligence/incident_report.mjs', import.meta.url));
const SHA = 'a'.repeat(40);

function log(message, minute, severity = 'error') {
  return normalizeEvent({ schema_version: 1, occurred_at: new Date(Date.UTC(2026, 9, 28, 8, minute)).toISOString(), source: 'application', kind: 'log', severity, data: { stream: 'stderr', message } });
}

function ci(conclusion, minute, sha = SHA) {
  return normalizeEvent({ schema_version: 1, occurred_at: new Date(Date.UTC(2026, 9, 28, 8, minute)).toISOString(), source: 'github_actions', kind: 'ci_result', severity: conclusion === 'failure' ? 'error' : 'info', data: { workflow: 'synthetic-ci', job: 'synthetic-test', conclusion, commit_sha: sha } });
}

function reportFor(events) {
  return analyzeIncidentEvents(events);
}

test('normalizes numeric and UUID identifiers into one stable fingerprint without echoing logs', () => {
  const result = reportFor([
    log('Synthetic timeout for request 1234 id 123e4567-e89b-12d3-a456-426614174000', 1),
    log('Synthetic timeout for request 5678 id 123e4567-e89b-12d3-a456-426614174999', 2),
  ]);
  assert.equal(result.clusters.length, 1);
  assert.equal(result.clusters[0].count, 2);
  assert.equal(result.clusters[0].grouping_methods[0], 'normalized_fingerprint');
  assert.equal(JSON.stringify(result).includes('request 1234'), false);
  assert.match(result.clusters[0].fingerprint, /^sha256:[0-9a-f]{24}$/);
});

test('groups similar but non-identical logs with bounded TF-IDF cosine matching', () => {
  const result = reportFor([
    log('database connection timeout while waiting for service alpha', 1),
    log('database connection timeout while waiting for service beta', 2),
    log('permission denied while opening the local configuration', 3),
  ]);
  assert.equal(result.clusters.length, 2);
  const similar = result.clusters.find(cluster => cluster.count === 2);
  assert.ok(similar.grouping_methods.includes('tfidf_cosine'));
  assert.ok(similar.max_similarity >= 0.62);
});

test('ranks possible causes from fixed markers and keeps confidence heuristic', () => {
  const result = reportFor([log('ETIMEDOUT: operation timed out', 1)]).clusters[0];
  assert.equal(result.hypotheses[0].classification, 'POSSIBLE');
  assert.equal(result.hypotheses[0].id, 'timeout');
  assert.equal(result.hypotheses[0].heuristic_confidence, 'medium');
  assert.deepEqual(result.hypotheses[0].evidence_markers, ['ETIMEDOUT', 'timed_out']);
  assert.equal(result.hypotheses[0].next_check.includes('راجع'), true);
});

test('links an explicit synthetic commit reference as possible context, not proven cause', () => {
  const result = reportFor([ci('failure', 2), log(`Synthetic job reports ETIMEDOUT at ${SHA}`, 10)]);
  assert.equal(result.clusters[0].correlation.classification, 'POSSIBLE');
  assert.equal(result.clusters[0].correlation.basis, 'full_commit_sha_text_match');
  assert.equal(result.clusters[0].correlation.commit_sha, SHA);
  assert.equal(result.deployment_correlation, 'unsupported_by_event_schema');
});

test('uses weak nearest-prior-CI context only within six hours and returns UNKNOWN otherwise', () => {
  const nearby = reportFor([ci('failure', 0), log('Synthetic test output has no shared SHA', 10)]).clusters[0];
  assert.equal(nearby.correlation.classification, 'POSSIBLE');
  assert.equal(nearby.correlation.heuristic_confidence, 'low');
  const distant = reportFor([ci('failure', 0), log('Synthetic test output has no shared SHA', 500)]).clusters[0];
  assert.equal(distant.correlation.classification, 'UNKNOWN');
});

test('fails closed on malformed or over-limit input without disclosing content', () => {
  assert.throws(() => reportFor([{ private: 'synthetic-private-marker' }]), error => {
    assert.ok(error instanceof IncidentAnalysisError);
    assert.equal(error.code, 'invalid_event');
    assert.equal(error.message.includes('synthetic-private-marker'), false);
    return true;
  });
  assert.throws(() => reportFor(new Array(10_001)), { code: 'invalid_event_batch' });
  assert.throws(() => reportFor(Array.from({ length: 251 }, (_, index) => log(`Synthetic log ${index}`, index))), { code: 'too_many_log_events' });
  assert.throws(() => reportFor([log(`${'synthetic '.repeat(128)}synthetic`, 1)]), { code: 'message_too_complex' });
});

test('offline CLI reads a synthetic store and emits only aggregates and bounded hypotheses', async t => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-incident-analysis-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const storePath = path.join(directory, 'events.jsonl');
  const records = [log('Synthetic timeout marker request 101', 1), log('Synthetic timeout marker request 102', 2)];
  await ingestText(`${records.map(event => JSON.stringify({ schema_version: event.schema_version, occurred_at: event.occurred_at, source: event.source, kind: event.kind, severity: event.severity, data: event.data })).join('\n')}\n`, storePath);
  const result = spawnSync(process.execPath, [REPORT_PATH, '--store', storePath], { env: { PATH: process.env.PATH ?? '' }, encoding: 'utf8', timeout: 10_000 });
  assert.equal(result.status, 0);
  assert.equal(result.stderr, '');
  assert.equal(result.stdout.includes(storePath), false);
  assert.equal(result.stdout.includes('request 101'), false);
  const output = JSON.parse(result.stdout);
  assert.equal(output.log_events, 2);
  assert.equal(output.clusters.length, 1);
});
