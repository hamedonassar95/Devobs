import assert from 'node:assert/strict';
import test from 'node:test';
import {
  AI9_EWMA_NOISE_CANDIDATE_POLICY,
  filterTrailingMedian,
  scoreEwmaNoiseCandidate,
} from '../scripts/ai_intelligence/ai9_ewma_noise_candidate.mjs';

test('trailing median filters a one-window spike without mutating the input', () => {
  const values = [...Array(30).fill(1), 50];
  const before = [...values];

  const filtered = filterTrailingMedian(values);

  assert.deepEqual(values, before);
  assert.equal(filtered.length, values.length);
  assert.equal(filtered.at(-1), 1);
});

test('noise candidate suppresses an isolated spike and detects a sustained step', () => {
  const baseline = Array(30).fill(1);
  const isolatedSpike = scoreEwmaNoiseCandidate([...baseline, 50]);
  const sustainedStep = scoreEwmaNoiseCandidate([...baseline, 50, 50]);

  assert.equal(isolatedSpike.flagged, false);
  assert.equal(sustainedStep.flagged, true);
  assert.equal(sustainedStep.filtered_latest, 50);
  assert.equal(sustainedStep.policy_version, AI9_EWMA_NOISE_CANDIDATE_POLICY.version);
});

test('candidate output records synthetic assumptions and does not report AI-9 gates', () => {
  const result = scoreEwmaNoiseCandidate([...Array(30).fill(1), 1]);

  assert.equal(result.classification, 'synthetic_development_only');
  assert.deepEqual(result.synthetic_assumptions, {
    before_seconds: 0,
    after_seconds: 120,
    quiet_windows_to_close: 2,
  });
  for (const gate of ['precision', 'recall', 'fpr', 'rca_top_3']) {
    assert.equal(Object.hasOwn(result, gate), false);
  }
});

test('candidate rejects non-finite series and unsupported alpha values', () => {
  assert.throws(() => scoreEwmaNoiseCandidate([...Array(30).fill(1), Number.NaN]), {
    code: 'invalid_series',
  });
  assert.throws(() => scoreEwmaNoiseCandidate([...Array(30).fill(1), 2], { alpha: 0.4 }), {
    code: 'unsupported_alpha',
  });
});
