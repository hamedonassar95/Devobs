/**
 * Offline-only robust shift filter for an already-confirmed candidate.
 * Frozen in docs/AI9_ROBUST_SHIFT_V1_PREREGISTRATION.md before implementation.
 * It reads no labels, sources, tenants, accounts or future measurements.
 */
export const AI9_ROBUST_SHIFT_POLICY = Object.freeze({
  version: 'ai9-robust-shift-confirmation-v1',
  classification: 'synthetic_development_only',
  reference_points: 30,
  recent_points: 3,
  mad_multiplier: 4,
});

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function median(values) {
  const sorted = [...values].sort((left, right) => left - right);
  const center = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[center]
    : (sorted[center - 1] + sorted[center]) / 2;
}

export function robustShiftDecision(metric, index, confirmed) {
  if (typeof confirmed !== 'boolean') reject('invalid_confirmation');
  if (!metric || !Array.isArray(metric.values) || !Array.isArray(metric.events)
      || !Number.isInteger(index) || index < 0
      || index >= metric.values.length || metric.events.length !== metric.values.length) {
    reject('invalid_metric_window');
  }
  const result = (status, robustShift) => Object.freeze({
    policy_version: AI9_ROBUST_SHIFT_POLICY.version,
    classification: AI9_ROBUST_SHIFT_POLICY.classification,
    status,
    robust_shift: robustShift,
    candidate_confirmed: confirmed && robustShift,
  });
  if (index < 32) return result('insufficient_history', false);

  const numbers = metric.values.slice(index - 32, index + 1);
  const events = metric.events.slice(index - 32, index + 1);
  if (numbers.length !== 33 || numbers.some(value => typeof value !== 'number'
      || !Number.isFinite(value))) reject('invalid_metric_window');

  let previousTimestamp = null;
  for (const item of events) {
    const time = typeof item?.occurred_at === 'string'
      ? Date.parse(item.occurred_at) : NaN;
    if (!Number.isFinite(time)) reject('invalid_temporal_order');
    if (previousTimestamp !== null && time - previousTimestamp !== 60_000) {
      reject('invalid_temporal_order');
    }
    previousTimestamp = time;
  }

  const reference = numbers.slice(0, 30);
  const recent = numbers.slice(30);
  const center = median(reference);
  const mad = median(reference.map(value => Math.abs(value - center)));
  const shift = Math.abs(median(recent) - center);
  const robust = shift > 4 * mad;
  if (!Number.isFinite(mad) || !Number.isFinite(shift)) reject('invalid_metric_window');
  return result('scored', robust);
}
