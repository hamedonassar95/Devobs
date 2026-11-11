import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { replayUsedSeedV2, AI9_JOINT_METRIC_EVALUATION_POLICY } from '../scripts/ai_intelligence/ai9_joint_metric_evaluation_v2.mjs';

test('v2 replay matches historical baseline and exposes only development quality', () => {
  const frozen = JSON.parse(readFileSync(
    new URL('../docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json', import.meta.url), 'utf8',
  ));
  const result = replayUsedSeedV2();
  const prior = frozen.per_seed[0];
  assert.equal(result.result.seed, 20270201);
  assert.equal(result.result.input_canonical_sha256, prior.input_canonical_sha256);
  assert.deepEqual(result.result.post_confirmation_baseline, prior.post_confirmation_layer.window_metrics);
  assert.equal(result.result.robust_shift_v1.tp, 59);
  assert.equal(result.result.robust_shift_v1.fp, 66);
  assert.equal(result.result.robust_shift_v1.fn, 31);
  assert.equal(result.result.joint_metric_v2.tp + result.result.joint_metric_v2.fn, 90);
  assert.equal(result.result.joint_metric_v2.fp + result.result.joint_metric_v2.tn, 45150);
  assert.ok(result.result.joint_metric_v2.tp <= result.result.post_confirmation_baseline.tp);
  assert.ok(result.result.joint_metric_v2.fp <= result.result.post_confirmation_baseline.fp);
  assert.equal(result.result.joint_fault_metric_delay.matched + result.result.joint_fault_metric_delay.missing, 18);
  assert.equal(result.production_decision, 'NOT_AUTHORIZED');
  assert.deepEqual(AI9_JOINT_METRIC_EVALUATION_POLICY.new_seeds, [20270501, 20270502, 20270503, 20270504]);
  // IMPORTANT: No call to evaluateFrozenFreshV2() here. The new seeds remain untouched.
  console.log('AI9_JOINT_V2_REUSED_SEED=' + JSON.stringify({
    seed: 20270201,
    baseline: result.result.post_confirmation_baseline,
    previously_rejected_v1: result.result.robust_shift_v1,
    exploratory_v2: result.result.joint_metric_v2,
    production_decision: result.production_decision,
  }));
});
