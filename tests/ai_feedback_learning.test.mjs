import assert from 'node:assert/strict';
import { chmod, lstat, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import {
  applyFeedbackLearning,
  createRecommendationFeedbackKey,
  FeedbackLearningError,
  readFeedbackLedger,
  recordRecommendationFeedback,
} from '../scripts/ai_intelligence/feedback_learning.mjs';
import { ingestText, normalizeEvent, readEventStore } from '../scripts/ai_intelligence/event_ingest.mjs';
import { analyzeIncidentEvents } from '../scripts/ai_intelligence/incident_analysis.mjs';
import { recommendFromIncidentAnalysis } from '../scripts/ai_intelligence/recommendations.mjs';

const REPORT_PATH = fileURLToPath(new URL('../scripts/ai_intelligence/recommendation_report.mjs', import.meta.url));
const KEY = `sha256:${'a'.repeat(64)}`;

async function temporaryDirectory(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-feedback-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  return directory;
}

function record(key, causeId, decision, day = '2026-10-28') {
  return {
    schema_version: 1,
    recommendation_key: key,
    cause_id: causeId,
    decision,
    recorded_at: `${day}T00:00:00.000Z`,
  };
}

function recommendation(key, causeId, reviewOrder) {
  return {
    feedback_key: key,
    cause_id: causeId,
    review_order: reviewOrder,
    heuristic_signal: 'low',
    requires_human_approval: true,
    automatic_execution: false,
  };
}

function syntheticEvent() {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: '2026-10-28T08:00:00Z',
    source: 'application',
    kind: 'log',
    severity: 'error',
    data: { stream: 'stderr', message: 'SYNTHETIC ETIMEDOUT request timed out' },
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
  }) + '\n';
}

test('feedback keys are stable digests and reject invalid targets', () => {
  const fingerprint = `sha256:${'b'.repeat(24)}`;
  assert.match(createRecommendationFeedbackKey(fingerprint, 'timeout'), /^sha256:[0-9a-f]{64}$/);
  assert.equal(createRecommendationFeedbackKey(fingerprint, 'timeout'), createRecommendationFeedbackKey(fingerprint, 'timeout'));
  assert.throws(() => createRecommendationFeedbackKey('raw private text', 'timeout'), { code: 'invalid_feedback_target' });
  assert.throws(() => createRecommendationFeedbackKey(fingerprint, 'unknown'), { code: 'invalid_feedback_target' });
});

test('explicit decisions are written to a private ledger without free-form fields', async t => {
  const directory = await temporaryDirectory(t);
  const ledgerPath = path.join(directory, 'feedback.jsonl');
  assert.deepEqual(await recordRecommendationFeedback({
    ledgerPath, recommendationKey: KEY, causeId: 'timeout', decision: 'accepted', recordedAt: '2026-10-28T00:00:00.000Z',
  }), { recorded: true, decision: 'accepted' });
  const info = await lstat(ledgerPath);
  assert.equal(info.mode & 0o777, 0o600);
  const records = await readFeedbackLedger(ledgerPath);
  assert.deepEqual(records, [record(KEY, 'timeout', 'accepted')]);
  assert.equal(Object.hasOwn(records[0], 'note'), false);
  assert.equal(Object.hasOwn(records[0], 'operator'), false);
});

test('latest choice replaces earlier votes for the same recommendation during aggregation', async t => {
  const directory = await temporaryDirectory(t);
  const ledgerPath = path.join(directory, 'feedback.jsonl');
  await recordRecommendationFeedback({ ledgerPath, recommendationKey: KEY, causeId: 'timeout', decision: 'accepted', recordedAt: '2026-10-27T00:00:00.000Z' });
  await recordRecommendationFeedback({ ledgerPath, recommendationKey: KEY, causeId: 'timeout', decision: 'rejected', recordedAt: '2026-10-28T00:00:00.000Z' });
  const result = applyFeedbackLearning({ recommendations: [recommendation(KEY, 'timeout', 1)] }, await readFeedbackLedger(ledgerPath));
  assert.equal(result.recommendations[0].feedback_review_signal.sample_count, 1);
  assert.equal(result.recommendations[0].feedback_review_signal.accepted_count, 0);
  assert.equal(result.recommendations[0].feedback_review_signal.rejected_count, 1);
});

test('feedback stays advisory and does not reorder recommendations below the evidence threshold', () => {
  const report = { mode: 'suggestion_only', recommendations: [recommendation(KEY, 'timeout', 1), recommendation(`sha256:${'c'.repeat(64)}`, 'dns', 2)] };
  const result = applyFeedbackLearning(report, [
    record(KEY, 'timeout', 'accepted'),
    record(`sha256:${'d'.repeat(64)}`, 'timeout', 'rejected'),
  ]);
  assert.deepEqual(result.recommendations.map(item => item.review_order), [1, 2]);
  assert.equal(result.feedback_learning.ranking_adjusted, false);
  assert.equal(result.recommendations[0].feedback_review_signal.sample_count, 2);
  assert.equal(result.recommendations[0].feedback_review_signal.smoothed_acceptance_rate, 0.5);
  assert.equal(result.recommendations[0].heuristic_signal, 'low');
  assert.equal(result.mode, 'suggestion_only');
});

test('three distinct reviewed recommendations enable deterministic smoothed ordering only', () => {
  const keys = ['d', 'e', 'f'].map(letter => `sha256:${letter.repeat(64)}`);
  const report = {
    mode: 'suggestion_only',
    recommendations: [recommendation(`sha256:${'a'.repeat(64)}`, 'timeout', 1), recommendation(`sha256:${'b'.repeat(64)}`, 'dns', 2)],
  };
  const feedback = [
    ...keys.map((key, index) => record(key, 'timeout', index === 0 ? 'rejected' : 'accepted')),
    ...['1', '2', '3'].map((digit, index) => record(`sha256:${digit.repeat(64)}`, 'dns', index === 0 ? 'accepted' : 'rejected')),
  ];
  const result = applyFeedbackLearning(report, feedback);
  assert.deepEqual(result.recommendations.map(item => item.cause_id), ['timeout', 'dns']);
  assert.equal(result.recommendations[0].feedback_review_signal.smoothed_acceptance_rate, 0.6);
  assert.equal(result.recommendations[1].feedback_review_signal.smoothed_acceptance_rate, 0.4);
  assert.equal(result.feedback_learning.ranking_adjusted, true);
  assert.equal(result.feedback_learning.automatic_execution, false);
  assert.equal(result.recommendations.every(item => item.requires_human_approval === true && item.automatic_execution === false), true);
});

test('invalid, over-permissive, linked, or locked ledgers fail closed without echoing paths', async t => {
  const directory = await temporaryDirectory(t);
  const publicLedger = path.join(directory, 'public.jsonl');
  await writeFile(publicLedger, `${JSON.stringify(record(KEY, 'timeout', 'accepted'))}\n`, { mode: 0o644 });
  await chmod(publicLedger, 0o644);
  await assert.rejects(readFeedbackLedger(publicLedger), error => error.code === 'unsafe_ledger_permissions' && !error.message.includes(publicLedger));

  const malformed = path.join(directory, 'malformed.jsonl');
  await writeFile(malformed, '{broken}\n', { mode: 0o600 });
  await assert.rejects(readFeedbackLedger(malformed), { code: 'invalid_ledger' });

  const target = path.join(directory, 'target.jsonl');
  await writeFile(target, '', { mode: 0o600 });
  const linked = path.join(directory, 'linked.jsonl');
  await symlink(target, linked);
  await assert.rejects(readFeedbackLedger(linked), { code: 'unsafe_ledger' });

  const locked = path.join(directory, 'locked.jsonl');
  await writeFile(`${locked}.lock`, '', { mode: 0o600 });
  await assert.rejects(recordRecommendationFeedback({ ledgerPath: locked, recommendationKey: KEY, causeId: 'timeout', decision: 'accepted' }), { code: 'ledger_locked' });
});

test('rejects invalid decisions, identifiers, timestamps, and schema fields', async t => {
  const directory = await temporaryDirectory(t);
  const ledgerPath = path.join(directory, 'feedback.jsonl');
  const invalidCases = [
    { recommendationKey: 'synthetic raw marker', causeId: 'timeout', decision: 'accepted' },
    { recommendationKey: KEY, causeId: 'timeout', decision: 'maybe' },
    { recommendationKey: KEY, causeId: 'timeout', decision: 'accepted', recordedAt: 'not-a-date' },
  ];
  for (const input of invalidCases) {
    await assert.rejects(recordRecommendationFeedback({ ledgerPath, ...input }), error => {
      assert.ok(error instanceof FeedbackLearningError);
      assert.equal(error.message.includes('synthetic raw marker'), false);
      return true;
    });
  }
  await assert.rejects(lstat(ledgerPath), { code: 'ENOENT' });
});

test('CLI records only an explicit choice and report remains local, bounded, and sanitized', async t => {
  const directory = await temporaryDirectory(t);
  const storePath = path.join(directory, 'events.jsonl');
  const ledgerPath = path.join(directory, 'feedback.jsonl');
  const rawMarker = 'SYNTHETIC_RAW_EVENT_MUST_NOT_APPEAR';
  const event = syntheticEvent();
  const eventLine = inputLine({ ...event, data: { ...event.data, message: `${rawMarker} ETIMEDOUT request timed out` } });
  await ingestText(eventLine, storePath);
  const events = await readEventStore(storePath);
  const recommendations = recommendFromIncidentAnalysis(analyzeIncidentEvents(events)).recommendations;
  assert.equal(recommendations.length, 1);

  const before = await readFile(storePath, 'utf8');
  const result = spawnSync(process.execPath, [
    REPORT_PATH, '--store', storePath, '--feedback-ledger', ledgerPath,
    '--record-feedback', recommendations[0].feedback_key, '--decision', 'accepted',
  ], { env: { PATH: process.env.PATH ?? '' }, encoding: 'utf8', timeout: 10_000 });
  assert.equal(result.status, 0);
  assert.equal(result.stderr, '');
  const output = JSON.parse(result.stdout);
  assert.equal(output.recommendations[0].feedback_review_signal.accepted_count, 1);
  assert.equal(output.mode, 'suggestion_only');
  assert.equal(result.stdout.includes(rawMarker), false);
  assert.equal(result.stdout.includes(storePath), false);
  assert.equal(await readFile(storePath, 'utf8'), before);
  assert.equal((await lstat(ledgerPath)).mode & 0o777, 0o600);

  const ledgerBeforeRead = await readFile(ledgerPath, 'utf8');
  const readOnly = spawnSync(process.execPath, [REPORT_PATH, '--store', storePath, '--feedback-ledger', ledgerPath], {
    env: { PATH: process.env.PATH ?? '' }, encoding: 'utf8', timeout: 10_000,
  });
  assert.equal(readOnly.status, 0);
  assert.equal(readOnly.stdout.includes('feedback_review_signal'), true);
  assert.equal(await readFile(ledgerPath, 'utf8'), ledgerBeforeRead);
});
