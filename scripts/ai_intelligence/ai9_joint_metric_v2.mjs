import { robustShiftDecision } from './ai9_robust_shift_candidate.mjs';

export const AI9_JOINT_METRIC_V2_POLICY = Object.freeze({
  version: 'ai9-joint-metric-confirmation-v2',
  classification: 'synthetic_development_only',
  minimum_distinct_robust_metrics: 2,
});

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

/**
 * Strictly offline, stateless, service-scoped consensus over exactly three
 * synchronous metric streams. The existing confirmation result remains
 * authoritative; consensus can only suppress, never introduce, positives.
 */
export function jointMetricDecision(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)
      || typeof input.serviceId !== 'string'
      || !/^[a-zA-Z0-9_.-]{1,128}$/.test(input.serviceId)
      || typeof input.occurredAt !== 'string'
      || !Number.isFinite(Date.parse(input.occurredAt))
      || !Number.isInteger(input.index) || input.index < 0
      || !Array.isArray(input.metrics) || input.metrics.length !== 3) {
    reject('invalid_joint_metric_window');
  }
  const seen = new Set();
  const decisions = input.metrics.map(item => {
    if (!item || typeof item !== 'object'
        || typeof item.metric !== 'string'
        || !/^[a-zA-Z0-9_]{1,80}$/.test(item.metric)
        || seen.has(item.metric)
        || typeof item.confirmed !== 'boolean'
        || !item.stream || !Array.isArray(item.stream.events)
        || !Array.isArray(item.stream.values)
        || item.index !== undefined
        || item.stream.events[input.index]?.occurred_at !== input.occurredAt) {
      reject('invalid_joint_metric_window');
    }
    seen.add(item.metric);
    // The frozen shift calculation is independent of each metric's current
    // confirmation result. Its 30/3 MAD thresholds remain unchanged.
    const shift = robustShiftDecision(item.stream, input.index, true);
    return {
      metric: item.metric,
      existing_confirmed: item.confirmed,
      robust_shift: shift.robust_shift,
    };
  });
  const strongCount = decisions.filter(item => item.robust_shift).length;
  const coherent = strongCount >= AI9_JOINT_METRIC_V2_POLICY.minimum_distinct_robust_metrics;
  return Object.freeze({
    policy_version: AI9_JOINT_METRIC_V2_POLICY.version,
    classification: AI9_JOINT_METRIC_V2_POLICY.classification,
    coherent_service_shift: coherent,
    robust_metric_count: strongCount,
    metrics: decisions.map(item => ({
      ...item,
      candidate_confirmed: item.existing_confirmed && coherent,
    })),
  });
}
