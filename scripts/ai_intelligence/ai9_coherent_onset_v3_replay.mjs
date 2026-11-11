import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { generateAi9MultimetricServicesV1, digestAi9MultimetricInputV1 } from './ai9_multimetric_service_generator_v1.mjs';
import { evaluateAi9SyntheticWindowV2, scoreAi9Confusion } from './ai9_synthetic_evaluation_v2.mjs';
import { createPostDetectorConfirmationLayer } from './post_detector_confirmation.mjs';
import { jointMetricDecision } from './ai9_joint_metric_v2.mjs';
import { coherentOnsetDecision } from './ai9_coherent_onset_v3.mjs';

const FROZEN_REPLAY_SEED = 20270201;
const FROZEN_DIGEST = '361a77e4ee44de9c10903f2045287dc86ed2b170c5da019f9880f8fe2f4962a0';

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function channels(replay) {
  const names = Object.entries(replay.baseline_channel_flags)
    .filter(([name, flagged]) => name !== 'ewma' && flagged)
    .map(([name]) => name);
  if (replay.candidate_ewma_flag) names.push('ewma');
  if (Boolean(names.length) !== replay.candidate_flag) reject('channel_reconciliation_mismatch');
  return names;
}

/** Already-consumed development seed only; NEVER call the independent holdout here. */
export function replayConsumedAi9OnsetV3() {
  const data = generateAi9MultimetricServicesV1(FROZEN_REPLAY_SEED);
  const digest = digestAi9MultimetricInputV1(data);
  if (digest !== FROZEN_DIGEST || data.services.length !== 56 || data.baseline_points !== 30) {
    reject('frozen_replay_mismatch');
  }
  const layer = createPostDetectorConfirmationLayer();
  const labels = [], baseline = [], oldV2 = [], v3 = [];
  const firstHits = [];
  for (const service of data.services) {
    if (service.metrics.length !== 3) reject('invalid_metric_count');
    const positions = [null,null,null];
    const length = service.metrics[0].events.length;
    for (let index = data.baseline_points; index < length; index++) {
      const at = service.metrics[0].events[index].occurred_at;
      const post = layer.processServiceWindow({
        serviceId: service.id,
        occurredAt: at,
        metrics: service.metrics.map(metric => ({
          metric: metric.metric,
          channels: channels(evaluateAi9SyntheticWindowV2(metric, index)),
        })),
      });
      const input = {
        serviceId: service.id,
        occurredAt: at,
        index,
        metrics: service.metrics.map((metric, i) => ({
          metric: metric.metric, stream: metric, confirmed: post.metrics[i].confirmed,
        })),
      };
      const previous = jointMetricDecision(input);
      const proposed = coherentOnsetDecision(input);
      for (let m = 0; m < 3; m++) {
        const metric = service.metrics[m];
        if (post.metrics[m].metric !== metric.metric || proposed.metrics[m].metric !== metric.metric
          || metric.events[index].occurred_at !== at
          || proposed.metrics[m].v2_confirmed !== previous.metrics[m].candidate_confirmed
          || (proposed.metrics[m].candidate_confirmed && !post.metrics[m].confirmed)) {
          reject('replay_identity_or_policy_mismatch');
        }
        const label = metric.labels[index], original = post.metrics[m].confirmed;
        if (typeof label !== 'boolean') reject('invalid_label');
        labels.push(label);
        baseline.push(original);
        oldV2.push(previous.metrics[m].candidate_confirmed);
        v3.push(proposed.metrics[m].candidate_confirmed);
        if (service.group === 'injected_fault' && label
          && proposed.metrics[m].candidate_confirmed && positions[m] === null) positions[m] = index - 150;
      }
    }
    if (service.group === 'injected_fault') firstHits.push(...positions);
  }
  if (labels.length !== 45240 || labels.filter(Boolean).length !== 90) reject('population_mismatch');
  const base = scoreAi9Confusion(labels, baseline);
  const v2 = scoreAi9Confusion(labels, oldV2);
  const candidate = scoreAi9Confusion(labels, v3);
  if ([base.tp,base.fp,base.fn,base.tn].join('/') !== '76/1126/14/44024'
    || [v2.tp,v2.fp,v2.fn,v2.tn].join('/') !== '58/8/32/45142') reject('historical_replay_mismatch');
  return {
    classification: 'synthetic_development_only_reused_seed',
    registration: 'ai9-coherent-onset-v3',
    seed: FROZEN_REPLAY_SEED,
    input_canonical_sha256: digest,
    baseline: base,
    frozen_joint_v2: v2,
    onset_v3: candidate,
    matched_fault_metrics: firstHits.filter(v => v !== null).length,
    missing_fault_metrics: firstHits.filter(v => v === null).length,
    first_positive_delay_windows: firstHits.filter(v => v !== null),
    production_decision: 'NOT_AUTHORIZED',
    ai9_gate: 'FAIL_UNTIL_INDEPENDENT_EVALUATION_AND_OWNER_APPROVAL',
  };
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  if (process.argv.length !== 3 || process.argv[2] !== '--replay-used') {
    process.stderr.write('usage: node scripts/ai_intelligence/ai9_coherent_onset_v3_replay.mjs --replay-used\n');
    process.exitCode = 2;
  } else {
    try {
      process.stdout.write('AI9_ONSET_V3_REPLAY=' + JSON.stringify(replayConsumedAi9OnsetV3()) + '\n');
    } catch (err) {
      process.stderr.write('AI9_ONSET_V3_INVALID=' + String(err.code ?? 'unknown') + '\n');
      process.exitCode = 2;
    }
  }
}
