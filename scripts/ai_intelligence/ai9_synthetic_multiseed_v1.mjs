import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { runAi9SyntheticEvaluationV2 } from './ai9_synthetic_evaluation_v2.mjs';

export const AI9_SYNTHETIC_MULTI_SEED_V1_POLICY = Object.freeze({
  version: 'ai9-synthetic-multiseed-v1',
  seeds: Object.freeze([
    20261201, 20261202, 20261203, 20261204, 20261205,
    20261206, 20261207, 20261208, 20261209, 20261210,
    20261211, 20261212, 20261213, 20261214, 20261215,
    20261216, 20261217, 20261218, 20261219, 20261220,
  ]),
  classification: 'synthetic_development_only',
});

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

export function summarizeSeedMetric(values) {
  if (!Array.isArray(values) || values.length === 0
    || values.some(value => value !== null && (!Number.isFinite(value) || value < 0 || value > 1))) {
    reject('invalid_seed_metric_values');
  }
  const missing = values.filter(value => value === null).length;
  if (missing > 0) {
    return {
      mean_percent: null,
      population_variance_percentage_points_squared: null,
      population_standard_deviation_percentage_points: null,
      defined_seed_count: values.length - missing,
      undefined_seed_count: missing,
    };
  }
  const percentages = values.map(value => value * 100);
  const meanPercent = percentages.reduce((sum, value) => sum + value, 0) / percentages.length;
  const variance = percentages.reduce((sum, value) => sum + ((value - meanPercent) ** 2), 0)
    / percentages.length;
  return {
    mean_percent: meanPercent,
    population_variance_percentage_points_squared: variance,
    population_standard_deviation_percentage_points: Math.sqrt(variance),
    defined_seed_count: values.length,
    undefined_seed_count: 0,
  };
}

function countGatePasses(perSeed, metricName) {
  return {
    precision: perSeed.filter(seed => seed[metricName].gate_status.precision === 'PASS').length,
    recall: perSeed.filter(seed => seed[metricName].gate_status.recall === 'PASS').length,
    fpr: perSeed.filter(seed => seed[metricName].gate_status.fpr === 'PASS').length,
    all_three: perSeed.filter(seed => Object.values(seed[metricName].gate_status)
      .every(status => status === 'PASS')).length,
    total_seeds: perSeed.length,
  };
}

function resultForVersion(run, version) {
  const metrics = run[version].window_metrics;
  return {
    tp: metrics.tp,
    fp: metrics.fp,
    fn: metrics.fn,
    tn: metrics.tn,
    precision: metrics.precision,
    recall: metrics.recall,
    fpr: metrics.fpr,
    gate_status: metrics.gate_status,
  };
}

function aggregateVersion(perSeed, version) {
  const versions = perSeed.map(seed => seed[version]);
  const precision = summarizeSeedMetric(versions.map(metrics => metrics.precision));
  const fpr = summarizeSeedMetric(versions.map(metrics => metrics.fpr));
  return {
    precision,
    fpr,
    per_seed_gate_pass_counts: countGatePasses(perSeed, version),
  };
}

export function runAi9SyntheticMultiSeedV1() {
  const runs = AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds.map(seed => runAi9SyntheticEvaluationV2(seed));
  if (runs.length !== AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds.length
    || runs.some((run, index) => run.seed !== AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds[index])) {
    reject('registered_seed_order_mismatch');
  }
  if (runs.some(run => run.frozen_gates.precision !== 0.8 || run.frozen_gates.recall !== 0.8
    || run.frozen_gates.fpr !== 0.05 || run.synthetic_assumptions.before_seconds !== 0
    || run.synthetic_assumptions.after_seconds !== 120 || run.synthetic_assumptions.quiet_windows_to_close !== 2)) {
    reject('registered_policy_mismatch');
  }

  const perSeed = runs.map(run => ({
    seed: run.seed,
    input_canonical_sha256: run.input_canonical_sha256,
    scored_windows: run.scored_windows,
    label_counts: run.label_counts,
    baseline: resultForVersion(run, 'baseline'),
    candidate: resultForVersion(run, 'candidate'),
  }));
  return {
    classification: AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.classification,
    registration_id: AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.version,
    candidate_policy_version: 'ai9-ewma-noise-candidate-v1',
    evaluation_policy_version: 'ai9-synthetic-window-evaluation-v2',
    assumptions: { before_seconds: 0, after_seconds: 120, quiet_windows_to_close: 2 },
    frozen_gates: { precision: 0.8, recall: 0.8, fpr: 0.05 },
    seed_count: perSeed.length,
    seeds: perSeed.map(seed => seed.seed),
    baseline_summary: aggregateVersion(perSeed, 'baseline'),
    candidate_summary: aggregateVersion(perSeed, 'candidate'),
    per_seed: perSeed,
    aggregate_gate_decision: 'NOT_DEFINED_BY_PREREGISTRATION',
    interpretation: 'Mean and variance summarize the registered synthetic generator only; they are not a new aggregate acceptance gate and do not change AI-9 FAIL or P01 NO-GO / BLOCKED.',
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.stdout.write(`${JSON.stringify(runAi9SyntheticMultiSeedV1())}\n`);
}
