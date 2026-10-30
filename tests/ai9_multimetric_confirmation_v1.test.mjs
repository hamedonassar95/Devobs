import assert from 'node:assert/strict';
import test from 'node:test';
import {
  AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY,
  AI9_MULTIMETRIC_CONFIRMATION_V1_SEEDS,
} from '../scripts/ai_intelligence/evaluate_ai9_multimetric_confirmation_v1.mjs';

test('multimetric confirmation evaluation freezes the preregistered policy and fresh seeds', () => {
  assert.equal(AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.version, 'ai9-multimetric-confirmation-v1');
  assert.equal(AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.layer_policy_version, 'ai9-post-detector-confirmation-v1');
  assert.equal(AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.candidate_policy_version, 'ai9-ewma-noise-candidate-v1');
  assert.equal(AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.before_seconds, 0);
  assert.equal(AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.after_seconds, 120);
  assert.equal(AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.quiet_windows_to_close, 2);
  assert.deepEqual(AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.gates, {
    precision: 0.8,
    recall: 0.8,
    fpr: 0.05,
  });
  assert.equal(AI9_MULTIMETRIC_CONFIRMATION_V1_SEEDS.length, 20);
  assert.equal(new Set(AI9_MULTIMETRIC_CONFIRMATION_V1_SEEDS).size, 20);
  assert.deepEqual(AI9_MULTIMETRIC_CONFIRMATION_V1_SEEDS,
    Array.from({ length: 20 }, (_, index) => 20270201 + index));
});
