import path from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  digestAi9MultimetricInputV1,
  generateAi9MultimetricServicesV1,
} from './ai9_multimetric_service_generator_v1.mjs';
import { evaluateAi9SyntheticWindowV2 } from './ai9_synthetic_evaluation_v2.mjs';
import { createPostDetectorConfirmationLayer } from './post_detector_confirmation.mjs';

export const AI9_FP_SLICE_EXPLORATION_POLICY = Object.freeze({
  version: 'ai9-fp-slice-posthoc-exploration-v1',
  classification: 'synthetic_development_only',
  first_seed: 20270201,
  last_seed: 20270220,
  production_use: false,
});

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function checkedSeed(seed) {
  if (!Number.isInteger(seed)
      || seed < AI9_FP_SLICE_EXPLORATION_POLICY.first_seed
      || seed > AI9_FP_SLICE_EXPLORATION_POLICY.last_seed) reject('unregistered_or_invalid_seed');
  return seed;
}

function newCounts() {
  return { tp: 0, fp: 0, fn: 0, tn: 0 };
}

function incrementCounts(counts, label, predicted) {
  if (label && predicted) counts.tp++;
  else if (label && !predicted) counts.fn++;
  else if (!label && predicted) counts.fp++;
  else counts.tn++;
}

function groupSlot(collection, name) {
  if (!collection.has(name)) collection.set(name, newCounts());
  return collection.get(name);
}

function incrementNameCount(collection, name) {
  collection.set(name, (collection.get(name) ?? 0) + 1);
}

function sortedCounts(collection) {
  return Object.fromEntries([...collection.entries()].sort(([a], [b]) => a.localeCompare(b)));
}

function candidateChannels(replay) {
  if (!replay || !replay.baseline_channel_flags
      || typeof replay.candidate_ewma_flag !== 'boolean'
      || typeof replay.candidate_flag !== 'boolean') reject('invalid_candidate_replay');
  const channels = Object.entries(replay.baseline_channel_flags)
    .filter(([name, flagged]) => name !== 'ewma' && flagged === true)
    .map(([name]) => name);
  if (replay.candidate_ewma_flag) channels.push('ewma');
  if ((channels.length > 0) !== replay.candidate_flag) reject('candidate_channel_mismatch');
  return channels;
}

/**
 * Replays one already-used synthetic seed for *descriptive* FP attribution.
 * No tuning, new held-out evaluation, raw values, external IO, or production use.
 */
export function exploreAi9FpSlices(seed = 20270201) {
  const selectedSeed = checkedSeed(seed);
  const dataset = generateAi9MultimetricServicesV1(selectedSeed);
  if (dataset.classification !== 'synthetic_development_only'
      || dataset.services.length !== 56 || dataset.baseline_points !== 30) {
    reject('synthetic_dataset_contract_changed');
  }
  const layer = createPostDetectorConfirmationLayer();
  const total = newCounts();
  const group = new Map();
  const metric = new Map();
  const currentWindowChannels = new Map();
  const confirmationReasons = new Map();

  for (const service of dataset.services) {
    if (typeof service.group !== 'string' || service.group.length === 0
        || service.metrics.length !== 3) reject('invalid_synthetic_service');
    const metricLength = service.metrics[0].events.length;
    if (service.metrics.some(item => item.events.length !== metricLength
        || item.labels.length !== metricLength)) reject('synthetic_cadence_mismatch');

    for (let index = dataset.baseline_points; index < metricLength; index++) {
      const inputMetrics = service.metrics.map(item => ({
        metric: item.metric,
        channels: candidateChannels(evaluateAi9SyntheticWindowV2(item, index)),
      }));
      const occurredAt = service.metrics[0].events[index].occurred_at;
      const window = layer.processServiceWindow({
        serviceId: service.id,
        occurredAt,
        metrics: inputMetrics,
      });
      if (!Array.isArray(window.metrics) || window.metrics.length !== service.metrics.length) {
        reject('confirmation_metric_count_mismatch');
      }

      for (let m = 0; m < service.metrics.length; m++) {
        const input = service.metrics[m];
        const output = window.metrics[m];
        const label = input.labels[index];
        const predicted = output?.confirmed;
        if (typeof label !== 'boolean' || typeof predicted !== 'boolean'
            || output.metric !== input.metric || !Array.isArray(output.confirmation_reasons)) {
          reject('invalid_synthetic_prediction');
        }
        incrementCounts(total, label, predicted);
        incrementCounts(groupSlot(group, service.group), label, predicted);
        incrementCounts(groupSlot(metric, input.metric), label, predicted);
        if (!label && predicted) {
          // Counts can overlap and are only *current-window associations*, not causal attribution.
          for (const channel of inputMetrics[m].channels) incrementNameCount(currentWindowChannels, channel);
          for (const reason of output.confirmation_reasons) incrementNameCount(confirmationReasons, reason);
        }
      }
    }
  }

  if (total.tp + total.fn !== 90 || total.fp + total.tn !== 45150
      || Object.values(sortedCounts(group)).reduce((sum, item) => sum + item.fp, 0) !== total.fp
      || Object.values(sortedCounts(metric)).reduce((sum, item) => sum + item.fp, 0) !== total.fp) {
    reject('frozen_population_or_slice_mismatch');
  }
  return {
    classification: AI9_FP_SLICE_EXPLORATION_POLICY.classification,
    policy_version: AI9_FP_SLICE_EXPLORATION_POLICY.version,
    reused_seed: selectedSeed,
    input_canonical_sha256: digestAi9MultimetricInputV1(dataset),
    totals: total,
    by_control_or_fault_group: sortedCounts(group),
    by_metric: sortedCounts(metric),
    overlapping_current_window_channels: sortedCounts(currentWindowChannels),
    overlapping_confirmation_reasons: sortedCounts(confirmationReasons),
    interpretation: 'post_hoc_exploration_no_new_holdout_or_causal_claim',
    quality_gate_decision: 'UNCHANGED_AI9_FAIL',
    production_decision: 'NOT_AUTHORIZED',
    p01_decision: 'NO-GO / BLOCKED',
  };
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  // The seed is deliberately fixed to a previously consumed development seed.
  console.log(JSON.stringify(exploreAi9FpSlices()));
}
