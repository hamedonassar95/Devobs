import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { normalizeEvent } from '../scripts/ai_intelligence/event_schema.mjs';
import {
  AI9_SYNTHETIC_EVALUATION_V2_POLICY,
  evaluateAi9SyntheticWindowV2,
  generateAi9SyntheticScenariosV2,
  scoreAi9Confusion,
  summarizeAi9SyntheticEpisodes,
} from '../scripts/ai_intelligence/ai9_synthetic_evaluation_v2.mjs';

function metricScenario(values, metric = 'cpu_percent', unit = 'percent') {
  const events = values.map((value, index) => normalizeEvent({
    schema_version: 1,
    occurred_at: new Date(Date.UTC(2026, 9, 29, 0, index)).toISOString(),
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: { name: metric, value, unit },
  }));
  return { values, events, unit };
}

test('v2 generator is deterministic and matches the preregistered synthetic class balance', () => {
  const first = generateAi9SyntheticScenariosV2();
  const second = generateAi9SyntheticScenariosV2();
  const digest = dataset => createHash('sha256')
    .update(JSON.stringify(dataset.scenarios.map(scenario => scenario.events)))
    .digest('hex');

  assert.equal(first.classification, 'synthetic_development_only');
  assert.equal(first.split, 'synthetic_evaluation_v2_only');
  assert.equal(first.seed, AI9_SYNTHETIC_EVALUATION_V2_POLICY.seed);
  assert.equal(first.scenarios.length, 56);
  assert.equal(first.scenarios.filter(scenario => scenario.group === 'injected_fault').length, 6);
  assert.deepEqual(digest(first), digest(second));

  const scoredLabels = first.scenarios.flatMap(scenario => scenario.labels.slice(30));
  assert.equal(scoredLabels.length, 15_080);
  assert.equal(scoredLabels.filter(Boolean).length, 30);
  assert.equal(scoredLabels.filter(label => !label).length, 15_050);
  assert.deepEqual(
    [...new Set(first.scenarios.map(scenario => scenario.group))],
    [
      'control_flat',
      'control_noise_only',
      'control_seasonality_only',
      'control_linear_drift_only',
      'control_seasonality_plus_noise',
      'control_seasonality_noise_and_drift',
      'injected_fault',
    ],
  );
  assert.ok(first.scenarios.every(scenario => scenario.events.length === scenario.values.length));
});

test('candidate substitutes only the EWMA channel and preserves other production channels', () => {
  const isolatedSpike = metricScenario([...Array(30).fill(34), 40]);
  const isolated = evaluateAi9SyntheticWindowV2(isolatedSpike, 30);
  assert.equal(isolated.baseline_flag, true);
  assert.equal(isolated.candidate_ewma_flag, false);
  assert.equal(isolated.candidate_flag, false);

  const largeStep = metricScenario([...Array(30).fill(34), 70]);
  const preserved = evaluateAi9SyntheticWindowV2(largeStep, 30);
  assert.equal(preserved.candidate_ewma_flag, false);
  assert.equal(preserved.candidate_flag, true);
});

test('confusion scoring uses the frozen formulas and fails precision when undefined', () => {
  const score = scoreAi9Confusion([true, true, false, false], [true, false, true, false]);
  assert.deepEqual(
    { tp: score.tp, fp: score.fp, fn: score.fn, tn: score.tn },
    { tp: 1, fp: 1, fn: 1, tn: 1 },
  );
  assert.equal(score.precision, 0.5);
  assert.equal(score.recall, 0.5);
  assert.equal(score.fpr, 0.5);
  assert.equal(score.gate_status.precision, 'FAIL');
  assert.equal(score.gate_status.recall, 'FAIL');
  assert.equal(score.gate_status.fpr, 'FAIL');

  const noPredictions = scoreAi9Confusion([true, false], [false, false]);
  assert.equal(noPredictions.precision, null);
  assert.equal(noPredictions.gate_status.precision, 'FAIL');
});

test('episode summaries close after two observed quiet windows and fail eligibility at EOF', () => {
  const closed = summarizeAi9SyntheticEpisodes([true, true, false, false, false, true, false, false]);
  assert.equal(closed.predicted_episodes, 2);
  assert.equal(closed.closed_episodes, 2);
  assert.equal(closed.open_episodes_at_end, 0);
  assert.equal(closed.eligible, true);

  const open = summarizeAi9SyntheticEpisodes([false, true]);
  assert.equal(open.open_episodes_at_end, 1);
  assert.equal(open.eligible, false);
});
