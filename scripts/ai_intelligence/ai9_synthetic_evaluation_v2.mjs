import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { analyzeMetricEvents } from './anomaly_detector.mjs';
import { scoreEwmaNoiseCandidate } from './ai9_ewma_noise_candidate.mjs';
import { canonicalJson, normalizeEvent } from './event_schema.mjs';

export const AI9_SYNTHETIC_EVALUATION_V2_POLICY = Object.freeze({
  version: 'ai9-synthetic-window-evaluation-v2',
  classification: 'synthetic_development_only',
  seed: 20261105,
  baseline_points: 30,
  cadence_seconds: 60,
  fault_start_sample: 150,
  fault_duration_windows: 5,
  before_seconds: 0,
  after_seconds: 120,
  quiet_windows_to_close: 2,
  gates: Object.freeze({ precision: 0.8, recall: 0.8, fpr: 0.05 }),
});

const BASE_INSTANT = Date.parse('2026-10-29T00:00:00.000Z');
const SCENARIO_START_SPACING_MS = 10_000_000_000;
const NOISE_AMPLITUDE = 0.7;
const CONTROL_RECIPES = Object.freeze([
  { id: 'flat', count: 8, seasonality: 0, noise: 0, drift: 0 },
  { id: 'noise_only', count: 9, seasonality: 0, noise: NOISE_AMPLITUDE, drift: 0 },
  { id: 'seasonality_only', count: 8, seasonality: 7, noise: 0, drift: 0 },
  { id: 'linear_drift_only', count: 8, seasonality: 0, noise: 0, drift: 10 },
  { id: 'seasonality_plus_noise', count: 8, seasonality: 7, noise: NOISE_AMPLITUDE, drift: 0 },
  {
    id: 'seasonality_noise_and_drift',
    count: 9,
    seasonality: 7,
    noise: NOISE_AMPLITUDE,
    drift: 10,
  },
]);
const FAULT_RECIPES = Object.freeze([
  { id: 'fault_latency_step', metric: 'latency_ms', unit: 'milliseconds', baseline: 100, step: 120 },
  { id: 'fault_cpu_step', metric: 'cpu_percent', unit: 'percent', baseline: 34, step: 18 },
  { id: 'fault_disk_step', metric: 'disk_percent', unit: 'percent', baseline: 34, step: 25 },
  { id: 'fault_error_rate_step', metric: 'error_rate', unit: 'percent', baseline: 0.5, step: 4 },
  { id: 'fault_request_rate_drop', metric: 'request_rate', unit: 'per_second', baseline: 34, step: -18 },
  { id: 'fault_memory_step', metric: 'memory_percent', unit: 'percent', baseline: 34, step: 15 },
]);
const SCORED_FIRST_SAMPLE = AI9_SYNTHETIC_EVALUATION_V2_POLICY.baseline_points;
const DETECTION_MATCH_LAST_SAMPLE = AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample
  + (AI9_SYNTHETIC_EVALUATION_V2_POLICY.after_seconds / AI9_SYNTHETIC_EVALUATION_V2_POLICY.cadence_seconds);

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

function boundedValue(value, unit) {
  const bounded = unit === 'percent' ? Math.min(100, Math.max(0, value)) : Math.max(0, value);
  return Number(bounded.toFixed(4));
}

function metricEvent(metric, unit, value, scenarioIndex, sampleIndex) {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: new Date(BASE_INSTANT + (scenarioIndex * SCENARIO_START_SPACING_MS)
      + (sampleIndex * AI9_SYNTHETIC_EVALUATION_V2_POLICY.cadence_seconds * 1_000)).toISOString(),
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: { name: metric, value: boundedValue(value, unit), unit },
  });
}

function makeScenario({ id, group, metric, unit, baseline, seasonality = 0, noise = NOISE_AMPLITUDE,
  drift = 0, faultStep = 0 }, scenarioIndex, random) {
  const length = scenarioIndex < 40 ? 299 : 300;
  const values = [];
  const labels = [];
  const events = [];
  for (let index = 0; index < length; index++) {
    const dailyPhase = (2 * Math.PI * (index % 1_440)) / 1_440;
    const seasonalValue = seasonality * Math.sin(dailyPhase - Math.PI / 3);
    const driftValue = drift * (index / (length - 1));
    const noiseValue = ((random() * 2) - 1) * noise;
    const inFault = faultStep !== 0 && index >= AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample
      && index < AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample
        + AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_duration_windows;
    const value = boundedValue(baseline + seasonalValue + driftValue + noiseValue
      + (inFault ? faultStep : 0), unit);
    values.push(value);
    labels.push(inFault);
    events.push(metricEvent(metric, unit, value, scenarioIndex, index));
  }
  return { id, group, metric, unit, values, labels, events };
}

export function generateAi9SyntheticScenariosV2(seed = AI9_SYNTHETIC_EVALUATION_V2_POLICY.seed) {
  if (!Number.isInteger(seed) || seed < 0 || seed > 0xFFFF_FFFF) reject('invalid_seed');
  const random = seededRandom(seed);
  const scenarios = [];
  for (const recipe of CONTROL_RECIPES) {
    for (let ordinal = 1; ordinal <= recipe.count; ordinal++) {
      scenarios.push(makeScenario({
        id: `control_${recipe.id}_${String(ordinal).padStart(2, '0')}`,
        group: `control_${recipe.id}`,
        metric: 'cpu_percent',
        unit: 'percent',
        baseline: 34,
        seasonality: recipe.seasonality,
        noise: recipe.noise,
        drift: recipe.drift,
      }, scenarios.length, random));
    }
  }
  for (const recipe of FAULT_RECIPES) {
    scenarios.push(makeScenario({
      id: recipe.id,
      group: 'injected_fault',
      metric: recipe.metric,
      unit: recipe.unit,
      baseline: recipe.baseline,
      faultStep: recipe.step,
    }, scenarios.length, random));
  }
  return {
    classification: AI9_SYNTHETIC_EVALUATION_V2_POLICY.classification,
    split: 'synthetic_evaluation_v2_only',
    seed,
    window_seconds: AI9_SYNTHETIC_EVALUATION_V2_POLICY.cadence_seconds,
    baseline_points: AI9_SYNTHETIC_EVALUATION_V2_POLICY.baseline_points,
    scenarios,
  };
}

function digestInput(dataset) {
  const digestShape = {
    classification: dataset.classification,
    split: dataset.split,
    seed: dataset.seed,
    window_seconds: dataset.window_seconds,
    baseline_points: dataset.baseline_points,
    scenarios: dataset.scenarios.map(scenario => ({
      id: scenario.id,
      group: scenario.group,
      metric: scenario.metric,
      unit: scenario.unit,
      values: scenario.values,
      labels: scenario.labels,
    })),
  };
  return createHash('sha256').update(canonicalJson(digestShape)).digest('hex');
}

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

/** Apply the frozen baseline/candidate composition to one observation window. */
export function evaluateAi9SyntheticWindowV2(scenario, sampleIndex) {
  if (!scenario || !Array.isArray(scenario.events) || !Array.isArray(scenario.values)
    || !Number.isInteger(sampleIndex) || sampleIndex < SCORED_FIRST_SAMPLE
    || sampleIndex >= scenario.events.length) reject('invalid_scenario_window');

  const productionWindow = scenario.events.slice(sampleIndex - SCORED_FIRST_SAMPLE, sampleIndex + 1);
  const [baseline] = analyzeMetricEvents(productionWindow);
  if (!baseline?.detectors) reject('missing_production_analysis');

  const candidateValues = scenario.values.slice(Math.max(0, sampleIndex - 32), sampleIndex + 1);
  const candidateEwma = scoreEwmaNoiseCandidate(candidateValues, {
    alpha: 0.3,
    baselinePoints: AI9_SYNTHETIC_EVALUATION_V2_POLICY.baseline_points,
    unit: scenario.unit,
  });
  const preservedChannels = ['z_score', 'moving_average', 'error_rate_spike'];
  const candidateFlag = preservedChannels.some(channel => baseline.detectors[channel].flagged)
    || candidateEwma.flagged;

  return {
    baseline_flag: baseline.status === 'anomaly_candidate',
    candidate_flag: candidateFlag,
    candidate_ewma_flag: candidateEwma.flagged,
  };
}

export function scoreAi9Confusion(labels, predictions) {
  if (!Array.isArray(labels) || !Array.isArray(predictions) || labels.length !== predictions.length
    || labels.some(value => typeof value !== 'boolean')
    || predictions.some(value => typeof value !== 'boolean')) reject('invalid_score_vectors');
  const result = { tp: 0, fp: 0, fn: 0, tn: 0 };
  labels.forEach((label, index) => {
    if (label && predictions[index]) result.tp++;
    else if (!label && predictions[index]) result.fp++;
    else if (label) result.fn++;
    else result.tn++;
  });
  const precision = result.tp + result.fp === 0 ? null : result.tp / (result.tp + result.fp);
  const recall = result.tp + result.fn === 0 ? null : result.tp / (result.tp + result.fn);
  const fpr = result.fp + result.tn === 0 ? null : result.fp / (result.fp + result.tn);
  return {
    ...result,
    windows: labels.length,
    precision,
    recall,
    fpr,
    gate_status: {
      precision: precision !== null && precision >= AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.precision
        ? 'PASS' : 'FAIL',
      recall: recall !== null && recall >= AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.recall
        ? 'PASS' : 'FAIL',
      fpr: fpr !== null && fpr <= AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.fpr ? 'PASS' : 'FAIL',
    },
  };
}

export function summarizeAi9SyntheticEpisodes(flags, fault = null, firstScoredSample = SCORED_FIRST_SAMPLE) {
  if (!Array.isArray(flags) || flags.some(flag => typeof flag !== 'boolean')) reject('invalid_episode_flags');
  const episodes = [];
  let active = null;
  let quietCount = 0;
  flags.forEach((flag, offset) => {
    const sampleIndex = firstScoredSample + offset;
    if (flag) {
      if (!active) active = { start_sample: sampleIndex };
      quietCount = 0;
    } else if (active) {
      quietCount++;
      if (quietCount === AI9_SYNTHETIC_EVALUATION_V2_POLICY.quiet_windows_to_close) {
        episodes.push({ ...active, end_sample: sampleIndex, closed: true });
        active = null;
        quietCount = 0;
      }
    }
  });
  if (active) episodes.push({ ...active, end_sample: null, closed: false });

  const eligible = episodes.every(episode => episode.closed);
  const firstFaultAlarm = episodes.find(episode => episode.start_sample >= fault?.start_sample
    && episode.start_sample <= fault?.last_match_sample);
  return {
    predicted_episodes: episodes.length,
    closed_episodes: episodes.filter(episode => episode.closed).length,
    open_episodes_at_end: episodes.filter(episode => !episode.closed).length,
    eligible,
    matched_fault: Boolean(fault && firstFaultAlarm),
    first_alarm_match_sample: fault && firstFaultAlarm ? firstFaultAlarm.start_sample : null,
  };
}

function summarizeVersion(labels, predictions, episodeScenarios, faultCount) {
  const confusion = scoreAi9Confusion(labels, predictions);
  const candidateFaultEpisodes = episodeScenarios.filter(episode => episode.first_alarm_match_sample !== null);
  const open = episodeScenarios.reduce((sum, episode) => sum + episode.open_episodes_at_end, 0);
  const predicted = episodeScenarios.reduce((sum, episode) => sum + episode.predicted_episodes, 0);
  const closed = episodeScenarios.reduce((sum, episode) => sum + episode.closed_episodes, 0);
  return {
    window_metrics: confusion,
    episode_summary: {
      fault_scenarios: faultCount,
      predicted_episodes: predicted,
      closed_episodes: closed,
      open_episodes_at_end: open,
      eligible: open === 0,
      fault_scenarios_detected_in_frozen_match_window: candidateFaultEpisodes.length,
    },
  };
}

function countLabels(dataset) {
  return dataset.scenarios.flatMap(scenario => scenario.labels.slice(SCORED_FIRST_SAMPLE))
    .reduce((counts, label) => {
      counts[label ? 'positive' : 'negative']++;
      return counts;
    }, { positive: 0, negative: 0 });
}

export function runAi9SyntheticEvaluationV2(seed = AI9_SYNTHETIC_EVALUATION_V2_POLICY.seed) {
  const dataset = generateAi9SyntheticScenariosV2(seed);
  const labelCounts = countLabels(dataset);
  const labels = [];
  const baselinePredictions = [];
  const candidatePredictions = [];
  const baselineEpisodes = [];
  const candidateEpisodes = [];
  for (const scenario of dataset.scenarios) {
    const scenarioLabels = [];
    const scenarioBaseline = [];
    const scenarioCandidate = [];
    for (let index = SCORED_FIRST_SAMPLE; index < scenario.events.length; index++) {
      const result = evaluateAi9SyntheticWindowV2(scenario, index);
      const label = scenario.labels[index];
      labels.push(label);
      scenarioLabels.push(label);
      baselinePredictions.push(result.baseline_flag);
      candidatePredictions.push(result.candidate_flag);
      scenarioBaseline.push(result.baseline_flag);
      scenarioCandidate.push(result.candidate_flag);
    }
    if (scenarioLabels.length !== scenarioBaseline.length || scenarioLabels.length !== scenarioCandidate.length) {
      reject('scenario_score_count_mismatch');
    }
    const fault = scenario.group === 'injected_fault' ? {
      start_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample,
      last_match_sample: DETECTION_MATCH_LAST_SAMPLE,
    } : null;
    baselineEpisodes.push(summarizeAi9SyntheticEpisodes(scenarioBaseline, fault));
    candidateEpisodes.push(summarizeAi9SyntheticEpisodes(scenarioCandidate, fault));
  }
  const faultCount = dataset.scenarios.filter(scenario => scenario.group === 'injected_fault').length;
  const baseline = summarizeVersion(labels, baselinePredictions, baselineEpisodes, faultCount);
  const candidate = summarizeVersion(labels, candidatePredictions, candidateEpisodes, faultCount);
  const allGates = [
    ...Object.values(baseline.window_metrics.gate_status),
    ...Object.values(candidate.window_metrics.gate_status),
  ];
  const candidatePolicy = 'ai9-ewma-noise-candidate-v1';
  return {
    classification: dataset.classification,
    registration_id: AI9_SYNTHETIC_EVALUATION_V2_POLICY.version,
    seed: dataset.seed,
    input_canonical_sha256: digestInput(dataset),
    candidate_policy_version: candidatePolicy,
    evaluation_policy_version: AI9_SYNTHETIC_EVALUATION_V2_POLICY.version,
    synthetic_assumptions: {
      before_seconds: AI9_SYNTHETIC_EVALUATION_V2_POLICY.before_seconds,
      after_seconds: AI9_SYNTHETIC_EVALUATION_V2_POLICY.after_seconds,
      quiet_windows_to_close: AI9_SYNTHETIC_EVALUATION_V2_POLICY.quiet_windows_to_close,
    },
    scenario_count: dataset.scenarios.length,
    fault_scenario_count: dataset.scenarios.filter(scenario => scenario.group === 'injected_fault').length,
    scored_windows: labelCounts.positive + labelCounts.negative,
    label_counts: labelCounts,
    frozen_gates: AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates,
    baseline,
    candidate,
    selected_window_gate_assessment: allGates.every(status => status === 'PASS') ? 'PASS' : 'FAIL',
    interpretation: 'Development-only synthetic comparison. This assessment does not change the recorded AI-9 FAIL or P01 NO-GO / BLOCKED states.',
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.stdout.write(`${JSON.stringify(runAi9SyntheticEvaluationV2())}\n`);
}
