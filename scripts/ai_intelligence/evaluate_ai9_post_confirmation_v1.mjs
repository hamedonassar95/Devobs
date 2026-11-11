import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createPostDetectorConfirmationLayer } from './post_detector_confirmation.mjs';
import {
  AI9_SYNTHETIC_EVALUATION_V2_POLICY,
  digestAi9SyntheticInputV2,
  evaluateAi9SyntheticWindowV2,
  generateAi9SyntheticScenariosV2,
  scoreAi9Confusion,
  summarizeAi9SyntheticEpisodes,
} from './ai9_synthetic_evaluation_v2.mjs';
import { summarizeSeedMetric } from './ai9_synthetic_multiseed_v1.mjs';

export const AI9_POST_CONFIRMATION_V1_SEEDS = Object.freeze([
  20270101, 20270102, 20270103, 20270104, 20270105,
  20270106, 20270107, 20270108, 20270109, 20270110,
  20270111, 20270112, 20270113, 20270114, 20270115,
  20270116, 20270117, 20270118, 20270119, 20270120,
]);

export const AI9_POST_CONFIRMATION_V1_POLICY = Object.freeze({
  version: 'ai9-post-detector-confirmation-v1',
  candidate_input: 'ai9-ewma-noise-candidate-v1',
  classification: 'synthetic_development_only',
  before_seconds: 0,
  after_seconds: 120,
  quiet_windows_to_close: 2,
  gates: Object.freeze({ precision: 0.8, recall: 0.8, fpr: 0.05 }),
});

const PREVIOUS_POLICY_SEEDS = new Set([
  20261029, 20261030, 20261031, 20261102, 20261103, 20261104, 20261105,
  ...Array.from({ length: 20 }, (_, index) => 20261201 + index),
]);

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function faultMatchWindow(scenario) {
  return scenario.group === 'injected_fault' ? {
    start_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample,
    last_match_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample
      + (AI9_POST_CONFIRMATION_V1_POLICY.after_seconds / AI9_SYNTHETIC_EVALUATION_V2_POLICY.cadence_seconds),
  } : null;
}

function summarizeOfflineEpisodes(perScenario) {
  return {
    predicted_episodes: perScenario.reduce((sum, item) => sum + item.predicted_episodes, 0),
    closed_episodes: perScenario.reduce((sum, item) => sum + item.closed_episodes, 0),
    open_episodes_at_end: perScenario.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
    fault_scenarios_matched: perScenario.filter(item => item.first_alarm_match_sample !== null).length,
  };
}

function summarizeVersion(seedResults, key) {
  const metrics = seedResults.map(item => item[key].window_metrics);
  const episodes = seedResults.map(item => item[key].episode_summary);
  return {
    precision: summarizeSeedMetric(metrics.map(item => item.precision)),
    recall: summarizeSeedMetric(metrics.map(item => item.recall)),
    fpr: summarizeSeedMetric(metrics.map(item => item.fpr)),
    gate_pass_counts: {
      precision: metrics.filter(item => item.gate_status.precision === 'PASS').length,
      recall: metrics.filter(item => item.gate_status.recall === 'PASS').length,
      fpr: metrics.filter(item => item.gate_status.fpr === 'PASS').length,
      all_three: metrics.filter(item => Object.values(item.gate_status).every(status => status === 'PASS')).length,
      seed_count: metrics.length,
    },
    missed_positive_windows_total: metrics.reduce((sum, item) => sum + item.fn, 0),
    missed_positive_windows_mean_per_seed: metrics.reduce((sum, item) => sum + item.fn, 0) / metrics.length,
    injected_fault_scenarios_total: episodes.reduce((sum, item) => sum + item.fault_scenarios_total, 0),
    injected_fault_scenarios_missed_total: episodes.reduce((sum, item) => sum + item.fault_scenarios_missed, 0),
    descriptive_incidents: {
      predicted_incidents: episodes.reduce((sum, item) => sum + item.predicted_episodes, 0),
      closed_incidents: episodes.reduce((sum, item) => sum + item.closed_episodes, 0),
      open_incidents_at_sample_end: episodes.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
      interrupted_incidents: episodes.reduce((sum, item) => sum + item.interrupted_episodes, 0),
      seeds_with_open_incidents: episodes.filter(item => item.open_episodes_at_end > 0).length,
    },
  };
}

function getTheoreticalPrecisionLimits() {
  const prevalence = 30 / 15_080;
  const fprLevels = [0.05, 0.01, 0.001, 0.0005, 0.0001, 0];
  return {
    positive_windows: 30,
    total_scored_windows_per_seed: 15_080,
    prevalence,
    prevalence_percent: prevalence * 100,
    negative_prevalence_percent: (1 - prevalence) * 100,
    assumes_recall: 1,
    formula: 'prevalence / (prevalence + (1-prevalence)*FPR)',
    maximum_precision_by_fpr: fprLevels.map(fpr => ({
      fpr_percent: fpr * 100,
      max_precision_percent: (prevalence / (prevalence + ((1 - prevalence) * fpr))) * 100,
    })),
  };
}

function evaluateSeed(seed) {
  const dataset = generateAi9SyntheticScenariosV2(seed);
  const inputDigest = digestAi9SyntheticInputV2(dataset);
  const baselineLabels = [];
  const baselinePredictions = [];
  const currentLabels = [];
  const currentPredictions = [];
  const layerLabels = [];
  const layerPredictions = [];
  const baselineEpisodes = [];
  const currentEpisodes = [];
  let layerFaultScenariosMatched = 0;
  const layer = createPostDetectorConfirmationLayer();

  for (const scenario of dataset.scenarios) {
    const scenarioBaseline = [];
    const scenarioCurrent = [];
    let scenarioFaultMatched = false;
    const faultWindow = faultMatchWindow(scenario);

    for (let index = AI9_SYNTHETIC_EVALUATION_V2_POLICY.baseline_points;
      index < scenario.events.length; index++) {
      const replay = evaluateAi9SyntheticWindowV2(scenario, index);
      const channels = Object.entries(replay.baseline_channel_flags)
        .filter(([channel, flagged]) => channel !== 'ewma' && flagged)
        .map(([channel]) => channel);
      if (replay.candidate_ewma_flag) channels.push('ewma');
      if ((channels.length > 0) !== replay.candidate_flag) reject('candidate_channel_reconciliation_mismatch');

      const output = layer.processServiceWindow({
        serviceId: scenario.id,
        occurredAt: scenario.events[index].occurred_at,
        metrics: [{ metric: scenario.metric, channels }],
      });
      const confirmed = output.metrics[0]?.confirmed;
      if (typeof confirmed !== 'boolean') reject('missing_confirmation_result');
      if (output.metrics[0].incident_started && faultWindow
        && index >= faultWindow.start_sample && index <= faultWindow.last_match_sample) {
        scenarioFaultMatched = true;
      }

      const label = scenario.labels[index];
      baselineLabels.push(label);
      currentLabels.push(label);
      layerLabels.push(label);
      baselinePredictions.push(replay.baseline_flag);
      currentPredictions.push(replay.candidate_flag);
      layerPredictions.push(confirmed);
      scenarioBaseline.push(replay.baseline_flag);
      scenarioCurrent.push(replay.candidate_flag);
    }

    baselineEpisodes.push(summarizeAi9SyntheticEpisodes(scenarioBaseline, faultWindow));
    currentEpisodes.push(summarizeAi9SyntheticEpisodes(scenarioCurrent, faultWindow));
    if (scenarioFaultMatched) layerFaultScenariosMatched++;
  }

  const snapshot = layer.getSnapshot();
  const faultScenarioCount = dataset.scenarios.filter(scenario => scenario.group === 'injected_fault').length;
  const baselineEpisodeSummary = summarizeOfflineEpisodes(baselineEpisodes);
  const currentEpisodeSummary = summarizeOfflineEpisodes(currentEpisodes);
  const baseline = {
    window_metrics: scoreAi9Confusion(baselineLabels, baselinePredictions),
    episode_summary: {
      ...baselineEpisodeSummary,
      fault_scenarios_total: faultScenarioCount,
      fault_scenarios_missed: faultScenarioCount - baselineEpisodeSummary.fault_scenarios_matched,
      interrupted_episodes: 0,
    },
  };
  const currentCandidate = {
    window_metrics: scoreAi9Confusion(currentLabels, currentPredictions),
    episode_summary: {
      ...currentEpisodeSummary,
      fault_scenarios_total: faultScenarioCount,
      fault_scenarios_missed: faultScenarioCount - currentEpisodeSummary.fault_scenarios_matched,
      interrupted_episodes: 0,
    },
  };
  const layerVersion = {
    window_metrics: scoreAi9Confusion(layerLabels, layerPredictions),
    episode_summary: {
      predicted_episodes: snapshot.started_incidents,
      closed_episodes: snapshot.closed_incidents,
      open_episodes_at_end: snapshot.open_incidents,
      interrupted_episodes: snapshot.interrupted_incidents,
      fault_scenarios_total: faultScenarioCount,
      fault_scenarios_matched: layerFaultScenariosMatched,
      fault_scenarios_missed: faultScenarioCount - layerFaultScenariosMatched,
    },
  };
  return {
    seed,
    input_canonical_sha256: inputDigest,
    scored_windows: baselineLabels.length,
    positive_windows: baselineLabels.filter(Boolean).length,
    negative_windows: baselineLabels.filter(label => !label).length,
    baseline,
    current_candidate: currentCandidate,
    post_confirmation_layer: layerVersion,
  };
}

function summarizePairedTradeoff(seedResults) {
  const deltas = seedResults.map(item => ({
    precisionGain: item.post_confirmation_layer.window_metrics.precision
      - item.current_candidate.window_metrics.precision,
    recallLoss: item.current_candidate.window_metrics.recall
      - item.post_confirmation_layer.window_metrics.recall,
  }));
  const meanPrecisionGain = deltas.reduce((sum, item) => sum + item.precisionGain, 0) / deltas.length;
  const meanRecallLoss = deltas.reduce((sum, item) => sum + item.recallLoss, 0) / deltas.length;
  const addedMissedPositiveWindows = seedResults.reduce((sum, item) => sum
    + item.post_confirmation_layer.window_metrics.fn - item.current_candidate.window_metrics.fn, 0);
  return {
    mean_precision_gain_percentage_points: meanPrecisionGain * 100,
    mean_recall_loss_percentage_points: meanRecallLoss * 100,
    added_missed_positive_windows_total: addedMissedPositiveWindows,
    added_missed_positive_windows_mean_per_seed: addedMissedPositiveWindows / seedResults.length,
    mean_recall_lost_per_precision_point_gained: meanPrecisionGain > 0
      ? meanRecallLoss / meanPrecisionGain
      : null,
    ratio_status: meanPrecisionGain > 0 ? 'DEFINED' : 'NOT_APPLICABLE_NO_POSITIVE_PRECISION_GAIN',
    seeds_with_precision_gain: deltas.filter(item => item.precisionGain > 0).length,
    seeds_with_recall_loss: deltas.filter(item => item.recallLoss > 0).length,
  };
}

export function runAi9PostConfirmationEvaluationV1() {
  if (AI9_POST_CONFIRMATION_V1_SEEDS.some(seed => PREVIOUS_POLICY_SEEDS.has(seed))) {
    reject('registered_seed_reused');
  }
  if (AI9_SYNTHETIC_EVALUATION_V2_POLICY.before_seconds !== AI9_POST_CONFIRMATION_V1_POLICY.before_seconds
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.after_seconds !== AI9_POST_CONFIRMATION_V1_POLICY.after_seconds
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.quiet_windows_to_close
      !== AI9_POST_CONFIRMATION_V1_POLICY.quiet_windows_to_close
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.precision !== AI9_POST_CONFIRMATION_V1_POLICY.gates.precision
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.recall !== AI9_POST_CONFIRMATION_V1_POLICY.gates.recall
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.fpr !== AI9_POST_CONFIRMATION_V1_POLICY.gates.fpr) {
    reject('registered_evaluation_policy_mismatch');
  }
  const seedResults = AI9_POST_CONFIRMATION_V1_SEEDS.map(evaluateSeed);
  const expectedSeedCount = 20;
  if (seedResults.length !== expectedSeedCount || new Set(seedResults.map(item => item.seed)).size !== expectedSeedCount) {
    reject('registered_seed_list_mismatch');
  }
  if (seedResults.some(item => item.scored_windows !== 15_080
    || item.positive_windows !== 30 || item.negative_windows !== 15_050)) reject('frozen_input_class_balance_mismatch');
  return {
    classification: AI9_POST_CONFIRMATION_V1_POLICY.classification,
    registration_id: AI9_POST_CONFIRMATION_V1_POLICY.version,
    layer_policy_version: AI9_POST_CONFIRMATION_V1_POLICY.version,
    current_candidate_policy_version: 'ai9-ewma-noise-candidate-v1',
    evaluation_policy_version: 'ai9-synthetic-window-evaluation-v2',
    seed_count: seedResults.length,
    seeds: seedResults.map(item => item.seed),
    assumptions: {
      cadence_seconds: 60,
      baseline_points: 30,
      before_seconds: AI9_POST_CONFIRMATION_V1_POLICY.before_seconds,
      after_seconds: AI9_POST_CONFIRMATION_V1_POLICY.after_seconds,
      quiet_windows_to_close: AI9_POST_CONFIRMATION_V1_POLICY.quiet_windows_to_close,
    },
    frozen_gates: AI9_POST_CONFIRMATION_V1_POLICY.gates,
    synthetic_prevalence: getTheoreticalPrecisionLimits(),
    baseline_summary: summarizeVersion(seedResults, 'baseline'),
    current_candidate_summary: summarizeVersion(seedResults, 'current_candidate'),
    post_confirmation_layer_summary: summarizeVersion(seedResults, 'post_confirmation_layer'),
    paired_recall_cost_for_precision_gain: summarizePairedTradeoff(seedResults),
    cross_metric_route_exercised_in_benchmark: false,
    per_seed: seedResults,
    aggregate_gate_decision: 'NOT_DEFINED_BY_PREREGISTRATION',
    interpretation: 'Synthetic development only. The layer is not production-integrated; AI-9 remains FAIL and P01 remains NO-GO / BLOCKED.',
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.stdout.write(`${JSON.stringify(runAi9PostConfirmationEvaluationV1())}\n`);
}
