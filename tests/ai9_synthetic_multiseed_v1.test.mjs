import assert from 'node:assert/strict';
import test from 'node:test';
import {
  AI9_SYNTHETIC_MULTI_SEED_V1_POLICY,
  summarizeSeedMetric,
} from '../scripts/ai_intelligence/ai9_synthetic_multiseed_v1.mjs';

test('multiseed runner freezes exactly the registered twenty unique seeds', () => {
  const seeds = AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds;
  assert.equal(seeds.length, 20);
  assert.equal(new Set(seeds).size, 20);
  assert.deepEqual(seeds, Array.from({ length: 20 }, (_, index) => 20261201 + index));
});

test('seed summary reports arithmetic mean and population variance in percentage points', () => {
  const summary = summarizeSeedMetric([0.1, 0.3]);
  assert.equal(summary.mean_percent, 20);
  assert.equal(summary.population_variance_percentage_points_squared, 100);
  assert.equal(summary.population_standard_deviation_percentage_points, 10);
  assert.equal(summary.defined_seed_count, 2);
  assert.equal(summary.undefined_seed_count, 0);
});

test('undefined precision is not silently dropped from the seed aggregate', () => {
  const summary = summarizeSeedMetric([0.5, null, 0.25]);
  assert.equal(summary.mean_percent, null);
  assert.equal(summary.population_variance_percentage_points_squared, null);
  assert.equal(summary.defined_seed_count, 2);
  assert.equal(summary.undefined_seed_count, 1);
});

test('seed summary rejects invalid metric values', () => {
  assert.throws(() => summarizeSeedMetric([]), { code: 'invalid_seed_metric_values' });
  assert.throws(() => summarizeSeedMetric([1.1]), { code: 'invalid_seed_metric_values' });
  assert.throws(() => summarizeSeedMetric([Number.NaN]), { code: 'invalid_seed_metric_values' });
});
