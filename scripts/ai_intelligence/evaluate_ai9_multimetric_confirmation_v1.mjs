import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createPostDetectorConfirmationLayer, POST_DETECTOR_CONFIRMATION_POLICY } from './post_detector_confirmation.mjs';
import {
  AI9_SYNTHETIC_EVALUATION_V2_POLICY,
  evaluateAi9SyntheticWindowV2,
  scoreAi9Confusion,
  summarizeAi9SyntheticEpisodes,
} from './ai9_synthetic_evaluation_v2.mjs';
import { summarizeSeedMetric } from './ai9_synthetic_multiseed_v1.mjs';
import { digestAi9MultimetricInputV1, generateAi9MultimetricServicesV1 } from './ai9_multimetric_service_generator_v1.mjs';

export const AI9_MULTIMETRIC_CONFIRMATION_V1_SEEDS = Object.freeze([
  20270201, 20270202, 20270203, 20270204, 20270205,
  20270206, 20270207, 20270208, 20270209, 20270210,
  20270211, 20270212, 20270213, 20270214, 20270215,
  20270216, 20270217, 20270218, 20270219, 20270220,
]);

export const AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY = Object.freeze({
  version: 'ai9-multimetric-confirmation-v1',
  layer_policy_version: 'ai9-post-detector-confirmation-v1',
  candidate_policy_version: 'ai9-ewma-noise-candidate-v1',
  classification: 'synthetic_development_only',
  gates: Object.freeze({ precision: 0.8, recall: 0.8, fpr: 0.05 }),
  before_seconds: 0,
  after_seconds: 120,
  quiet_windows_to_close: 2,
});

const PREVIOUS_POLICY_SEEDS = new Set([
  20261029, 20261030, 20261031, 20261102, 20261103, 20261104, 20261105,
  ...Array.from({ length: 20 }, (_, index) => 20261201 + index),
  ...Array.from({ length: 20 }, (_, index) => 20270101 + index),
]);

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function faultMatchWindow(service) {
  return service.group === 'injected_fault' ? {
    start_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample,
    last_match_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample
      + (AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.after_seconds
        / AI9_SYNTHETIC_EVALUATION_V2_POLICY.cadence_seconds),
  } : null;
}

function candidateChannels(replay) {
  const channels = Object.entries(replay.baseline_channel_flags)
    .filter(([channel, flagged]) => channel !== 'ewma' && flagged)
    .map(([channel]) => channel);
  if (replay.candidate_ewma_flag) channels.push('ewma');
  if ((channels.length > 0) !== replay.candidate_flag) reject('candidate_channel_reconciliation_mismatch');
  return channels;
}

function summarizeEpisodes(perMetric) {
  return {
    predicted_episodes: perMetric.reduce((sum, item) => sum + item.predicted_episodes, 0),
    closed_episodes: perMetric.reduce((sum, item) => sum + item.closed_episodes, 0),
    open_episodes_at_end: perMetric.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
    fault_service_matched: perMetric.some(item => item.first_alarm_match_sample !== null),
  };
}

function evaluateSeed(seed) {
  const dataset = generateAi9MultimetricServicesV1(seed);
  const inputDigest = digestAi9MultimetricInputV1(dataset);
  const baselinePredictions = [];
  const candidatePredictions = [];
  const layerPredictions = [];
  const labels = [];
  const baselineEpisodes = [];
  const candidateEpisodes = [];
  let faultServiceCount = 0;
  let baselineFaultServicesMatched = 0;
  let candidateFaultServicesMatched = 0;
  let layerFaultServicesMatched = 0;
  let persistenceConfirmedMetricWindows = 0;
  let crossMetricConfirmedMetricWindows = 0;
  const layer = createPostDetectorConfirmationLayer();

  for (const service of dataset.services) {
    const baselinePerMetric = [];
    const candidatePerMetric = [];
    let layerFaultServiceMatched = false;
    const faultWindow = faultMatchWindow(service);
    if (faultWindow) faultServiceCount++;
    const metricLength = service.metrics[0]?.events.length;
    if (!Number.isInteger(metricLength)
      || service.metrics.length !== 3
      || service.metrics.some(metric => metric.events.length !== metricLength)) {
      reject('service_metric_cadence_mismatch');
    }

    for (let index = dataset.baseline_points; index < metricLength; index++) {
      const baselineFlags = [];
      const candidateFlags = [];
      const serviceLabels = [];
      const currentMetricInputs = [];
      const eventTime = service.metrics[0].events[index].occurred_at;
      for (const metric of service.metrics) {
        const replay = evaluateAi9SyntheticWindowV2(metric, index);
        const channels = candidateChannels(replay);
        currentMetricInputs.push({ metric: metric.metric, channels });
        baselineFlags.push(replay.baseline_flag);
        candidateFlags.push(replay.candidate_flag);
        serviceLabels.push(metric.labels[index]);
      }
      const layerWindow = layer.processServiceWindow({
        serviceId: service.id,
        occurredAt: eventTime,
        metrics: currentMetricInputs,
      });
      if (layerWindow.metrics.length !== service.metrics.length) reject('confirmation_metric_count_mismatch');

      for (let metricIndex = 0; metricIndex < service.metrics.length; metricIndex++) {
        const serviceMetric = layerWindow.metrics[metricIndex];
        const label = serviceLabels[metricIndex];
        labels.push(label);
        baselinePredictions.push(baselineFlags[metricIndex]);
        candidatePredictions.push(candidateFlags[metricIndex]);
        layerPredictions.push(serviceMetric.confirmed);
        if (serviceMetric.confirmation_reasons.includes('persistent_same_channel_2_of_3')) {
          persistenceConfirmedMetricWindows++;
        }
        if (serviceMetric.confirmation_reasons.includes('cross_metric_coincidence_within_120s')) {
          crossMetricConfirmedMetricWindows++;
        }
        if (serviceMetric.incident_started && faultWindow
          && index >= faultWindow.start_sample && index <= faultWindow.last_match_sample) {
          layerFaultServiceMatched = true;
        }
      }
      for (let metricIndex = 0; metricIndex < service.metrics.length; metricIndex++) {
        baselinePerMetric[metricIndex] ??= [];
        candidatePerMetric[metricIndex] ??= [];
        baselinePerMetric[metricIndex].push(baselineFlags[metricIndex]);
        candidatePerMetric[metricIndex].push(candidateFlags[metricIndex]);
      }
    }

    const baselineSummaries = service.metrics.map((_, metricIndex) => summarizeAi9SyntheticEpisodes(
      baselinePerMetric[metricIndex],
      faultWindow,
    ));
    const candidateSummaries = service.metrics.map((_, metricIndex) => summarizeAi9SyntheticEpisodes(
      candidatePerMetric[metricIndex],
      faultWindow,
    ));
    const baselineSummary = summarizeEpisodes(baselineSummaries);
    const candidateSummary = summarizeEpisodes(candidateSummaries);
    baselineEpisodes.push({ ...baselineSummary, fault_service_matched: faultWindow ? baselineSummary.fault_service_matched : null });
    candidateEpisodes.push({ ...candidateSummary, fault_service_matched: faultWindow ? candidateSummary.fault_service_matched : null });
    if (faultWindow) {
      if (baselineSummary.fault_service_matched) baselineFaultServicesMatched++;
      if (candidateSummary.fault_service_matched) candidateFaultServicesMatched++;
      if (layerFaultServiceMatched) layerFaultServicesMatched++;
    }
  }

  const snapshot = layer.getSnapshot();
  const confusion = (predictionArray) => scoreAi9Confusion(labels, predictionArray);
  return {
    seed,
    input_canonical_sha256: inputDigest,
    scored_windows: labels.length,
    positive_windows: labels.filter(Boolean).length,
    negative_windows: labels.filter(label => !label).length,
    baseline: {
      window_metrics: confusion(baselinePredictions),
      episode_summary: {
        predicted_episodes: baselineEpisodes.reduce((sum, item) => sum + item.predicted_episodes, 0),
        closed_episodes: baselineEpisodes.reduce((sum, item) => sum + item.closed_episodes, 0),
        open_episodes_at_end: baselineEpisodes.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
        fault_services_total: faultServiceCount,
        fault_services_matched: baselineFaultServicesMatched,
        fault_services_missed: faultServiceCount - baselineFaultServicesMatched,
        interrupted_incidents: 0,
      },
    },
    current_candidate: {
      window_metrics: confusion(candidatePredictions),
      episode_summary: {
        predicted_episodes: candidateEpisodes.reduce((sum, item) => sum + item.predicted_episodes, 0),
        closed_episodes: candidateEpisodes.reduce((sum, item) => sum + item.closed_episodes, 0),
        open_episodes_at_end: candidateEpisodes.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
        fault_services_total: faultServiceCount,
        fault_services_matched: candidateFaultServicesMatched,
        fault_services_missed: faultServiceCount - candidateFaultServicesMatched,
        interrupted_incidents: 0,
      },
    },
    post_confirmation_layer: {
      window_metrics: confusion(layerPredictions),
      episode_summary: {
        predicted_episodes: snapshot.started_incidents,
        closed_episodes: snapshot.closed_incidents,
        open_episodes_at_end: snapshot.open_incidents,
        interrupted_incidents: snapshot.interrupted_incidents,
        fault_services_total: faultServiceCount,
        fault_services_matched: layerFaultServicesMatched,
        fault_services_missed: faultServiceCount - layerFaultServicesMatched,
      },
      confirmation_rule_counts: {
        persistence_confirmed_metric_windows: persistenceConfirmedMetricWindows,
        cross_metric_confirmed_metric_windows: crossMetricConfirmedMetricWindows,
      },
    },
  };
}

function summarizeVersion(seedResults, key) {
  const metrics = seedResults.map(item => item[key].window_metrics);
  const episodes = seedResults.map(item => item[key].episode_summary);
  const summary = {
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
    missed_fault_services_total: episodes.reduce((sum, item) => sum + item.fault_services_missed, 0),
    fault_services_total: episodes.reduce((sum, item) => sum + item.fault_services_total, 0),
    descriptive_incidents: {
      predicted_incidents: episodes.reduce((sum, item) => sum + item.predicted_episodes, 0),
      closed_incidents: episodes.reduce((sum, item) => sum + item.closed_episodes, 0),
      open_incidents_at_sample_end: episodes.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
      interrupted_incidents: episodes.reduce((sum, item) => sum + item.interrupted_incidents, 0),
      seeds_with_open_incidents: episodes.filter(item => item.open_episodes_at_end > 0).length,
    },
  };
  if (key === 'post_confirmation_layer') {
    summary.confirmation_rule_counts = {
      persistence_confirmed_metric_windows: seedResults.reduce((sum, item) => sum
        + item[key].confirmation_rule_counts.persistence_confirmed_metric_windows, 0),
      cross_metric_confirmed_metric_windows: seedResults.reduce((sum, item) => sum
        + item[key].confirmation_rule_counts.cross_metric_confirmed_metric_windows, 0),
    };
  }
  return summary;
}

function summarizeTradeoff(seedResults) {
  const deltas = seedResults.map(item => ({
    precisionGain: item.post_confirmation_layer.window_metrics.precision
      - item.current_candidate.window_metrics.precision,
    recallLoss: item.current_candidate.window_metrics.recall
      - item.post_confirmation_layer.window_metrics.recall,
  }));
  const meanPrecisionGain = deltas.reduce((sum, item) => sum + item.precisionGain, 0) / deltas.length;
  const meanRecallLoss = deltas.reduce((sum, item) => sum + item.recallLoss, 0) / deltas.length;
  const addedFn = seedResults.reduce((sum, item) => sum
    + item.post_confirmation_layer.window_metrics.fn - item.current_candidate.window_metrics.fn, 0);
  return {
    mean_precision_gain_percentage_points: meanPrecisionGain * 100,
    mean_recall_loss_percentage_points: meanRecallLoss * 100,
    added_missed_positive_windows_total: addedFn,
    added_missed_positive_windows_mean_per_seed: addedFn / seedResults.length,
    recall_lost_per_precision_point_gained: meanPrecisionGain > 0 ? meanRecallLoss / meanPrecisionGain : null,
    ratio_status: meanPrecisionGain > 0 ? 'DEFINED' : 'NOT_APPLICABLE_NO_POSITIVE_PRECISION_GAIN',
    seeds_with_precision_gain: deltas.filter(item => item.precisionGain > 0).length,
    seeds_with_recall_loss: deltas.filter(item => item.recallLoss > 0).length,
  };
}

function precisionCeiling() {
  const prevalence = 90 / 45_240;
  const fprLevels = [0.05, 0.01, 0.001, 0.0005, 0.0001, 0];
  return {
    positive_windows: 90,
    total_scored_windows_per_seed: 45_240,
    prevalence,
    prevalence_percent: prevalence * 100,
    assumes_recall: 1,
    formula: 'prevalence / (prevalence + (1-prevalence)*FPR)',
    maximum_precision_by_fpr: fprLevels.map(fpr => ({
      fpr_percent: fpr * 100,
      max_precision_percent: prevalence / (prevalence + (1 - prevalence) * fpr) * 100,
    })),
  };
}

export function runAi9MultimetricConfirmationEvaluationV1() {
  if (AI9_MULTIMETRIC_CONFIRMATION_V1_SEEDS.some(seed => PREVIOUS_POLICY_SEEDS.has(seed))) {
    reject('registered_seed_reused');
  }
  if (POST_DETECTOR_CONFIRMATION_POLICY.version
    !== AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.layer_policy_version
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.precision !== AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.gates.precision
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.recall !== AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.gates.recall
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.gates.fpr !== AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.gates.fpr
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.before_seconds !== AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.before_seconds
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.after_seconds !== AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.after_seconds
    || AI9_SYNTHETIC_EVALUATION_V2_POLICY.quiet_windows_to_close
      !== AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.quiet_windows_to_close) reject('registered_policy_mismatch');

  const seeds = AI9_MULTIMETRIC_CONFIRMATION_V1_SEEDS.map(evaluateSeed);
  if (seeds.length !== 20 || new Set(seeds.map(item => item.seed)).size !== 20) reject('registered_seed_list_mismatch');
  if (seeds.some(item => item.scored_windows !== 45_240
    || item.positive_windows !== 90 || item.negative_windows !== 45_150)) reject('class_balance_mismatch');

  return {
    classification: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.classification,
    registration_id: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.version,
    layer_policy_version: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.layer_policy_version,
    current_candidate_policy_version: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.candidate_policy_version,
    evaluation_policy_version: AI9_SYNTHETIC_EVALUATION_V2_POLICY.version,
    seed_count: seeds.length,
    seeds: seeds.map(item => item.seed),
    assumptions: {
      service_count: 56,
      metrics_per_service: 3,
      cadence_seconds: 60,
      baseline_points: 30,
      before_seconds: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.before_seconds,
      after_seconds: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.after_seconds,
      quiet_windows_to_close: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.quiet_windows_to_close,
    },
    frozen_gates: AI9_MULTIMETRIC_CONFIRMATION_V1_POLICY.gates,
    synthetic_prevalence: precisionCeiling(),
    baseline_summary: summarizeVersion(seeds, 'baseline'),
    current_candidate_summary: summarizeVersion(seeds, 'current_candidate'),
    post_confirmation_layer_summary: summarizeVersion(seeds, 'post_confirmation_layer'),
    paired_recall_cost_for_precision_gain: summarizeTradeoff(seeds),
    cross_metric_benchmark_exercised: true,
    per_seed: seeds,
    aggregate_gate_decision: 'NOT_DEFINED_BY_PREREGISTRATION',
    interpretation: 'Synthetic development only; no production changes. AI-9 remains FAIL and P01 remains NO-GO / BLOCKED.',
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.stdout.write(`${JSON.stringify(runAi9MultimetricConfirmationEvaluationV1())}\n`);
}
