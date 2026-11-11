import assert from 'node:assert/strict';
import test from 'node:test';
import {
  AI9_POST_CONFIRMATION_V1_POLICY,
  AI9_POST_CONFIRMATION_V1_SEEDS,
} from '../scripts/ai_intelligence/evaluate_ai9_post_confirmation_v1.mjs';

test('confirmation evaluation freezes the registered policy and exactly 20 fresh seeds', () => {
  assert.equal(AI9_POST_CONFIRMATION_V1_POLICY.version, 'ai9-post-detector-confirmation-v1');
  assert.equal(AI9_POST_CONFIRMATION_V1_POLICY.candidate_input, 'ai9-ewma-noise-candidate-v1');
  assert.equal(AI9_POST_CONFIRMATION_V1_POLICY.before_seconds, 0);
  assert.equal(AI9_POST_CONFIRMATION_V1_POLICY.after_seconds, 120);
  assert.equal(AI9_POST_CONFIRMATION_V1_POLICY.quiet_windows_to_close, 2);
  assert.deepEqual(AI9_POST_CONFIRMATION_V1_POLICY.gates, {
    precision: 0.8,
    recall: 0.8,
    fpr: 0.05,
  });
  assert.equal(AI9_POST_CONFIRMATION_V1_SEEDS.length, 20);
  assert.equal(new Set(AI9_POST_CONFIRMATION_V1_SEEDS).size, 20);
  assert.deepEqual(AI9_POST_CONFIRMATION_V1_SEEDS, Array.from({ length: 20 }, (_, index) => 20270101 + index));
  assert.ok(AI9_POST_CONFIRMATION_V1_SEEDS.every(seed => seed >= 20270101 && seed <= 20270120));
});
