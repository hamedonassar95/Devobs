import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {
  digestAi9SyntheticInputV2,
  generateAi9SyntheticScenariosV2,
  scoreAi9Confusion,
  summarizeAi9SyntheticEpisodes,
  AI9_SYNTHETIC_EVALUATION_V2_POLICY,
  evaluateAi9SyntheticWindowV2,
} from './ai9_synthetic_evaluation_v2.mjs';
import { AI9_SYNTHETIC_MULTI_SEED_V1_POLICY, summarizeSeedMetric } from './ai9_synthetic_multiseed_v1.mjs';

export const AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY = Object.freeze({
  version: 'ai9-zma-2of3-alert-grouping-v1',
  classification: 'synthetic_development_only',
  z_score_confirmation: 'at_least_2_of_current_and_previous_2_scored_windows',
  moving_average_confirmation: 'at_least_2_of_current_and_previous_2_scored_windows',
  ewma_policy: 'ai9-ewma-noise-candidate-v1',
  error_rate_spike: 'unchanged_production_channel',
  alert_merge_gap_seconds: 120,
  quiet_windows_to_close: 2,
});

const SCORED_FIRST_SAMPLE = AI9_SYNTHETIC_EVALUATION_V2_POLICY.baseline_points;
const PRIOR_RESULT_PATH = fileURLToPath(new URL('../../docs/AI9_SYNTHETIC_MULTI_SEED_V1_RESULTS.json', import.meta.url));

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

/** Two-of-three confirmation over only the scored flags already observed. */
export function confirmTwoOfThreeScoredFlags(flags) {
  if (!Array.isArray(flags) || flags.length === 0 || flags.length > 3
    || flags.some(flag => typeof flag !== 'boolean')) reject('invalid_confirmation_flags');
  return flags.filter(Boolean).length >= 2;
}

function groupedEpisodeSummary(flags, scenario) {
  const fault = scenario.group === 'injected_fault' ? {
    start_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample,
    last_match_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample
      + (AI9_SYNTHETIC_EVALUATION_V2_POLICY.after_seconds
        / AI9_SYNTHETIC_EVALUATION_V2_POLICY.cadence_seconds),
  } : null;
  return summarizeAi9SyntheticEpisodes(flags, fault);
}

function collectSeedVersions(scenarios, seed) {
  const labels = [];
  const predictions = { baseline: [], candidate_v1: [], candidate_v2: [] };
  const episodeSummaries = { baseline: [], candidate_v1: [], candidate_v2: [] };
  for (const scenario of scenarios) {
    const scenarioFlags = { baseline: [], candidate_v1: [], candidate_v2: [] };
    const channelHistory = { z_score: [], moving_average: [] };
    for (let index = SCORED_FIRST_SAMPLE; index < scenario.events.length; index++) {
      const replay = evaluateAi9SyntheticWindowV2(scenario, index);
      const channels = replay.baseline_channel_flags;
      channelHistory.z_score.push(channels.z_score);
      channelHistory.moving_average.push(channels.moving_average);
      const zConfirmed = confirmTwoOfThreeScoredFlags(channelHistory.z_score.slice(-3));
      const movingConfirmed = confirmTwoOfThreeScoredFlags(channelHistory.moving_average.slice(-3));
      const nextCandidateFlag = zConfirmed || movingConfirmed || replay.candidate_ewma_flag
        || channels.error_rate_spike;
      const label = scenario.labels[index];
      labels.push(label);
      scenarioFlags.baseline.push(replay.baseline_flag);
      scenarioFlags.candidate_v1.push(replay.candidate_flag);
      scenarioFlags.candidate_v2.push(nextCandidateFlag);
    }
    for (const version of Object.keys(predictions)) {
      predictions[version].push(...scenarioFlags[version]);
      episodeSummaries[version].push(groupedEpisodeSummary(scenarioFlags[version], scenario));
    }
  }
  return Object.fromEntries(Object.keys(predictions).map(version => {
    const perScenario = episodeSummaries[version];
    return [version, {
      window_metrics: scoreAi9Confusion(labels, predictions[version]),
      episode_summary: {
        predicted_episodes: perScenario.reduce((sum, item) => sum + item.predicted_episodes, 0),
        closed_episodes: perScenario.reduce((sum, item) => sum + item.closed_episodes, 0),
        open_episodes_at_end: perScenario.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
        fault_scenarios_detected_in_match_window: perScenario
          .filter(item => item.first_alarm_match_sample !== null).length,
      },
      seed,
    }];
  }));
}

function summarizeVersion(seedResults, version) {
  const metrics = seedResults.map(seed => seed[version].window_metrics);
  const episodes = seedResults.map(seed => seed[version].episode_summary);
  return {
    precision: summarizeSeedMetric(metrics.map(item => item.precision)),
    fpr: summarizeSeedMetric(metrics.map(item => item.fpr)),
    per_seed_gate_pass_counts: {
      precision: metrics.filter(item => item.gate_status.precision === 'PASS').length,
      recall: metrics.filter(item => item.gate_status.recall === 'PASS').length,
      fpr: metrics.filter(item => item.gate_status.fpr === 'PASS').length,
      all_three: metrics.filter(item => Object.values(item.gate_status).every(status => status === 'PASS')).length,
      total_seeds: metrics.length,
    },
    descriptive_episode_totals: {
      predicted_episodes: episodes.reduce((sum, item) => sum + item.predicted_episodes, 0),
      closed_episodes: episodes.reduce((sum, item) => sum + item.closed_episodes, 0),
      open_episodes_at_end: episodes.reduce((sum, item) => sum + item.open_episodes_at_end, 0),
      seeds_with_open_episodes: episodes.filter(item => item.open_episodes_at_end > 0).length,
      fault_scenarios_detected_in_match_window: episodes
        .reduce((sum, item) => sum + item.fault_scenarios_detected_in_match_window, 0),
    },
  };
}

function comparableCounts(version) {
  const metrics = version.window_metrics;
  return { tp: metrics.tp, fp: metrics.fp, fn: metrics.fn, tn: metrics.tn };
}

function matchesFrozenResult(actual, expected) {
  const counts = comparableCounts(actual);
  return ['tp', 'fp', 'fn', 'tn'].every(key => counts[key] === expected[key]);
}

export function runAi9ZmaGroupingCandidateV1() {
  const previous = JSON.parse(readFileSync(PRIOR_RESULT_PATH, 'utf8'));
  if (previous.seed_count !== AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds.length
    || previous.per_seed.length !== AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds.length) reject('frozen_result_count_mismatch');
  const priorBySeed = new Map(previous.per_seed.map(item => [item.seed, item]));
  const seedResults = [];
  for (const seed of AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds) {
    const dataset = generateAi9SyntheticScenariosV2(seed);
    const inputDigest = digestAi9SyntheticInputV2(dataset);
    const expected = priorBySeed.get(seed);
    if (!expected || inputDigest !== expected.input_canonical_sha256) reject('frozen_input_mismatch');
    const scoredWindows = dataset.scenarios.reduce((sum, scenario) => sum + scenario.events.length - SCORED_FIRST_SAMPLE, 0);
    if (scoredWindows !== 15_080) reject('frozen_window_count_mismatch');
    const versions = collectSeedVersions(dataset.scenarios, seed);
    const baseline = versions.baseline;
    const currentCandidate = versions.candidate_v1;
    const nextCandidate = versions.candidate_v2;
    if (!matchesFrozenResult(baseline, expected.baseline)
      || !matchesFrozenResult(currentCandidate, expected.candidate)) reject('frozen_detector_reconciliation_mismatch');
    seedResults.push({
      seed,
      input_canonical_sha256: inputDigest,
      scored_windows: scoredWindows,
      baseline,
      candidate_v1: currentCandidate,
      candidate_v2: nextCandidate,
    });
  }
  const outputSeeds = seedResults.map(item => item.seed);
  if (JSON.stringify(outputSeeds) !== JSON.stringify(AI9_SYNTHETIC_MULTI_SEED_V1_POLICY.seeds)) {
    reject('registered_seed_order_mismatch');
  }
  return {
    classification: 'synthetic_development_only_reused_seeds',
    registration_id: AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY.version,
    candidate_policy_version: AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY.version,
    reference_candidate_policy_version: 'ai9-ewma-noise-candidate-v1',
    evaluation_policy_version: 'ai9-synthetic-window-evaluation-v2',
    seed_count: seedResults.length,
    seeds: outputSeeds,
    reused_seed_notice: 'All seeds were previously used for baseline/v1 evaluation. This is a paired development comparison, not independent validation.',
    assumptions: { before_seconds: 0, after_seconds: 120, quiet_windows_to_close: 2 },
    frozen_gates: { precision: 0.8, recall: 0.8, fpr: 0.05 },
    candidate_definition: AI9_ZMA_GROUPING_CANDIDATE_V1_POLICY,
    baseline_summary: summarizeVersion(seedResults, 'baseline'),
    current_candidate_summary: summarizeVersion(seedResults, 'candidate_v1'),
    new_candidate_summary: summarizeVersion(seedResults, 'candidate_v2'),
    per_seed: seedResults.map(item => ({
      seed: item.seed,
      input_canonical_sha256: item.input_canonical_sha256,
      scored_windows: item.scored_windows,
      baseline: item.baseline.window_metrics,
      current_candidate: item.candidate_v1.window_metrics,
      new_candidate: item.candidate_v2.window_metrics,
      baseline_episodes: item.baseline.episode_summary,
      current_candidate_episodes: item.candidate_v1.episode_summary,
      new_candidate_episodes: item.candidate_v2.episode_summary,
    })),
    aggregate_gate_decision: 'NOT_DEFINED_BY_PREREGISTRATION',
    interpretation: 'The registered gates apply per seed at the window level. Grouping is descriptive only. The reused seeds do not establish independent generalization; AI-9 remains FAIL and P01 remains NO-GO / BLOCKED.',
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.stdout.write(`${JSON.stringify(runAi9ZmaGroupingCandidateV1())}\n`);
}
