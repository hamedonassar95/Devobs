import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { generateAi9MultimetricServicesV1, digestAi9MultimetricInputV1 } from './ai9_multimetric_service_generator_v1.mjs';
import { evaluateAi9SyntheticWindowV2, scoreAi9Confusion } from './ai9_synthetic_evaluation_v2.mjs';
import { createPostDetectorConfirmationLayer } from './post_detector_confirmation.mjs';
import { robustShiftDecision, AI9_ROBUST_SHIFT_POLICY } from './ai9_robust_shift_candidate.mjs';

export const AI9_ROBUST_SHIFT_EVAL_POLICY = Object.freeze({
  version: 'ai9-robust-shift-evaluation-v1',
  preregistration: 'docs/AI9_ROBUST_SHIFT_V1_PREREGISTRATION.md',
  classification: 'synthetic_development_only',
  preregistered_seeds: Object.freeze([20270401, 20270402, 20270403, 20270404]),
  frozen_window_gates: Object.freeze({ precision: 0.8, recall: 0.8, fpr: 0.05 }),
});

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function candidateChannels(replay) {
  const channels = Object.entries(replay.baseline_channel_flags)
    .filter(([name, flagged]) => name !== 'ewma' && flagged)
    .map(([name]) => name);
  if (replay.candidate_ewma_flag) channels.push('ewma');
  if ((channels.length !== 0) !== replay.candidate_flag) reject('candidate_channel_reconciliation_mismatch');
  return channels;
}

function score(seed) {
  if (seed !== 20270201 && !AI9_ROBUST_SHIFT_EVAL_POLICY.preregistered_seeds.includes(seed)) {
    reject('seed_not_in_registered_or_replay_set');
  }
  const data = generateAi9MultimetricServicesV1(seed);
  if (data.classification !== 'synthetic_development_only' || data.services.length !== 56
      || data.baseline_points !== 30) reject('population_contract_mismatch');

  const layer = createPostDetectorConfirmationLayer();
  const labels = [], baseline = [], candidate = [], delays = [];
  let matchedFaultMetrics = 0, missingFaultMetrics = 0;
  for (const service of data.services) {
    if (!Array.isArray(service.metrics) || service.metrics.length !== 3) reject('metric_count_mismatch');
    const length = service.metrics[0].events.length;
    if (service.metrics.some(item => item.values.length !== length
      || item.labels.length !== length || item.events.length !== length)) reject('metric_cadence_mismatch');

    const firstHit = new Array(3).fill(null);
    for (let index = data.baseline_points; index < length; index++) {
      const channels = service.metrics.map(metric => ({
        metric: metric.metric,
        channels: candidateChannels(evaluateAi9SyntheticWindowV2(metric, index)),
      }));
      const at = service.metrics[0].events[index].occurred_at;
      if (service.metrics.some(metric => metric.events[index].occurred_at !== at)) {
        reject('cross_metric_timestamp_mismatch');
      }
      const confirmed = layer.processServiceWindow({ serviceId: service.id, occurredAt: at, metrics: channels });
      if (!Array.isArray(confirmed.metrics) || confirmed.metrics.length !== 3) reject('invalid_confirmation_result');
      for (let metricIndex = 0; metricIndex < 3; metricIndex++) {
        const item = service.metrics[metricIndex];
        if (typeof item.labels[index] !== 'boolean'
            || confirmed.metrics[metricIndex].metric !== item.metric
            || typeof confirmed.metrics[metricIndex].confirmed !== 'boolean') {
          reject('invalid_metric_scoring_contract');
        }
        const previouslyConfirmed = confirmed.metrics[metricIndex].confirmed;
        const next = robustShiftDecision(item, index, previouslyConfirmed).candidate_confirmed;
        labels.push(item.labels[index]);
        baseline.push(previouslyConfirmed);
        candidate.push(next);
        if (service.group === 'injected_fault' && item.labels[index] && next
            && firstHit[metricIndex] === null) firstHit[metricIndex] = index - 150;
      }
    }
    if (service.group === 'injected_fault') {
      for (const hit of firstHit) {
        if (hit === null) missingFaultMetrics++;
        else {
          matchedFaultMetrics++;
          delays.push(hit);
        }
      }
    }
  }
  const base = scoreAi9Confusion(labels, baseline);
  const test = scoreAi9Confusion(labels, candidate);
  if (labels.length !== 45240 || base.tp + base.fn !== 90 || base.fp + base.tn !== 45150
      || test.tp + test.fn !== 90 || test.fp + test.tn !== 45150) {
    reject('scored_population_mismatch');
  }
  return {
    seed,
    canonical_input_sha256: digestAi9MultimetricInputV1(data),
    baseline: base,
    candidate: test,
    candidate_delta: { fp: test.fp - base.fp, fn: test.fn - base.fn },
    candidate_fault_metric_delay: {
      metric_streams_matched: matchedFaultMetrics,
      metric_streams_missing: missingFaultMetrics,
      first_positive_delay_windows: delays,
    },
  };
}

export function replayPreviouslyConsumedSeed() {
  return {
    classification: 'synthetic_development_only',
    interpretation: 'development_replay_previous_seed_not_fresh_evaluation',
    candidate_policy_version: AI9_ROBUST_SHIFT_POLICY.version,
    production_decision: 'NOT_AUTHORIZED',
    p01_decision: 'NO-GO / BLOCKED',
    result: score(20270201),
  };
}

export function runFrozenFreshEvaluation() {
  const replay = score(20270201);
  // Match the already frozen baseline before ever reading new seed data.
  // This reference was published before the present candidate was defined.
  if (replay.canonical_input_sha256 !== '361a77e4ee44de9c10903f2045287dc86ed2b170c5da019f9880f8fe2f4962a0'
      || replay.baseline.tp !== 76 || replay.baseline.fp !== 1126
      || replay.baseline.fn !== 14 || replay.baseline.tn !== 44024) {
    reject('historical_baseline_reference_mismatch');
  }
  const runs = AI9_ROBUST_SHIFT_EVAL_POLICY.preregistered_seeds.map(seed => score(seed));
  const decision = runs.every(run => Object.values(run.candidate.gate_status).every(value => value === 'PASS'))
    ? 'SYNTHETIC_ONLY_ALL_FROZEN_WINDOW_GATES_PASS' : 'SYNTHETIC_WINDOW_GATES_FAIL';
  return {
    classification: AI9_ROBUST_SHIFT_EVAL_POLICY.classification,
    registration_id: AI9_ROBUST_SHIFT_EVAL_POLICY.version,
    candidate_policy_version: AI9_ROBUST_SHIFT_POLICY.version,
    seeds: [...AI9_ROBUST_SHIFT_EVAL_POLICY.preregistered_seeds],
    frozen_gates: AI9_ROBUST_SHIFT_EVAL_POLICY.frozen_window_gates,
    quality_result: decision,
    production_decision: 'NOT_AUTHORIZED',
    p01_decision: 'NO-GO / BLOCKED',
    runs,
  };
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  const arg = process.argv[2];
  if (process.argv.length !== 3 || !['--replay-used', '--fresh-once'].includes(arg)) {
    console.error('usage: node scripts/ai_intelligence/ai9_robust_shift_evaluation_v1.mjs --replay-used|--fresh-once');
    process.exitCode = 2;
  } else {
    try {
      console.log(JSON.stringify(arg === '--replay-used'
        ? replayPreviouslyConsumedSeed() : runFrozenFreshEvaluation()));
    } catch (error) {
      console.error(JSON.stringify({
        evaluation: 'INVALID',
        reason: error.code ?? 'evaluation_error',
        production_decision: 'NOT_AUTHORIZED',
      }));
      process.exitCode = 2;
    }
  }
}
