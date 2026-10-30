import assert from 'node:assert/strict';
import test from 'node:test';
import {
  AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY,
  confirmTwoOfThreeScoredFlags,
} from '../scripts/ai_intelligence/ai9_zma_grouping_candidate_v1.mjs';

test('Z-score and moving-average confirmation requires two of the last three scored flags', () => {
  assert.equal(confirmTwoOfThreeScoredFlags([false]), false);
  assert.equal(confirmTwoOfThreeScoredFlags([true]), false);
  assert.equal(confirmTwoOfThreeScoredFlags([true, false]), false);
  assert.equal(confirmTwoOfThreeScoredFlags([true, true]), true);
  assert.equal(confirmTwoOfThreeScoredFlags([true, false, true]), true);
  assert.equal(confirmTwoOfThreeScoredFlags([false, true, false]), false);
});

test('candidate keeps grouping descriptive and aligned to the registered interval', () => {
  assert.equal(AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY.alert_merge_gap_seconds, 120);
  assert.equal(AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY.quiet_windows_to_close, 2);
  assert.equal(AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY.ewma_policy, 'ai9-ewma-noise-candidate-v1');
  assert.equal(AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY.error_rate_spike, 'unchanged_production_channel');
});

test('confirmation rejects empty, oversized, or malformed histories', () => {
  assert.throws(() => confirmTwoOfThreeScoredFlags([]), { code: 'invalid_confirmation_flags' });
  assert.throws(() => confirmTwoOfThreeScoredFlags([true, false, true, false]), {
    code: 'invalid_confirmation_flags',
  });
  assert.throws(() => confirmTwoOfThreeScoredFlags([true, 1]), {
    code: 'invalid_confirmation_flags',
  });
});
