import assert from 'node:assert/strict';
import test from 'node:test';
import { replayConsumedAi9OnsetV3 } from '../scripts/ai_intelligence/ai9_coherent_onset_v3_replay.mjs';

test('replay uses only consumed seed and exactly reconciles historic baseline and v2', () => {
  const r = replayConsumedAi9OnsetV3();
  assert.equal(r.seed, 20270201);
  assert.equal(r.input_canonical_sha256, '361a77e4ee44de9c10903f2045287dc86ed2b170c5da019f9880f8fe2f4962a0');
  assert.deepEqual([r.baseline.tp,r.baseline.fp,r.baseline.fn,r.baseline.tn], [76,1126,14,44024]);
  assert.deepEqual([r.frozen_joint_v2.tp,r.frozen_joint_v2.fp,r.frozen_joint_v2.fn,r.frozen_joint_v2.tn], [58,8,32,45142]);
  assert.equal(r.onset_v3.tp + r.onset_v3.fn, 90);
  assert.equal(r.onset_v3.fp + r.onset_v3.tn, 45150);
  assert.ok(r.onset_v3.tp >= r.frozen_joint_v2.tp, 'v3 cannot remove a v2 alert');
  assert.ok(r.onset_v3.fp >= r.frozen_joint_v2.fp, 'v3 restores onsets, so FP can rise');
  assert.equal(r.matched_fault_metrics + r.missing_fault_metrics, 18);
  assert.equal(r.production_decision, 'NOT_AUTHORIZED');
  console.log('AI9_ONSET_V3_REUSED_SEED=' + JSON.stringify({
    seed: r.seed,
    v2: r.frozen_joint_v2,
    v3: r.onset_v3,
    missed_fault_metrics: r.missing_fault_metrics,
    production_decision: r.production_decision,
  }));
});
