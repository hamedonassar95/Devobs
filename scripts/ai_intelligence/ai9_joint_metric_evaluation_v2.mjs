import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { generateAi9MultimetricServicesV1, digestAi9MultimetricInputV1 } from './ai9_multimetric_service_generator_v1.mjs';
import { evaluateAi9SyntheticWindowV2, scoreAi9Confusion } from './ai9_synthetic_evaluation_v2.mjs';
import { createPostDetectorConfirmationLayer } from './post_detector_confirmation.mjs';
import { robustShiftDecision } from './ai9_robust_shift_candidate.mjs';
import { jointMetricDecision, AI9_JOINT_METRIC_V2_POLICY } from './ai9_joint_metric_v2.mjs';

export const AI9_JOINT_METRIC_EVALUATION_POLICY = Object.freeze({
  version: 'ai9-joint-metric-evaluation-v2',
  classification: 'synthetic_development_only',
  preregistration: 'docs/AI9_JOINT_METRIC_V2_PREREGISTRATION.md',
  new_seeds: Object.freeze([20270501, 20270502, 20270503, 20270504]),
  gates: Object.freeze({ precision: 0.8, recall: 0.8, fpr: 0.05 }),
});

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function channels(replay) {
  const result = Object.entries(replay.baseline_channel_flags)
    .filter(([name, flagged]) => name !== 'ewma' && flagged)
    .map(([name]) => name);
  if (replay.candidate_ewma_flag) result.push('ewma');
  if (Boolean(result.length) !== replay.candidate_flag) reject('replay_channels_changed');
  return result;
}

function scoreSeed(seed) {
  if (seed !== 20270201 && !AI9_JOINT_METRIC_EVALUATION_POLICY.new_seeds.includes(seed)) reject('unregistered_seed');
  const data = generateAi9MultimetricServicesV1(seed);
  if (data.classification !== 'synthetic_development_only' || data.services.length !== 56
      || data.baseline_points !== 30) reject('dataset_contract_mismatch');

  const layer = createPostDetectorConfirmationLayer();
  const labels = [], confirmedFlags = [], previousFlags = [], jointFlags = [];
  const detections = [];
  let missed = 0;
  for (const service of data.services) {
    if (!Array.isArray(service.metrics) || service.metrics.length !== 3) reject('invalid_service');
    const names = service.metrics.map(x => x.metric);
    if (new Set(names).size !== 3) reject('duplicate_metric_name');
    const length = service.metrics[0].events.length;
    if (service.metrics.some(x => x.values.length !== length || x.labels.length !== length
        || x.events.length !== length)) reject('metric_length_mismatch');
    const firstHits = [null, null, null];
    for (let i = data.baseline_points; i < length; i++) {
      const at = service.metrics[0].events[i].occurred_at;
      const rawChannels = service.metrics.map(metric => ({
        metric: metric.metric,
        channels: channels(evaluateAi9SyntheticWindowV2(metric, i)),
      }));
      const post = layer.processServiceWindow({ serviceId: service.id, occurredAt: at, metrics: rawChannels });
      if (post.metrics.length !== 3) reject('confirmation_shape_mismatch');
      const inputs = service.metrics.map((metric, m) => ({
        metric: metric.metric,
        stream: metric,
        confirmed: post.metrics[m].confirmed,
      }));
      const joint = jointMetricDecision({ serviceId: service.id, occurredAt: at, index: i, metrics: inputs });
      if (joint.metrics.length !== 3) reject('joint_shape_mismatch');
      for (let m = 0; m < 3; m++) {
        const metric = service.metrics[m];
        if (post.metrics[m].metric !== metric.metric || joint.metrics[m].metric !== metric.metric
            || typeof metric.labels[i] !== 'boolean') reject('metric_identity_mismatch');
        const baseline = post.metrics[m].confirmed;
        const previous = robustShiftDecision(metric, i, baseline).candidate_confirmed;
        const proposed = joint.metrics[m].candidate_confirmed;
        if ((previous && !baseline) || (proposed && !baseline)) reject('unapproved_positive_creation');
        labels.push(metric.labels[i]);
        confirmedFlags.push(baseline);
        previousFlags.push(previous);
        jointFlags.push(proposed);
        if (service.group === 'injected_fault' && metric.labels[i] && proposed && firstHits[m] === null) {
          firstHits[m] = i - 150;
        }
      }
    }
    if (service.group === 'injected_fault') {
      for (const hit of firstHits) {
        if (hit === null) missed++;
        else detections.push(hit);
      }
    }
  }
  if (labels.length !== 45240 || labels.filter(Boolean).length !== 90) reject('population_mismatch');
  const baseline = scoreAi9Confusion(labels, confirmedFlags);
  const individual = scoreAi9Confusion(labels, previousFlags);
  const joint = scoreAi9Confusion(labels, jointFlags);
  return {
    seed,
    input_canonical_sha256: digestAi9MultimetricInputV1(data),
    post_confirmation_baseline: baseline,
    robust_shift_v1: individual,
    joint_metric_v2: joint,
    delta_from_baseline: { false_positives: joint.fp - baseline.fp, false_negatives: joint.fn - baseline.fn },
    joint_fault_metric_delay: { matched: detections.length, missing: missed, first_positive_delay_windows: detections },
  };
}

export function replayUsedSeedV2() {
  return {
    interpretation: 'previously_consumed_synthetic_replay_not_independent',
    classification: 'synthetic_development_only',
    production_decision: 'NOT_AUTHORIZED',
    p01_decision: 'NO-GO / BLOCKED',
    result: scoreSeed(20270201),
  };
}

export function evaluateFrozenFreshV2() {
  const prior = scoreSeed(20270201);
  if (prior.input_canonical_sha256 !== '361a77e4ee44de9c10903f2045287dc86ed2b170c5da019f9880f8fe2f4962a0'
      || prior.post_confirmation_baseline.tp !== 76 || prior.post_confirmation_baseline.fp !== 1126
      || prior.post_confirmation_baseline.fn !== 14 || prior.post_confirmation_baseline.tn !== 44024) {
    reject('frozen_historical_baseline_mismatch');
  }
  const seeds = AI9_JOINT_METRIC_EVALUATION_POLICY.new_seeds.map(scoreSeed);
  const passed = seeds.every(run => Object.values(run.joint_metric_v2.gate_status).every(value => value === 'PASS'));
  return {
    classification: 'synthetic_development_only',
    registration_id: AI9_JOINT_METRIC_EVALUATION_POLICY.version,
    policy_version: AI9_JOINT_METRIC_V2_POLICY.version,
    frozen_gates: AI9_JOINT_METRIC_EVALUATION_POLICY.gates,
    seed_set: [...AI9_JOINT_METRIC_EVALUATION_POLICY.new_seeds],
    independent_synthetic_result: passed ? 'ALL_FROZEN_WINDOW_GATES_PASS' : 'FROZEN_WINDOW_GATES_FAIL',
    production_decision: 'NOT_AUTHORIZED',
    p01_decision: 'NO-GO / BLOCKED',
    runs: seeds,
  };
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  if (process.argv.length !== 3 || !['--replay-used', '--fresh-once'].includes(process.argv[2])) {
    console.error('usage: node scripts/ai_intelligence/ai9_joint_metric_evaluation_v2.mjs --replay-used|--fresh-once');
    process.exitCode = 2;
  } else {
    try {
      console.log(JSON.stringify(process.argv[2] === '--replay-used'
        ? replayUsedSeedV2() : evaluateFrozenFreshV2()));
    } catch (error) {
      console.error(JSON.stringify({ evaluation: 'INVALID', error_code: error.code ?? 'unknown', production_decision: 'NOT_AUTHORIZED' }));
      process.exitCode = 2;
    }
  }
}
