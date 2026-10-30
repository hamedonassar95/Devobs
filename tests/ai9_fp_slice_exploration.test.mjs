import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  AI9_FP_SLICE_EXPLORATION_POLICY,
  exploreAi9FpSlices,
} from '../scripts/ai_intelligence/ai9_fp_slice_exploration.mjs';

const ROOT_REPORT = JSON.parse(readFileSync(
  new URL('../docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json', import.meta.url),
  'utf8',
));

test('post-hoc synthetic slice totals agree with exact frozen first seed', () => {
  const report = exploreAi9FpSlices(20270201);
  const reference = ROOT_REPORT.per_seed[0];
  const { tp, fp, fn, tn } = reference.post_confirmation_layer.window_metrics;
  assert.deepEqual(report.totals, { tp, fp, fn, tn });
  assert.equal(report.input_canonical_sha256, reference.input_canonical_sha256);
  assert.equal(report.reused_seed, 20270201);
  assert.equal(report.classification, 'synthetic_development_only');
  assert.equal(report.policy_version, AI9_FP_SLICE_EXPLORATION_POLICY.version);
  assert.equal(report.quality_gate_decision, 'UNCHANGED_AI9_FAIL');
  assert.equal(report.production_decision, 'NOT_AUTHORIZED');
  assert.equal(report.p01_decision, 'NO-GO / BLOCKED');
  const slices = Object.values(report.by_control_or_fault_group);
  assert.equal(slices.reduce((n, c) => n + c.fp, 0), fp);
  assert.equal(slices.reduce((n, c) => n + c.tp, 0), tp);
  assert.equal(Object.values(report.by_metric).reduce((n, c) => n + c.fn, 0), fn);
  assert.ok(slices.length >= 6);
  assert.ok(Object.hasOwn(report.by_control_or_fault_group, 'injected_fault'));
  assert.ok(!JSON.stringify(report).includes('"values"'));
  assert.ok(!JSON.stringify(report).includes('"events"'));
});

test('post-hoc diagnostic refuses any seed outside previously consumed set', () => {
  for (const seed of [20270200, 20270221, -1, 1.5, '20270201', null]) {
    assert.throws(() => exploreAi9FpSlices(seed), { code: 'unregistered_or_invalid_seed' });
  }
});
