import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { analyzeMetricEvents } from './anomaly_detector.mjs';
import { scoreEwmaNoiseCandidate } from './ai9_ewma_noise_candidate.mjs';
import { canonicalJson } from './event_schema.mjs';
import {
  AI9_SYNTHETIC_EVALUATION_V2_POLICY,
  generateAi9SyntheticScenariosV2,
  summarizeAi9SyntheticEpisodes,
} from './ai9_synthetic_evaluation_v2.mjs';

const CONSUMED_SEED = 20261105;
const EXPECTED_INPUT_SHA256 = '1e4211cf0e21371cbbbc8fa3849db1fa0c859e44dab5d02e6c63bc5b33d5852b';
const EXPECTED_FP_COUNTS = Object.freeze({ baseline: 1_710, candidate: 794 });
const SCORED_FIRST_SAMPLE = AI9_SYNTHETIC_EVALUATION_V2_POLICY.baseline_points;

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function digestDataset(dataset) {
  const shape = {
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
  return createHash('sha256').update(canonicalJson(shape)).digest('hex');
}

function makeOpenEpisodeDetails(flags, scenario) {
  const episodes = [];
  let active = null;
  let quietCount = 0;
  flags.forEach((flag, offset) => {
    const sampleIndex = SCORED_FIRST_SAMPLE + offset;
    if (flag) {
      if (!active) active = { start_sample: sampleIndex };
      quietCount = 0;
    } else if (active) {
      quietCount++;
      if (quietCount === AI9_SYNTHETIC_EVALUATION_V2_POLICY.quiet_windows_to_close) {
        const endSample = sampleIndex;
        episodes.push({ ...active, end_sample: endSample, closed: true });
        active = null;
        quietCount = 0;
      }
    }
  });
  if (active) {
    const lastSample = scenario.events.length - 1;
    const positiveWindowsInOpenEpisode = scenario.labels
      .slice(active.start_sample, lastSample + 1)
      .filter(Boolean).length;
    episodes.push({
      ...active,
      last_observed_sample: lastSample,
      trailing_observed_quiet_windows: quietCount,
      closed: false,
      overlaps_fault_windows: positiveWindowsInOpenEpisode > 0,
      positive_windows_in_open_episode: positiveWindowsInOpenEpisode,
    });
  }
  return episodes;
}

function groupForFalsePositive(scenario) {
  return scenario.group === 'injected_fault'
    ? `fault_background_${scenario.metric}`
    : scenario.group;
}

export function runAi9SyntheticFpDiagnosticV2() {
  const dataset = generateAi9SyntheticScenariosV2(CONSUMED_SEED);
  const inputSha256 = digestDataset(dataset);
  if (inputSha256 !== EXPECTED_INPUT_SHA256) reject('consumed_input_digest_mismatch');

  const groupCounts = new Map();
  const signalPatterns = new Map();
  const signalPresence = new Map();
  const baselineEpisodes = [];
  const candidateEpisodes = [];
  const candidateFalsePositiveRuns = [];
  let baselinePredictedEpisodes = 0;
  let candidatePredictedEpisodes = 0;
  let baselineMatchedFaults = 0;
  let candidateMatchedFaults = 0;
  let baselineFalsePositives = 0;
  let candidateFalsePositives = 0;
  let candidateFpWithEwma = 0;
  let candidateFpWithoutEwma = 0;
  let candidateFpAdjacent = 0;
  let candidateFpIsolated = 0;

  for (const scenario of dataset.scenarios) {
    const baselineFlags = [];
    const candidateFlags = [];
    const candidateFalsePositiveFlags = [];
    for (let sampleIndex = SCORED_FIRST_SAMPLE; sampleIndex < scenario.events.length; sampleIndex++) {
      const productionWindow = scenario.events.slice(sampleIndex - SCORED_FIRST_SAMPLE, sampleIndex + 1);
      const [analysis] = analyzeMetricEvents(productionWindow);
      const candidateHistory = scenario.values.slice(Math.max(0, sampleIndex - 32), sampleIndex + 1);
      const candidateEwma = scoreEwmaNoiseCandidate(candidateHistory, {
        alpha: 0.3,
        baselinePoints: AI9_SYNTHETIC_EVALUATION_V2_POLICY.baseline_points,
        unit: scenario.unit,
      });
      const candidateChannelFlags = {
        z_score: analysis.detectors.z_score.flagged,
        moving_average: analysis.detectors.moving_average.flagged,
        ewma_candidate: candidateEwma.flagged,
        error_rate_spike: analysis.detectors.error_rate_spike.flagged,
      };
      const baselineFlag = analysis.status === 'anomaly_candidate';
      const candidateFlag = Object.values(candidateChannelFlags).some(Boolean);
      const isPositive = scenario.labels[sampleIndex];
      const isBaselineFp = !isPositive && baselineFlag;
      const isCandidateFp = !isPositive && candidateFlag;
      const falsePositiveGroup = groupForFalsePositive(scenario);
      baselineFlags.push(baselineFlag);
      candidateFlags.push(candidateFlag);
      candidateFalsePositiveFlags.push(isCandidateFp);

      const group = groupCounts.get(falsePositiveGroup) ?? {
        negative_windows: 0,
        baseline_fp: 0,
        candidate_fp: 0,
        candidate_fp_signal_patterns: {},
      };
      if (!isPositive) group.negative_windows++;
      if (isBaselineFp) {
        baselineFalsePositives++;
        group.baseline_fp++;
      }
      if (isCandidateFp) {
        candidateFalsePositives++;
        group.candidate_fp++;
        const channels = Object.entries(candidateChannelFlags)
          .filter(([, flagged]) => flagged)
          .map(([channel]) => channel);
        const signature = channels.join('+');
        signalPatterns.set(signature, (signalPatterns.get(signature) ?? 0) + 1);
        group.candidate_fp_signal_patterns[signature] = (group.candidate_fp_signal_patterns[signature] ?? 0) + 1;
        for (const channel of channels) signalPresence.set(channel, (signalPresence.get(channel) ?? 0) + 1);
        if (candidateChannelFlags.ewma_candidate) candidateFpWithEwma++;
        else candidateFpWithoutEwma++;
      }
      groupCounts.set(falsePositiveGroup, group);
    }

    for (let offset = 0; offset < candidateFalsePositiveFlags.length; offset++) {
      if (!candidateFalsePositiveFlags[offset]) continue;
      if (candidateFalsePositiveFlags[offset - 1] || candidateFalsePositiveFlags[offset + 1]) {
        candidateFpAdjacent++;
      } else {
        candidateFpIsolated++;
      }
    }
    for (let offset = 0; offset < candidateFalsePositiveFlags.length;) {
      if (!candidateFalsePositiveFlags[offset]) {
        offset++;
        continue;
      }
      let end = offset + 1;
      while (end < candidateFalsePositiveFlags.length && candidateFalsePositiveFlags[end]) end++;
      candidateFalsePositiveRuns.push(end - offset);
      offset = end;
    }
    const fault = scenario.group === 'injected_fault' ? {
      start_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample,
      last_match_sample: AI9_SYNTHETIC_EVALUATION_V2_POLICY.fault_start_sample
        + (AI9_SYNTHETIC_EVALUATION_V2_POLICY.after_seconds
          / AI9_SYNTHETIC_EVALUATION_V2_POLICY.cadence_seconds),
    } : null;
    const baselineEpisodeSummary = summarizeAi9SyntheticEpisodes(baselineFlags, fault);
    const candidateEpisodeSummary = summarizeAi9SyntheticEpisodes(candidateFlags, fault);
    baselinePredictedEpisodes += baselineEpisodeSummary.predicted_episodes;
    candidatePredictedEpisodes += candidateEpisodeSummary.predicted_episodes;
    if (baselineEpisodeSummary.first_alarm_match_sample !== null) baselineMatchedFaults++;
    if (candidateEpisodeSummary.first_alarm_match_sample !== null) candidateMatchedFaults++;
    baselineEpisodes.push(...makeOpenEpisodeDetails(baselineFlags, scenario)
      .filter(episode => !episode.closed)
      .map(episode => ({ scenario_id: scenario.id, group: scenario.group, ...episode })));
    candidateEpisodes.push(...makeOpenEpisodeDetails(candidateFlags, scenario)
      .filter(episode => !episode.closed)
      .map(episode => ({ scenario_id: scenario.id, group: scenario.group, ...episode })));
  }

  if (baselineFalsePositives !== EXPECTED_FP_COUNTS.baseline
    || candidateFalsePositives !== EXPECTED_FP_COUNTS.candidate
    || candidateEpisodes.length !== 2 || baselineEpisodes.length !== 10
    || baselinePredictedEpisodes !== 1_052 || candidatePredictedEpisodes !== 519
    || baselineMatchedFaults !== 4 || candidateMatchedFaults !== 5) {
    reject('posthoc_reconciliation_mismatch');
  }

  const runs = { one: 0, two: 0, three_to_four: 0, five_or_more: 0 };
  for (const length of candidateFalsePositiveRuns) {
    if (length === 1) runs.one++;
    else if (length === 2) runs.two++;
    else if (length <= 4) runs.three_to_four++;
    else runs.five_or_more++;
  }
  const groupReport = Object.fromEntries([...groupCounts.entries()].sort(([left], [right]) => left.localeCompare(right))
    .map(([group, counts]) => [group, {
      ...counts,
      candidate_fp_signal_patterns: Object.fromEntries(Object.entries(counts.candidate_fp_signal_patterns)
        .sort(([left], [right]) => left.localeCompare(right))),
      candidate_fpr_percent: Number(((counts.candidate_fp / counts.negative_windows) * 100).toFixed(4)),
    }]));
  const sortedPatterns = Object.fromEntries([...signalPatterns.entries()].sort(([left], [right]) => left.localeCompare(right)));
  const sortedSignalPresence = Object.fromEntries([...signalPresence.entries()].sort(([left], [right]) => left.localeCompare(right)));
  return {
    classification: 'posthoc_synthetic_diagnostic_only',
    analysis_policy_version: 'ai9-synthetic-window-evaluation-v2',
    candidate_policy_version: 'ai9-ewma-noise-candidate-v1',
    consumed_seed: CONSUMED_SEED,
    input_canonical_sha256: inputSha256,
    baseline_fp_reconciliation: baselineFalsePositives,
    candidate_fp_reconciliation: candidateFalsePositives,
    candidate_false_positives_by_series_type: groupReport,
    candidate_false_positive_detector_attribution: {
      channel_presence_counts_overlap: sortedSignalPresence,
      exclusive_signal_combinations_partition_794_windows: sortedPatterns,
      fp_windows_with_ewma_candidate_signal: candidateFpWithEwma,
      fp_windows_without_ewma_candidate_signal: candidateFpWithoutEwma,
      fp_windows_adjacent_to_another_false_positive_window: candidateFpAdjacent,
      isolated_fp_windows: candidateFpIsolated,
      contiguous_fp_run_length_buckets: runs,
    },
    open_episode_impact: {
      baseline_open_at_eof_count: baselineEpisodes.length,
      candidate_open_at_eof_count: candidateEpisodes.length,
      baseline_open_at_eof: baselineEpisodes,
      candidate_open_at_eof: candidateEpisodes,
      implication: 'An open episode lacks two observed quiet windows. Its end and closure are unconfirmed; it remains ineligible and no quiet observations are appended.',
    },
    descriptive_incident_precision: {
      definition: 'matched predicted episodes divided by all predicted episodes; one episode can match at most one of the six injected fault scenarios when its start is in [fault onset, onset+120s]. All other predicted episodes, including open episodes, count as false incident alerts.',
      baseline: {
        matched_episodes: baselineMatchedFaults,
        predicted_episodes: baselinePredictedEpisodes,
        precision_percent: Number(((baselineMatchedFaults / baselinePredictedEpisodes) * 100).toFixed(4)),
        incident_recall_percent: Number(((baselineMatchedFaults / 6) * 100).toFixed(4)),
      },
      candidate: {
        matched_episodes: candidateMatchedFaults,
        predicted_episodes: candidatePredictedEpisodes,
        precision_percent: Number(((candidateMatchedFaults / candidatePredictedEpisodes) * 100).toFixed(4)),
        incident_recall_percent: Number(((candidateMatchedFaults / 6) * 100).toFixed(4)),
      },
      relation_to_window_precision: 'Descriptive alternative unit only; it does not replace or modify the frozen window-precision gate.',
    },
    limitations: [
      'Post-hoc decomposition of the consumed 20261105 development input; it is not an independent performance result and is excluded from the preregistered multi-seed statistics.',
      'Detector flags show which rules emitted each false-positive window; the synthetic factor labels support recipe-level attribution only and do not establish causality in real telemetry.',
      'No raw metric values are emitted. No detector, threshold, assumption, or gate is changed.',
    ],
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.stdout.write(`${JSON.stringify(runAi9SyntheticFpDiagnosticV2())}\n`);
}
