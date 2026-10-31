import { jointMetricDecision } from './ai9_joint_metric_v2.mjs';

export const AI9_COHERENT_ONSET_V3_POLICY = Object.freeze({
  version: 'ai9-coherent-onset-v3',
  classification: 'synthetic_development_only',
  reference_points: 30,
  preceding_normal_points: 2,
  normal_mad_multiple: 4,
  onset_mad_multiple: 12,
  minimum_distinct_onset_metrics: 2,
});

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function metricOnset(stream, index) {
  if (index < 32) return false;
  const numbers = stream.values.slice(index - 32, index + 1);
  const events = stream.events.slice(index - 32, index + 1);
  if (numbers.length !== 33 || events.length !== 33
    || numbers.some(v => typeof v !== 'number' || !Number.isFinite(v))) {
    reject('invalid_onset_window');
  }
  let lastTime = null;
  for (const item of events) {
    const time = typeof item?.occurred_at === 'string' ? Date.parse(item.occurred_at) : NaN;
    if (!Number.isFinite(time) || (lastTime !== null && time - lastTime !== 60_000)) {
      reject('invalid_onset_temporal_order');
    }
    lastTime = time;
  }
  const reference = numbers.slice(0, 30);
  const center = median(reference);
  const mad = median(reference.map(v => Math.abs(v - center)));
  if (!Number.isFinite(mad) || mad <= 0) return false;
  const precedingNormal = numbers.slice(30, 32).every(
    v => Math.abs(v - center) <= AI9_COHERENT_ONSET_V3_POLICY.normal_mad_multiple * mad,
  );
  return precedingNormal
    && Math.abs(numbers[32] - center) > AI9_COHERENT_ONSET_V3_POLICY.onset_mad_multiple * mad;
}

/**
 * A strictly causal, development-only extension of frozen joint v2.
 * It can restore an already-confirmed first-onset alert but cannot create one.
 */
export function coherentOnsetDecision(input) {
  const v2 = jointMetricDecision(input); // reuses v2's fail-closed shape/time checks
  const onsetFlags = input.metrics.map(m => metricOnset(m.stream, input.index));
  const count = onsetFlags.filter(Boolean).length;
  const coherentOnset = count >= AI9_COHERENT_ONSET_V3_POLICY.minimum_distinct_onset_metrics;
  return Object.freeze({
    policy_version: AI9_COHERENT_ONSET_V3_POLICY.version,
    classification: AI9_COHERENT_ONSET_V3_POLICY.classification,
    coherent_service_shift_v2: v2.coherent_service_shift,
    coherent_onset: coherentOnset,
    onset_metric_count: count,
    metrics: v2.metrics.map((item, i) => Object.freeze({
      metric: item.metric,
      existing_confirmed: item.existing_confirmed,
      v2_confirmed: item.candidate_confirmed,
      onset: onsetFlags[i],
      candidate_confirmed: item.existing_confirmed && (v2.coherent_service_shift || coherentOnset),
    })),
  });
}
