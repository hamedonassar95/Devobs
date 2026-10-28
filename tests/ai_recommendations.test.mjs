import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { ingestText, normalizeEvent } from '../scripts/ai_intelligence/event_ingest.mjs';
import { analyzeIncidentEvents } from '../scripts/ai_intelligence/incident_analysis.mjs';
import { RecommendationError, recommendFromIncidentAnalysis } from '../scripts/ai_intelligence/recommendations.mjs';

const REPORT_PATH = fileURLToPath(new URL('../scripts/ai_intelligence/recommendation_report.mjs', import.meta.url));

function hypothesis(id, markers, heuristicConfidence = 'low') {
  return { id, classification: 'POSSIBLE', heuristic_confidence: heuristicConfidence, evidence_markers: markers };
}

function analysis(hypotheses) {
  return {
    clusters: [{ fingerprint: `sha256:${'a'.repeat(24)}`, count: 2, hypotheses }],
  };
}

function log(message, minute) {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: new Date(Date.UTC(2026, 9, 28, 8, minute)).toISOString(),
    source: 'application',
    kind: 'log',
    severity: 'error',
    data: { stream: 'stderr', message },
  });
}

function inputLine(event) {
  return JSON.stringify({
    schema_version: event.schema_version,
    occurred_at: event.occurred_at,
    source: event.source,
    kind: event.kind,
    severity: event.severity,
    data: event.data,
  });
}

test('maps an AI-3 POSSIBLE timeout signal to fixed read-only checks and a suggestion only', () => {
  const result = recommendFromIncidentAnalysis(analysis([hypothesis('timeout', ['ETIMEDOUT', 'timed_out'], 'medium')]));
  assert.equal(result.mode, 'suggestion_only');
  assert.equal(result.recommendations.length, 1);
  assert.equal(result.recommendations[0].classification, 'POSSIBLE');
  assert.equal(result.recommendations[0].heuristic_signal, 'medium');
  assert.equal(result.recommendations[0].automatic_execution, false);
  assert.equal(result.recommendations[0].requires_human_approval, true);
  assert.match(result.recommendations[0].feedback_key, /^sha256:[0-9a-f]{64}$/);
  assert.match(result.recommendations[0].read_only_checks[0], /راجع/);
});

test('maps each supported cause to an existing bounded local runbook entry', () => {
  const cases = [
    ['timeout', ['timeout']],
    ['connection', ['ECONNRESET']],
    ['dns', ['ENOTFOUND']],
    ['permission', ['EACCES']],
    ['dependency', ['module_not_found']],
    ['memory', ['heap_limit']],
  ];
  const clusters = cases.map(([id, markers], index) => ({
    fingerprint: `sha256:${String(index + 1).padStart(2, '0')}${'b'.repeat(22)}`,
    count: 1,
    hypotheses: [hypothesis(id, markers)],
  }));
  const result = recommendFromIncidentAnalysis({ clusters });
  assert.deepEqual(result.recommendations.map(item => item.cause_id), cases.map(([id]) => id));
  assert.ok(result.recommendations.every(item => item.automatic_execution === false));
});

test('unknown cause ids are counted but never echoed or mapped to a guessed fix', () => {
  const result = recommendFromIncidentAnalysis(analysis([hypothesis('unlisted_cause', ['FUTURE_MARKER'])]));
  assert.equal(result.status, 'NO_KNOWN_SUGGESTIONS');
  assert.equal(result.unmapped_hypothesis_count, 1);
  assert.deepEqual(result.recommendations, []);
  assert.equal(JSON.stringify(result).includes('unlisted_cause'), false);
});

test('does not echo untrusted source fields and rejects non-POSSIBLE or mismatched evidence', () => {
  const tainted = hypothesis('timeout', ['ETIMEDOUT']);
  tainted.description = 'SYNTHETIC_SECRET_MARKER';
  assert.equal(JSON.stringify(recommendFromIncidentAnalysis(analysis([tainted]))).includes('SYNTHETIC_SECRET_MARKER'), false);
  assert.throws(() => recommendFromIncidentAnalysis(analysis([{ ...hypothesis('timeout', ['ETIMEDOUT']), classification: 'CONFIRMED' }])), { code: 'invalid_hypothesis' });
  assert.throws(() => recommendFromIncidentAnalysis(analysis([hypothesis('timeout', ['UNRELATED'])])), { code: 'invalid_hypothesis_evidence' });
});

test('rejects malformed and over-limit analysis with fixed error codes', () => {
  assert.throws(() => recommendFromIncidentAnalysis(null), error => error instanceof RecommendationError && error.code === 'invalid_analysis');
  assert.throws(() => recommendFromIncidentAnalysis({ clusters: new Array(251) }), { code: 'too_many_clusters' });
  assert.throws(() => recommendFromIncidentAnalysis(analysis(new Array(9))), { code: 'invalid_cluster' });
});

test('offline CLI reads synthetic JSONL, returns bounded guidance, and leaves the store unchanged', async t => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-recommendations-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const storePath = path.join(directory, 'events.jsonl');
  const rawMarker = 'SYNTHETIC_RAW_MESSAGE_MUST_NOT_APPEAR';
  const event = log(`${rawMarker} ETIMEDOUT operation timed out`, 1);
  await ingestText(`${inputLine(event)}\n`, storePath);
  const before = await readFile(storePath, 'utf8');
  const result = spawnSync(process.execPath, [REPORT_PATH, '--store', storePath], {
    env: { PATH: process.env.PATH ?? '' },
    encoding: 'utf8',
    timeout: 10_000,
  });
  const after = await readFile(storePath, 'utf8');
  assert.equal(result.status, 0);
  assert.equal(result.stderr, '');
  assert.equal(after, before);
  assert.equal(result.stdout.includes(storePath), false);
  assert.equal(result.stdout.includes(rawMarker), false);
  const output = JSON.parse(result.stdout);
  assert.equal(output.mode, 'suggestion_only');
  assert.equal(output.automatic_execution, false);
  assert.equal(output.recommendations[0].cause_id, 'timeout');
});
