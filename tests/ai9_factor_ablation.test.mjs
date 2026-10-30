import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import {
  ABLATION_SEED,
  ABLATION_SPLIT,
  generateFactorAblationScenarios,
} from '../scripts/ai_intelligence/ai9_factor_ablation.mjs';

test('factor ablations use a development-only seed, fixed baseline, and one isolated factor at a time', () => {
  const data = generateFactorAblationScenarios();
  assert.equal(data.classification, 'synthetic_development_only');
  assert.equal(data.split, ABLATION_SPLIT);
  assert.equal(data.seed, ABLATION_SEED);
  assert.ok(![20261029, 20261031, 20261102, 20261103].includes(data.seed));
  assert.equal(data.baseline_points, 30);
  assert.equal(data.scenarios.length, 6);
  assert.deepEqual(data.scenarios.map(scenario => scenario.id), [
    'flat-control', 'noise-only', 'seasonality-only', 'drift-only',
    'seasonality-plus-noise', 'seasonality-noise-and-drift',
  ]);
  assert.ok(data.scenarios.every(scenario => scenario.events.length === 3 * 24 * 60));
});

test('factor ablation generator is deterministic and labels only synthetic metrics', () => {
  const canonical = value => JSON.stringify(value);
  const first = generateFactorAblationScenarios();
  const second = generateFactorAblationScenarios();
  assert.equal(
    createHash('sha256').update(canonical(first)).digest('hex'),
    createHash('sha256').update(canonical(second)).digest('hex'),
  );
  assert.ok(first.scenarios.flatMap(scenario => scenario.events).every(event =>
    event.kind === 'server_metric' && event.source === 'server'));
});
