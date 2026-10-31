import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { FROZEN_HOLDOUT_CONTRACT, validateSyntheticScore } from '../scripts/ai_intelligence/ai9_v3_frozen_holdout_once.mjs';

const evaluator = fileURLToPath(new URL('../scripts/ai_intelligence/ai9_v3_frozen_holdout_once.mjs', import.meta.url));
function sample(tp, fp, fn, tn) {
  return {
    tp, fp, fn, tn,
    precision: tp + fp ? tp / (tp + fp) : null,
    recall: tp / (tp + fn),
    fpr: fp / (fp + tn),
  };
}

test('frozen policy uses exactly four preregistered seed identifiers and window gates', () => {
  assert.deepEqual(FROZEN_HOLDOUT_CONTRACT.seeds, [20270601, 20270602, 20270603, 20270604]);
  assert.deepEqual(FROZEN_HOLDOUT_CONTRACT.gates, { precision: 0.8, recall: 0.8, fpr: 0.05 });
  assert.equal(FROZEN_HOLDOUT_CONTRACT.scored_windows, 45240);
  assert.equal(FROZEN_HOLDOUT_CONTRACT.positives, 90);
  assert.equal(FROZEN_HOLDOUT_CONTRACT.negatives, 45150);
});

test('pure scored-count contract accepts hand-authored passing counts', () => {
  assert.equal(validateSyntheticScore(sample(75, 8, 15, 45142)), true);
});

test('low recall is a frozen gate failure, not an invalid count', () => {
  assert.equal(validateSyntheticScore(sample(58, 8, 32, 45142)), false);
});

test('no-alert denominator fails precision without hiding missed faults', () => {
  assert.equal(validateSyntheticScore(sample(0, 0, 90, 45150)), false);
});

test('reject inconsistent populations, bad metrics, and count corruption', () => {
  assert.throws(() => validateSyntheticScore(sample(73, 8, 17, 45141)), { code: 'invalid_scoring_contract' });
  const invalid = sample(73, 8, 17, 45142);
  invalid.precision = 0.99;
  assert.throws(() => validateSyntheticScore(invalid), { code: 'invalid_scoring_contract' });
  const type = sample(73, 8, 17, 45142);
  type.fp = '8';
  assert.throws(() => validateSyntheticScore(type), { code: 'invalid_scoring_contract' });
});

test('CLI must reject default/unknown switches without generating holdout seeds', () => {
  for (const args of [[], ['--replay-used'], ['--fresh-once'], ['--fresh-once','--approved-sha']]) {
    const result = spawnSync(process.execPath, [evaluator, ...args], {
      encoding: 'utf8', timeout: 4000,
    });
    assert.equal(result.status, 2, result.stderr);
    assert.match(result.stderr, /manual only/);
    assert.doesNotMatch(result.stdout, /ALL_FROZEN_WINDOW_GATES_PASS/);
  }
});
// Deliberately NEVER call runOnce, scoreOneSeed or --fresh-once with a SHA here.
