import { parseStoredEvent } from './event_schema.mjs';

export const MIN_FORECAST_DAYS = 6;
export const MAX_FORECAST_DAYS = 30;
export const SES_ALPHA = 0.3;

const MAX_FORECAST_EVENTS = 100_000;
const DAY_MS = 86_400_000;
const METRIC_DOMAINS = {
  cpu_percent: { min: 0, max: 100 },
  memory_percent: { min: 0, max: 100 },
  disk_percent: { min: 0, max: 100 },
  error_rate: { min: 0, max: 100 },
  request_rate: { min: 0, max: null },
  latency_ms: { min: 0, max: null },
  uptime_seconds: { min: 0, max: null },
};

export class TrendAnalysisError extends Error {
  constructor(code) {
    super(code);
    this.name = 'TrendAnalysisError';
    this.code = code;
  }
}

function reject(code) {
  throw new TrendAnalysisError(code);
}

function round(value) {
  if (!Number.isFinite(value)) reject('numeric_range');
  return Number(value.toPrecision(8));
}

function validateEvents(records) {
  if (!Array.isArray(records) || records.length > MAX_FORECAST_EVENTS) reject('invalid_event_batch');
  try {
    return records.map(record => parseStoredEvent(record));
  } catch {
    reject('invalid_event');
  }
}

function dailyMetricPoints(events) {
  const metrics = new Map();
  for (const event of events) {
    if (event.kind !== 'server_metric') continue;
    const { name, unit, value } = event.data;
    const key = `${name}\u0000${unit}`;
    if (!metrics.has(key)) metrics.set(key, { name, unit, days: new Map() });
    const series = metrics.get(key);
    const day = event.occurred_at.slice(0, 10);
    const current = series.days.get(day) ?? { mean: 0, count: 0 };
    current.count++;
    current.mean += (value - current.mean) / current.count;
    series.days.set(day, current);
  }
  return [...metrics.values()].map(series => ({
    metric: series.name,
    unit: series.unit,
    points: [...series.days.entries()]
      .map(([day, aggregate]) => ({ day, value: aggregate.mean }))
      .sort((left, right) => left.day.localeCompare(right.day)),
  })).sort((left, right) => left.metric.localeCompare(right.metric));
}

function latestConsecutiveTail(points) {
  let start = points.length - 1;
  while (start > 0) {
    const previous = Date.parse(`${points[start - 1].day}T00:00:00Z`);
    const current = Date.parse(`${points[start].day}T00:00:00Z`);
    if (current - previous !== DAY_MS) break;
    start--;
  }
  return points.slice(start).slice(-MAX_FORECAST_DAYS);
}

function linearRegressionNext(values) {
  const scale = Math.max(1, ...values.map(value => Math.abs(value)));
  const normalized = values.map(value => value / scale);
  const meanY = normalized.reduce((sum, value) => sum + value / normalized.length, 0);
  const meanX = (normalized.length - 1) / 2;
  let covariance = 0;
  let variance = 0;
  normalized.forEach((value, index) => {
    const xDelta = index - meanX;
    covariance += xDelta * (value - meanY);
    variance += xDelta * xDelta;
  });
  const slope = covariance / variance;
  const next = (meanY + slope * (normalized.length - meanX)) * scale;
  if (!Number.isFinite(slope) || !Number.isFinite(next)) reject('numeric_range');
  return { dailySlope: slope * scale, next };
}

function simpleExponentialSmoothingNext(values) {
  let level = values[0];
  for (const value of values.slice(1)) level = SES_ALPHA * value + (1 - SES_ALPHA) * level;
  if (!Number.isFinite(level)) reject('numeric_range');
  return level;
}

export function forecastMetricEvents(records) {
  const events = validateEvents(records);
  return dailyMetricPoints(events).map(series => {
    const tail = latestConsecutiveTail(series.points);
    const base = {
      metric: series.metric,
      unit: series.unit,
      daily_observations: series.points.length,
      consecutive_observations: tail.length,
      minimum_consecutive_observations: MIN_FORECAST_DAYS,
      horizon_days: 1,
      latest_observation: series.points.at(-1),
    };
    if (tail.length < MIN_FORECAST_DAYS) {
      return { ...base, status: 'insufficient_history' };
    }

    const values = tail.map(point => point.value);
    const regression = linearRegressionNext(values);
    const exponential = simpleExponentialSmoothingNext(values);
    const domain = METRIC_DOMAINS[series.metric];
    const outOfDomain = [regression.next, exponential].some(value => value < domain.min
      || (domain.max !== null && value > domain.max));
    return {
      ...base,
      status: outOfDomain ? 'range_warning' : 'forecast_candidate',
      model_window_start_utc: tail[0].day,
      model_window_end_utc: tail.at(-1).day,
      linear_regression: {
        next_day_candidate: round(regression.next),
        slope_per_day: round(regression.dailySlope),
      },
      simple_exponential_smoothing: {
        alpha: SES_ALPHA,
        next_day_candidate: round(exponential),
      },
      range_warning: outOfDomain,
    };
  });
}
