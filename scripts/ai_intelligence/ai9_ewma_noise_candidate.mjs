const MIN_BASELINE_POINTS = 6;
const MAX_BASELINE_POINTS = 30;
const FILTER_WIDTH = 3;
const ALLOWED_ALPHA_VALUES = Object.freeze([0.3, 0.5]);

export const AI9_EWMA_NOISE_CANDIDATE_POLICY = Object.freeze({
  version: 'ai9-ewma-noise-candidate-v1',
  classification: 'synthetic_development_only',
  method: 'causal_trailing_median_3_then_existing_ewma_rule',
  baseline_points: 30,
  alpha: 0.3,
  synthetic_assumptions: Object.freeze({
    before_seconds: 0,
    after_seconds: 120,
    quiet_windows_to_close: 2,
  }),
});

export class Ai9NoiseCandidateError extends Error {
  constructor(code) {
    super(code);
    this.name = 'Ai9NoiseCandidateError';
    this.code = code;
  }
}

function reject(code) {
  throw new Ai9NoiseCandidateError(code);
}

function assertFiniteSeries(values) {
  if (!Array.isArray(values) || values.some(value => !Number.isFinite(value))) {
    reject('invalid_series');
  }
}

function median(values) {
  const ordered = [...values].sort((left, right) => left - right);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2;
}

function meanAndSampleDeviation(values) {
  let mean = 0;
  let sumSquaredDifferences = 0;
  values.forEach((value, index) => {
    const difference = value - mean;
    mean += difference / (index + 1);
    sumSquaredDifferences += difference * (value - mean);
  });
  const variance = sumSquaredDifferences / (values.length - 1);
  const deviation = Math.sqrt(Math.max(0, variance));
  if (!Number.isFinite(mean) || !Number.isFinite(deviation)) reject('numeric_range');
  return { mean, deviation };
}

function calculateEwma(values, alpha) {
  let value = values[0];
  for (const next of values.slice(1)) value = alpha * next + (1 - alpha) * value;
  if (!Number.isFinite(value)) reject('numeric_range');
  return value;
}

function round(value) {
  if (!Number.isFinite(value)) reject('numeric_range');
  return Number(value.toPrecision(8));
}

/** Causal width-three median filter. No future observation is used. */
export function filterTrailingMedian(values) {
  assertFiniteSeries(values);
  if (values.length === 0) reject('invalid_series');

  return values.map((_, index) => median(values.slice(Math.max(0, index - FILTER_WIDTH + 1), index + 1)));
}

/**
 * Scores one synthetic development metric series with an isolated EWMA noise
 * candidate. This function does not compute AI-9 gates, episodes, or RCA.
 */
export function scoreEwmaNoiseCandidate(values, options = {}) {
  assertFiniteSeries(values);
  const alpha = options.alpha ?? AI9_EWMA_NOISE_CANDIDATE_POLICY.alpha;
  const baselinePoints = options.baselinePoints ?? AI9_EWMA_NOISE_CANDIDATE_POLICY.baseline_points;
  const unit = options.unit ?? 'percent';

  if (!ALLOWED_ALPHA_VALUES.includes(alpha)) reject('unsupported_alpha');
  if (!Number.isInteger(baselinePoints)
    || baselinePoints < MIN_BASELINE_POINTS
    || baselinePoints > MAX_BASELINE_POINTS) reject('invalid_baseline_points');
  if (values.length < baselinePoints + 1) reject('insufficient_history');
  if (typeof unit !== 'string' || unit.length === 0) reject('invalid_unit');

  const filtered = filterTrailingMedian(values);
  const window = filtered.slice(-baselinePoints - 1);
  const baseline = window.slice(0, -1);
  const current = window.at(-1);
  const { deviation } = meanAndSampleDeviation(baseline);
  const ewma = calculateEwma(baseline, alpha);
  const minimumChange = unit === 'percent' ? 0.5 : 1e-6;
  const ewmaVarianceFactor = (alpha / (2 - alpha))
    * (1 - ((1 - alpha) ** (2 * baseline.length)));
  const threshold = Math.max(3 * deviation * Math.sqrt(ewmaVarianceFactor), minimumChange);
  const delta = current - ewma;

  return {
    policy_version: AI9_EWMA_NOISE_CANDIDATE_POLICY.version,
    classification: AI9_EWMA_NOISE_CANDIDATE_POLICY.classification,
    synthetic_assumptions: { ...AI9_EWMA_NOISE_CANDIDATE_POLICY.synthetic_assumptions },
    method: AI9_EWMA_NOISE_CANDIDATE_POLICY.method,
    alpha,
    baseline_points: baseline.length,
    filter_width: FILTER_WIDTH,
    filtered_latest: round(current),
    baseline: round(ewma),
    delta: round(delta),
    threshold: round(threshold),
    flagged: Math.abs(delta) >= threshold,
  };
}
