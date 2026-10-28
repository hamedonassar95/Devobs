import { parseStoredEvent } from './event_schema.mjs';

export const MIN_HISTORY_POINTS = 6;
export const MAX_ANALYSIS_EVENTS = 100_000;
export const MAX_BASELINE_POINTS = 30;

const Z_SCORE_THRESHOLD = 3;
const EWMA_ALPHA = 0.3;
const MOVING_DEVIATION_RATIO = 0.3;
const ERROR_RATE_MIN_SPIKE_POINTS = 1;

export class AnomalyAnalysisError extends Error {
  constructor(code) {
    super(code);
    this.name = 'AnomalyAnalysisError';
    this.code = code;
  }
}

function reject(code) {
  throw new AnomalyAnalysisError(code);
}

function round(value) {
  if (!Number.isFinite(value)) reject('numeric_range');
  return Number(value.toPrecision(8));
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

function calculateEwma(values) {
  let value = values[0];
  for (const next of values.slice(1)) value = EWMA_ALPHA * next + (1 - EWMA_ALPHA) * value;
  if (!Number.isFinite(value)) reject('numeric_range');
  return value;
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function analyzeSeries(points) {
  const ordered = [...points].sort((left, right) => compareText(left.occurred_at, right.occurred_at)
    || compareText(left.event_id, right.event_id));
  const latest = ordered.at(-1);
  if (ordered.length < MIN_HISTORY_POINTS) {
    return {
      metric: latest.data.name,
      unit: latest.data.unit,
      status: 'insufficient_data',
      observations: ordered.length,
      minimum_observations: MIN_HISTORY_POINTS,
      latest: { occurred_at: latest.occurred_at, value: latest.data.value },
      signals: [],
    };
  }

  const baselinePoints = ordered.slice(-MAX_BASELINE_POINTS - 1, -1);
  const values = baselinePoints.map(point => point.data.value);
  const current = latest.data.value;
  const { mean, deviation } = meanAndSampleDeviation(values);
  const delta = current - mean;
  const zScore = deviation > 0 ? delta / deviation : null;
  const minimumChange = latest.data.unit === 'percent' ? 0.5 : 1e-6;
  const movingThreshold = Math.max(Math.abs(mean) * MOVING_DEVIATION_RATIO, minimumChange);
  const ewma = calculateEwma(values);
  const ewmaVarianceFactor = (EWMA_ALPHA / (2 - EWMA_ALPHA))
    * (1 - ((1 - EWMA_ALPHA) ** (2 * values.length)));
  const ewmaThreshold = Math.max(3 * deviation * Math.sqrt(ewmaVarianceFactor), minimumChange);
  const errorRateThreshold = Math.max(3 * deviation, ERROR_RATE_MIN_SPIKE_POINTS);
  const checks = {
    z_score: {
      value: zScore === null ? null : round(zScore),
      threshold: Z_SCORE_THRESHOLD,
      flagged: zScore !== null && Math.abs(zScore) >= Z_SCORE_THRESHOLD,
    },
    moving_average: {
      baseline: round(mean),
      delta: round(delta),
      threshold: round(movingThreshold),
      flagged: Math.abs(delta) >= movingThreshold,
    },
    ewma: {
      alpha: EWMA_ALPHA,
      baseline: round(ewma),
      delta: round(current - ewma),
      threshold: round(ewmaThreshold),
      flagged: Math.abs(current - ewma) >= ewmaThreshold,
    },
    error_rate_spike: {
      applicable: latest.data.name === 'error_rate',
      baseline: round(mean),
      minimum_increase: ERROR_RATE_MIN_SPIKE_POINTS,
      threshold: round(errorRateThreshold),
      flagged: latest.data.name === 'error_rate' && delta > errorRateThreshold,
    },
  };
  const signals = Object.entries(checks).filter(([, result]) => result.flagged).map(([name]) => name);
  return {
    metric: latest.data.name,
    unit: latest.data.unit,
    status: signals.length ? 'anomaly_candidate' : 'no_signal',
    observations: ordered.length,
    baseline_observations: values.length,
    latest: { occurred_at: latest.occurred_at, value: current },
    detectors: checks,
    signals,
  };
}

export function analyzeMetricEvents(records) {
  if (!Array.isArray(records) || records.length > MAX_ANALYSIS_EVENTS) reject('invalid_event_batch');
  const metrics = new Map();
  for (const record of records) {
    let event;
    try {
      event = parseStoredEvent(record);
    } catch {
      reject('invalid_event');
    }
    if (event.kind !== 'server_metric') continue;
    const key = `${event.data.name}\u0000${event.data.unit}`;
    if (!metrics.has(key)) metrics.set(key, []);
    metrics.get(key).push(event);
  }
  return [...metrics.values()]
    .map(analyzeSeries)
    .sort((left, right) => compareText(left.metric, right.metric));
}
