import assert from 'node:assert/strict';
import test from 'node:test';
import { AI9_ROBUST_SHIFT_POLICY, robustShiftDecision } from '../scripts/ai_intelligence/ai9_robust_shift_candidate.mjs';

const MINUTE = 60_000;
const FIRST = Date.parse('2026-10-30T00:00:00.000Z');
function stream(values) {
  return {
    values,
    events: values.map((value, index) => ({
      occurred_at: new Date(FIRST + index * MINUTE).toISOString(),
      data: { value },
    })),
  };
}

test('declared robust-shift policy and strict persistent median contrast', () => {
  assert.equal(AI9_ROBUST_SHIFT_POLICY.version, 'ai9-robust-shift-confirmation-v1');
  assert.equal(AI9_ROBUST_SHIFT_POLICY.reference_points, 30);
  assert.equal(AI9_ROBUST_SHIFT_POLICY.recent_points, 3);
  assert.equal(AI9_ROBUST_SHIFT_POLICY.mad_multiplier, 4);
  const high = stream([...Array(30).fill(10), 20, 20, 20]);
  const result = robustShiftDecision(high, 32, true);
  assert.equal(result.robust_shift, true);
  assert.equal(result.candidate_confirmed, true);
  assert.equal(result.status, 'scored');
  assert.equal(robustShiftDecision(high, 32, false).candidate_confirmed, false);
});

test('single outlier suppressed; persistent two of three robust excursion retained', () => {
  assert.equal(robustShiftDecision(stream([...Array(30).fill(10), 20, 10, 10]), 32, true).candidate_confirmed, false);
  assert.equal(robustShiftDecision(stream([...Array(30).fill(10), 10, 20, 20]), 32, true).candidate_confirmed, true);
  assert.equal(robustShiftDecision(stream(Array(33).fill(10)), 32, true).candidate_confirmed, false);
});

test('bounded noise and slow drift do not create a robust shift', () => {
  const noisy = stream([...Array.from({ length: 30 }, (_, i) => i % 2 ? 11 : 9), 11, 11, 11]);
  assert.equal(robustShiftDecision(noisy, 32, true).candidate_confirmed, false);
  const drift = stream(Array.from({ length: 33 }, (_, i) => 10 + i * 0.1));
  assert.equal(robustShiftDecision(drift, 32, true).candidate_confirmed, false);
});

test('insufficient lookback fails closed, recovery and replay are deterministic', () => {
  const all = stream([...Array(30).fill(10), 10, 20, 20, 10, 10, 10]);
  assert.equal(robustShiftDecision(all, 30, true).status, 'insufficient_history');
  assert.equal(robustShiftDecision(all, 30, true).candidate_confirmed, false);
  const onset = robustShiftDecision(all, 32, true);
  const restarted = robustShiftDecision(all, 32, true);
  assert.deepEqual(onset, restarted);
  assert.equal(robustShiftDecision(all, 35, true).candidate_confirmed, false);
});

test('bad numeric observations and missing/out-of-order cadence fail closed', () => {
  const bad = stream([...Array(30).fill(10), 10, 20, Number.NaN]);
  assert.throws(() => robustShiftDecision(bad, 32, true), { code: 'invalid_metric_window' });
  const duplicate = stream(Array(33).fill(10));
  duplicate.events[31].occurred_at = duplicate.events[30].occurred_at;
  assert.throws(() => robustShiftDecision(duplicate, 32, true), { code: 'invalid_temporal_order' });
  const missing = stream(Array(33).fill(10));
  missing.events[31].occurred_at = new Date(FIRST + 32 * MINUTE).toISOString();
  assert.throws(() => robustShiftDecision(missing, 32, true), { code: 'invalid_temporal_order' });
});

test('malformed context cannot be interpreted as positive', () => {
  assert.throws(() => robustShiftDecision({}, 32, true), { code: 'invalid_metric_window' });
  assert.throws(() => robustShiftDecision(stream(Array(33).fill(10)), 32, 'true'), { code: 'invalid_confirmation' });
  assert.throws(() => robustShiftDecision(stream(Array(33).fill(10)), 100, true), { code: 'invalid_metric_window' });
});
