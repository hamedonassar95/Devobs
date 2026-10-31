/**
 * Manual-only independent synthetic AI-9 v3 evaluator.
 * Never import or invoke this from CI, unit tests or scheduled automation.
 * Frozen seed set and quality gates: docs/AI9_COHERENT_ONSET_V3_PREREGISTRATION.md
 */
import { existsSync, openSync, writeFileSync, closeSync, writeSync, fsyncSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { generateAi9MultimetricServicesV1, digestAi9MultimetricInputV1 } from './ai9_multimetric_service_generator_v1.mjs';
import { evaluateAi9SyntheticWindowV2, scoreAi9Confusion } from './ai9_synthetic_evaluation_v2.mjs';
import { createPostDetectorConfirmationLayer } from './post_detector_confirmation.mjs';
import { jointMetricDecision } from './ai9_joint_metric_v2.mjs';
import { coherentOnsetDecision } from './ai9_coherent_onset_v3.mjs';
import { replayConsumedAi9OnsetV3 } from './ai9_coherent_onset_v3_replay.mjs';

export const FROZEN_HOLDOUT_CONTRACT = Object.freeze({
  registration: 'ai9-coherent-onset-v3',
  seeds: Object.freeze([20270601, 20270602, 20270603, 20270604]),
  gates: Object.freeze({ precision: 0.80, recall: 0.80, fpr: 0.05 }),
  scored_windows: 45240,
  positives: 90,
  negatives: 45150,
  fault_metric_streams: 18,
});
const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const RESULT = path.join(ROOT, 'docs/AI9_V3_FROZEN_HOLDOUT_RESULTS.json');
const LOCK = path.join(ROOT, 'docs/AI9_V3_FROZEN_HOLDOUT_LOCK.json');

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}
function git(args) {
  return execFileSync('git', args, { cwd: ROOT, encoding: 'utf8', timeout: 30000 }).trim();
}
function frozenGates(metrics) {
  return metrics.precision !== null && metrics.precision >= 0.8
    && metrics.recall !== null && metrics.recall >= 0.8
    && metrics.fpr !== null && metrics.fpr <= 0.05;
}

/** Pure contract checks: hand-authored fixtures, never a reserved seed. */
export function validateSyntheticScore(metrics, expectedWindows = FROZEN_HOLDOUT_CONTRACT.scored_windows) {
  if (!metrics || ![metrics.tp, metrics.fp, metrics.fn, metrics.tn].every(
    value => Number.isSafeInteger(value) && value >= 0,
  ) || metrics.tp + metrics.fp + metrics.fn + metrics.tn !== expectedWindows
    || metrics.tp + metrics.fn !== FROZEN_HOLDOUT_CONTRACT.positives
    || metrics.fp + metrics.tn !== FROZEN_HOLDOUT_CONTRACT.negatives
    || ![metrics.precision, metrics.recall, metrics.fpr].every(
      value => value === null || (typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1),
    )
    || Math.abs(metrics.recall - metrics.tp / FROZEN_HOLDOUT_CONTRACT.positives) > 1e-12
    || Math.abs(metrics.fpr - metrics.fp / FROZEN_HOLDOUT_CONTRACT.negatives) > 1e-12
    || Math.abs(metrics.precision - (metrics.tp + metrics.fp ? metrics.tp / (metrics.tp + metrics.fp) : 0)) > 1e-12
       && !(metrics.precision === null && metrics.tp + metrics.fp === 0)) {
    reject('invalid_scoring_contract');
  }
  return frozenGates(metrics);
}

function channelList(replay) {
  const value = Object.entries(replay.baseline_channel_flags)
    .filter(([channel, flagged]) => channel !== 'ewma' && flagged)
    .map(([channel]) => channel);
  if (replay.candidate_ewma_flag) value.push('ewma');
  if (Boolean(value.length) !== replay.candidate_flag) reject('channel_reconciliation_mismatch');
  return value;
}

function scoreOneSeed(seed) {
  if (!FROZEN_HOLDOUT_CONTRACT.seeds.includes(seed)) reject('unregistered_seed');
  const data = generateAi9MultimetricServicesV1(seed);
  if (data.seed !== seed || data.classification !== 'synthetic_development_only'
    || data.services?.length !== 56 || data.baseline_points !== 30) reject('generator_contract_mismatch');

  const labels = [], confirmed = [], oldJoint = [], candidate = [], firstDelays = [];
  const layer = createPostDetectorConfirmationLayer();
  for (const service of data.services) {
    if (service.metrics?.length !== 3
      || new Set(service.metrics.map(x => x.metric)).size !== 3
      || service.metrics.some(x => !Array.isArray(x.events) || !Array.isArray(x.labels)
        || !Array.isArray(x.values) || x.events.length !== x.labels.length
        || x.values.length !== x.events.length)) reject('invalid_service_population');
    const delays = [null, null, null];
    for (let index = data.baseline_points; index < service.metrics[0].events.length; index++) {
      const at = service.metrics[0].events[index].occurred_at;
      if (service.metrics.some(metric => metric.events[index]?.occurred_at !== at)) {
        reject('metric_time_mismatch');
      }
      const post = layer.processServiceWindow({
        serviceId: service.id, occurredAt: at,
        metrics: service.metrics.map(metric => ({
          metric: metric.metric, channels: channelList(evaluateAi9SyntheticWindowV2(metric, index)),
        })),
      });
      if (post.metrics.length !== 3) reject('confirmation_shape_mismatch');
      const input = {
        serviceId: service.id, occurredAt: at, index,
        metrics: service.metrics.map((metric, m) => ({
          metric: metric.metric, stream: metric, confirmed: post.metrics[m].confirmed,
        })),
      };
      const v2 = jointMetricDecision(input);
      const v3 = coherentOnsetDecision(input);
      for (let m = 0; m < 3; m++) {
        const metric = service.metrics[m], label = metric.labels[index];
        if (typeof label !== 'boolean'
          || post.metrics[m].metric !== metric.metric
          || v3.metrics[m].metric !== metric.metric
          || v3.metrics[m].v2_confirmed !== v2.metrics[m].candidate_confirmed
          || (v3.metrics[m].candidate_confirmed && !post.metrics[m].confirmed)) {
          reject('identity_or_confirmation_mismatch');
        }
        labels.push(label);
        confirmed.push(post.metrics[m].confirmed);
        oldJoint.push(v2.metrics[m].candidate_confirmed);
        candidate.push(v3.metrics[m].candidate_confirmed);
        if (service.group === 'injected_fault' && label
          && v3.metrics[m].candidate_confirmed && delays[m] === null) delays[m] = index - 150;
      }
    }
    if (service.group === 'injected_fault') firstDelays.push(...delays);
  }
  if (labels.length !== FROZEN_HOLDOUT_CONTRACT.scored_windows
    || labels.filter(Boolean).length !== FROZEN_HOLDOUT_CONTRACT.positives
    || firstDelays.length !== FROZEN_HOLDOUT_CONTRACT.fault_metric_streams) reject('scoring_population_mismatch');
  const baseline = scoreAi9Confusion(labels, confirmed);
  const jointV2 = scoreAi9Confusion(labels, oldJoint);
  const onsetV3 = scoreAi9Confusion(labels, candidate);
  for (const metrics of [baseline, jointV2, onsetV3]) validateSyntheticScore(metrics);
  if (onsetV3.tp < jointV2.tp || onsetV3.fp < jointV2.fp || onsetV3.fn > jointV2.fn
    || onsetV3.tp > baseline.tp || onsetV3.fp > baseline.fp) reject('non_suppressive_candidate');
  return {
    seed, input_canonical_sha256: digestAi9MultimetricInputV1(data),
    scored_windows: labels.length, positive_windows: FROZEN_HOLDOUT_CONTRACT.positives,
    negative_windows: FROZEN_HOLDOUT_CONTRACT.negatives,
    post_confirmation_baseline: baseline, frozen_joint_v2: jointV2, candidate_v3: onsetV3,
    first_detection_delay_windows: firstDelays.filter(v => v !== null),
    missing_fault_metric_detections: firstDelays.filter(v => v === null).length,
    window_gate_result: frozenGates(onsetV3) ? 'PASS' : 'FAIL',
  };
}

function preflight(expectedSha) {
  if (!/^[a-f0-9]{40}$/.test(expectedSha)) reject('invalid_approved_sha');
  if (git(['rev-parse', 'HEAD']) !== expectedSha) reject('source_sha_mismatch');
  if (git(['rev-parse', '--abbrev-ref', 'HEAD']) !== 'main') reject('main_branch_required');
  if (git(['rev-parse', '--is-shallow-repository']) !== 'false') reject('full_git_history_required');
  if (git(['status', '--porcelain']).length) reject('dirty_checkout');
  if (existsSync(LOCK) || existsSync(RESULT)) reject('holdout_already_started_or_completed');
  // A hit in the historical structured result artifacts is not silently ignored.
  // Preregistration/documentation mentions are intentionally not treated as scored results.
  const commits = git(['log', '--all', '--format=%H', '-G', '2027060[1-4]', '--',
    ':(glob)docs/**/*RESULTS.json', ':(glob)docs/*RESULTS.json']);
  if (commits.length) reject('historical_result_seed_collision_review_required');
  const previous = replayConsumedAi9OnsetV3(); // old seed only
  if (previous.input_canonical_sha256 !== '361a77e4ee44de9c10903f2045287dc86ed2b170c5da019f9880f8fe2f4962a0'
    || [previous.onset_v3.tp,previous.onset_v3.fp,previous.onset_v3.fn,previous.onset_v3.tn]
      .join('/') !== '73/8/17/45142') reject('historical_replay_changed');
}

function persistNew(pathname, payload) {
  const fd = openSync(pathname, 'wx', 0o600);
  try {
    writeSync(fd, JSON.stringify(payload, null, 2) + '\n');
    fsyncSync(fd);
  } finally { closeSync(fd); }
}

/** Owner-authorized single-run entrypoint; do not call this from another module. */
function runOnce(approvedSha) {
  preflight(approvedSha);
  persistNew(LOCK, {
    status: 'STARTED', approved_sha: approvedSha,
    registration: FROZEN_HOLDOUT_CONTRACT.registration,
    seeds: FROZEN_HOLDOUT_CONTRACT.seeds,
    warning: 'Do not rerun or remove this lock. Preserve INVALID if evaluation fails.',
  });
  try {
    const perSeed = FROZEN_HOLDOUT_CONTRACT.seeds.map(scoreOneSeed);
    const passed = perSeed.every(x => x.window_gate_result === 'PASS');
    const report = {
      classification: 'independent_synthetic_only', registration: FROZEN_HOLDOUT_CONTRACT.registration,
      evaluated_sha: approvedSha, seed_order: FROZEN_HOLDOUT_CONTRACT.seeds,
      frozen_gates: FROZEN_HOLDOUT_CONTRACT.gates,
      result: passed ? 'ALL_FROZEN_WINDOW_GATES_PASS' : 'FROZEN_WINDOW_GATES_FAIL',
      per_seed: perSeed,
      production_decision: 'NOT_AUTHORIZED', ai9_gate: 'BLOCKED',
      p01_decision: 'NO-GO / BLOCKED',
    };
    persistNew(RESULT, report);
    process.stdout.write(JSON.stringify({
      result: report.result, report_file: 'docs/AI9_V3_FROZEN_HOLDOUT_RESULTS.json',
      evaluated_sha: approvedSha, seeds: FROZEN_HOLDOUT_CONTRACT.seeds,
      production_decision: 'NOT_AUTHORIZED',
    }) + '\n');
  } catch (error) {
    persistNew(RESULT, {
      classification: 'independent_synthetic_only', result: 'INVALID',
      error_code: error?.code ?? 'evaluation_error', evaluated_sha: approvedSha,
      production_decision: 'NOT_AUTHORIZED', ai9_gate: 'BLOCKED',
    });
    reject('holdout_invalid_no_automatic_retry');
  }
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  if (process.argv.length !== 5 || process.argv[2] !== '--fresh-once'
    || process.argv[3] !== '--approved-sha') {
    process.stderr.write('ERROR manual only: --fresh-once --approved-sha <full-main-sha>\n');
    process.exitCode = 2;
  } else {
    try { runOnce(process.argv[4]); }
    catch (error) {
      process.stderr.write('INVALID: ' + String(error?.code ?? 'evaluation_error') + '\n');
      process.exitCode = 2;
    }
  }
}
