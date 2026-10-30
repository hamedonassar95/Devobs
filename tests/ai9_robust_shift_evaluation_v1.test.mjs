import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  AI9_ROBUST_SHIFT_EVAL_POLICY,
  replayPreviouslyConsumedSeed,
} from '../scripts/ai_intelligence/ai9_robust_shift_evaluation_v1.mjs';

test('previously used seed reproduces frozen baseline and never authorizes rollout', () => {
  const frozen = JSON.parse(readFileSync(
    new URL('../docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json', import.meta.url), 'utf8'));
  const replay = replayPreviouslyConsumedSeed();
  const first = frozen.per_seed[0];
  assert.equal(replay.result.seed, 20270201);
  assert.equal(replay.result.canonical_input_sha256, first.input_canonical_sha256);
  assert.deepEqual(replay.result.baseline, first.post_confirmation_layer.window_metrics);
  assert.equal(replay.classification, 'synthetic_development_only');
  assert.equal(replay.production_decision, 'NOT_AUTHORIZED');
  assert.equal(replay.p01_decision, 'NO-GO / BLOCKED');
  assert.ok(replay.result.candidate.tp <= replay.result.baseline.tp);
  assert.ok(replay.result.candidate.fp <= replay.result.baseline.fp);
  assert.ok(replay.result.candidate.fn >= replay.result.baseline.fn);
  assert.equal(replay.result.candidate.tp + replay.result.candidate.fn, 90);
  assert.equal(replay.result.candidate.fp + replay.result.candidate.tn, 45150);
  assert.equal(replay.result.candidate_fault_metric_delay.metric_streams_matched
    + replay.result.candidate_fault_metric_delay.metric_streams_missing, 18);
  assert.deepEqual(AI9_ROBUST_SHIFT_EVAL_POLICY.preregistered_seeds,
    [20270401, 20270402, 20270403, 20270404]);
  // The new holdout is deliberately not evaluated inside CI.
  console.log('AI9_REUSED_SEED_BASELINE_MATCH=' + JSON.stringify({
    seed: replay.result.seed,
    baseline: replay.result.baseline,
    candidate_posthoc: replay.result.candidate,
    interpretation: replay.interpretation,
  }));
});
