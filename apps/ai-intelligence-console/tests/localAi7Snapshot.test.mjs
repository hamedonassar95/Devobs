import test from 'node:test';
import assert from 'node:assert/strict';
import { parseLocalAi7Snapshot } from '../src/utils/localAi7Snapshot.ts';

function snapshot(overrides = {}) {
  return {
    source: 'local_ai7_snapshot',
    status: 'local_snapshot',
    mode: 'local_advisory_only',
    read_only: true,
    summary: {
      event_count: 24,
      log_cluster_count: 2,
      recommendation_count: 1,
      anomaly_candidate_count: 2,
    },
    stages: Array.from({ length: 7 }, (_, index) => ({
      id: `AI-${index + 1}`,
      status: 'ready',
      count: 1,
    })),
    recommendations: [{
      review_order: 1,
      cause_id: 'timeout',
      classification: 'POSSIBLE',
      heuristic_signal: 'medium',
      event_count: 3,
      evidence_markers: ['ETIMEDOUT'],
      requires_human_approval: true,
      automatic_execution: false,
    }],
    ...overrides,
  };
}

test('accepts and copies a valid local, advisory-only snapshot', () => {
  const input = snapshot();
  const parsed = parseLocalAi7Snapshot(input);
  assert.ok(parsed);
  assert.equal(parsed.mode, 'local_advisory_only');
  assert.equal(parsed.recommendations[0].requires_human_approval, true);
  assert.equal(parsed.recommendations[0].automatic_execution, false);
  assert.notEqual(parsed.stages, input.stages);
  assert.notEqual(parsed.recommendations, input.recommendations);
});

test('rejects wrong source, status, mode, access mode and extra top-level fields', () => {
  for (const invalid of [
    snapshot({ source: 'remote_ai' }),
    snapshot({ status: 'live' }),
    snapshot({ mode: 'automatic_recovery' }),
    snapshot({ read_only: false }),
    snapshot({ apiKey: 'must-not-be-used' }),
  ]) {
    assert.equal(parseLocalAi7Snapshot(invalid), null);
  }
});

test('rejects malformed, unsafe or inconsistent summary counts', () => {
  for (const value of [-1, 1.5, Number.MAX_SAFE_INTEGER + 1, 10_000_001, '24', NaN]) {
    const invalid = snapshot();
    invalid.summary.event_count = value;
    assert.equal(parseLocalAi7Snapshot(invalid), null);
  }
  const mismatch = snapshot({ summary: { ...snapshot().summary, recommendation_count: 2 } });
  assert.equal(parseLocalAi7Snapshot(mismatch), null);
});

test('rejects invalid stages before a snapshot reaches the UI', () => {
  const wrongOrder = snapshot();
  wrongOrder.stages[0].id = 'AI-2';
  const malformedCount = snapshot();
  malformedCount.stages[2].count = -1;
  const unsafeStatus = snapshot();
  unsafeStatus.stages[3].status = 'provider response with unsafe content';
  const extraField = snapshot();
  extraField.stages[4].debug = 'unexpected upstream data';

  for (const invalid of [
    snapshot({ stages: [] }),
    wrongOrder,
    malformedCount,
    unsafeStatus,
    extraField,
  ]) {
    assert.equal(parseLocalAi7Snapshot(invalid), null);
  }
});

test('rejects unknown recommendation causes, evidence, confidence and approval flags', () => {
  const changes = [
    { cause_id: 'untrusted_free_text' },
    { evidence_markers: ['raw customer text'] },
    { heuristic_signal: 'high' },
    { classification: 'CONFIRMED' },
    { requires_human_approval: false },
    { automatic_execution: true },
    { event_count: 0 },
    { review_order: 7 },
    { runbook_text: 'extra untrusted content' },
  ];
  for (const change of changes) {
    const invalid = snapshot();
    invalid.recommendations = [{ ...invalid.recommendations[0], ...change }];
    assert.equal(parseLocalAi7Snapshot(invalid), null);
  }
});

test('requires visible recommendations to match the bounded total', () => {
  const tooFew = snapshot({
    summary: { ...snapshot().summary, recommendation_count: 2 },
  });
  assert.equal(parseLocalAi7Snapshot(tooFew), null);

  const many = snapshot({
    summary: { ...snapshot().summary, recommendation_count: 6 },
    recommendations: Array.from({ length: 5 }, (_, index) => ({
      ...snapshot().recommendations[0],
      review_order: index + 1,
    })),
  });
  assert.equal(parseLocalAi7Snapshot(many)?.recommendations.length, 5);
});
