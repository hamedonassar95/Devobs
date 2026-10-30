import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { normalizeEvent } from './event_ingest.mjs';
import { analyzeMetricEventsWithAlpha } from './ai9_alpha_detector.mjs';

export const ABLATION_POLICY_VERSION = 'ai9-factor-ablation-v1';
export const ABLATION_SEED = 20261104;
export const ABLATION_SPLIT = 'development_factor_ablation_only';
const WINDOW_COUNT = 3 * 24 * 60;
const WINDOW_SECONDS = 60;
const BASELINE_POINTS = 30;
const BASE_INSTANT = Date.parse('2026-10-29T00:00:00.000Z');
const FACTORS = Object.freeze([
  { id: 'flat-control', seasonality: 0, noise: 0, drift: 0 },
  { id: 'noise-only', seasonality: 0, noise: 0.7, drift: 0 },
  { id: 'seasonality-only', seasonality: 7, noise: 0, drift: 0 },
  { id: 'drift-only', seasonality: 0, noise: 0, drift: 10 },
  { id: 'seasonality-plus-noise', seasonality: 7, noise: 0.7, drift: 0 },
  { id: 'seasonality-noise-and-drift', seasonality: 7, noise: 0.7, drift: 10 },
]);
const DETECTORS = Object.freeze(['z_score', 'moving_average', 'ewma', 'error_rate_spike']);

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6D2B79F5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4_294_967_296;
  };
}

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function event(value, scenarioIndex, sampleIndex) {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: new Date(BASE_INSTANT + (scenarioIndex * 10_000_000_000)
      + (sampleIndex * WINDOW_SECONDS * 1_000)).toISOString(),
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: { name: 'cpu_percent', value: Number(value.toFixed(4)), unit: 'percent' },
  });
}

function makeScenario(factors, scenarioIndex) {
  const random = seededRandom(ABLATION_SEED);
  const values = Array.from({ length: WINDOW_COUNT }, (_, index) => {
    const dailyPhase = (2 * Math.PI * (index % 1_440)) / 1_440;
    const seasonal = factors.seasonality * Math.sin(dailyPhase - Math.PI / 3);
    const drift = factors.drift * (index / (WINDOW_COUNT - 1));
    const noise = ((random() * 2 - 1) * factors.noise);
    return 34 + seasonal + drift + noise;
  });
  return {
    id: factors.id,
    class: 'fault_free_controlled_factor',
    events: values.map((value, index) => event(value, scenarioIndex, index)),
  };
}

export function generateFactorAblationScenarios() {
  return {
    classification: 'synthetic_development_only',
    split: ABLATION_SPLIT,
    seed: ABLATION_SEED,
    window_seconds: WINDOW_SECONDS,
    baseline_points: BASELINE_POINTS,
    scenarios: FACTORS.map((factors, index) => makeScenario(factors, index)),
  };
}

function analyzeScenario(scenario, alpha) {
  const signalCounts = Object.fromEntries(DETECTORS.map(detector => [detector, 0]));
  let flaggedWindows = 0;
  let overlappingSignalWindows = 0;
  const eligibleWindows = scenario.events.length - BASELINE_POINTS;
  for (let index = BASELINE_POINTS; index < scenario.events.length; index++) {
    const batch = scenario.events.slice(index - BASELINE_POINTS, index + 1);
    const [analysis] = analyzeMetricEventsWithAlpha(batch, alpha, BASELINE_POINTS);
    if (!analysis) reject('missing_metric_analysis');
    if (analysis.status === 'anomaly_candidate') flaggedWindows++;
    if (analysis.signals.length > 1) overlappingSignalWindows++;
    for (const detector of analysis.signals) signalCounts[detector]++;
  }
  return {
    policy_version: ABLATION_POLICY_VERSION,
    scenario_id: scenario.id,
    alpha,
    eligible_windows: eligibleWindows,
    false_alarm_windows: flaggedWindows,
    false_alarm_rate: flaggedWindows / eligibleWindows,
    detector_signal_counts: signalCounts,
    overlapping_signal_windows: overlappingSignalWindows,
  };
}

export function runFactorAblationDiagnostic() {
  const data = generateFactorAblationScenarios();
  const inputCanonicalSha256 = createHash('sha256').update(JSON.stringify(data)).digest('hex');
  const results = data.scenarios.flatMap(scenario => [0.3, 0.5]
    .map(alpha => analyzeScenario(scenario, alpha)));
  const report = {
    policy_version: ABLATION_POLICY_VERSION,
    classification: data.classification,
    split: data.split,
    seed: data.seed,
    scenario_count: data.scenarios.length,
    baseline_points: data.baseline_points,
    input_canonical_sha256: inputCanonicalSha256,
    results,
    limits: [
      'Exploratory development ablation only; no fault windows, formal evaluator, gates, or RCA score.',
      'Each factor comparison uses one synthetic recipe and seed; it does not establish real-world causality.',
      'Baseline length is held at 30; baseline-length effects are not measured by this run.',
      'Detector signal counts may overlap and are attribution counts, not independent window totals.',
    ],
  };
  report.outputCanonicalSha256 = createHash('sha256').update(JSON.stringify(report)).digest('hex');
  return report;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.stdout.write(`${JSON.stringify(runFactorAblationDiagnostic())}\n`);
}
