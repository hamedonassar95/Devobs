import { createHash } from 'node:crypto';
import { canonicalJson, normalizeEvent } from './event_schema.mjs';
import { generateAi9SyntheticScenariosV2 } from './ai9_synthetic_evaluation_v2.mjs';

export const AI9_MULTIMETRIC_SERVICE_GENERATOR_V1_POLICY = Object.freeze({
  version: 'ai9-multimetric-service-generator-v1',
  classification: 'synthetic_development_only',
  control_metric_names: Object.freeze(['cpu_percent', 'latency_ms', 'error_rate']),
  positive_windows_per_fault_metric: 5,
  fault_start_sample: 150,
  metric_configurations: Object.freeze({
    cpu_percent: Object.freeze({ baseline: 34, scale: 1, unit: 'percent' }),
    disk_percent: Object.freeze({ baseline: 34, scale: 1, unit: 'percent' }),
    memory_percent: Object.freeze({ baseline: 34, scale: 1, unit: 'percent' }),
    latency_ms: Object.freeze({ baseline: 100, scale: 2, unit: 'milliseconds' }),
    error_rate: Object.freeze({ baseline: 3, scale: 0.25, unit: 'percent' }),
    request_rate: Object.freeze({ baseline: 34, scale: 1, unit: 'per_second' }),
  }),
});

const FAULT_EFFECTS = Object.freeze({
  fault_latency_step: Object.freeze([
    Object.freeze({ metric: 'latency_ms', delta: 120 }),
    Object.freeze({ metric: 'cpu_percent', delta: 10 }),
    Object.freeze({ metric: 'error_rate', delta: 0.5 }),
  ]),
  fault_cpu_step: Object.freeze([
    Object.freeze({ metric: 'cpu_percent', delta: 18 }),
    Object.freeze({ metric: 'latency_ms', delta: 60 }),
    Object.freeze({ metric: 'error_rate', delta: 0.375 }),
  ]),
  fault_disk_step: Object.freeze([
    Object.freeze({ metric: 'disk_percent', delta: 25 }),
    Object.freeze({ metric: 'latency_ms', delta: 90 }),
    Object.freeze({ metric: 'error_rate', delta: 0.625 }),
  ]),
  fault_error_rate_step: Object.freeze([
    Object.freeze({ metric: 'error_rate', delta: 1 }),
    Object.freeze({ metric: 'latency_ms', delta: 100 }),
    Object.freeze({ metric: 'cpu_percent', delta: 12 }),
  ]),
  fault_request_rate_drop: Object.freeze([
    Object.freeze({ metric: 'request_rate', delta: -18 }),
    Object.freeze({ metric: 'latency_ms', delta: 80 }),
    Object.freeze({ metric: 'error_rate', delta: 0.5 }),
  ]),
  fault_memory_step: Object.freeze([
    Object.freeze({ metric: 'memory_percent', delta: 15 }),
    Object.freeze({ metric: 'latency_ms', delta: 70 }),
    Object.freeze({ metric: 'cpu_percent', delta: 12 }),
  ]),
});
const WINDOW_SECONDS = 60;

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6D2B79F5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4_294_967_296;
  };
}

function metricSeed(seed, serviceIndex, metricIndex) {
  return (seed
    ^ Math.imul(serviceIndex + 1, 0x9E3779B1)
    ^ Math.imul(metricIndex + 1, 0x85EBCA6B)) >>> 0;
}

function controlFactors(group) {
  return {
    seasonality: group.includes('seasonality') ? 7 : 0,
    noise: group.includes('noise') ? 0.7 : 0,
    drift: group.includes('drift') ? 10 : 0,
  };
}

function normalizedValue(value, metricConfig) {
  const bounded = metricConfig.unit === 'percent'
    ? Math.min(100, Math.max(0, value))
    : Math.max(0, value);
  return Number(bounded.toFixed(4));
}

function makeEvent(value, metric, metricConfig, occurredAt) {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: occurredAt,
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: {
      name: metric,
      value: normalizedValue(value, metricConfig),
      unit: metricConfig.unit,
    },
  });
}

function makeMetricStream({ descriptor, serviceIndex, metricIndex, metricEffect, seed }) {
  const metric = metricEffect.metric;
  const config = AI9_MULTIMETRIC_SERVICE_GENERATOR_V1_POLICY.metric_configurations[metric];
  if (!config) reject('unsupported_synthetic_metric');
  const random = mulberry32(metricSeed(seed, serviceIndex, metricIndex));
  const factors = descriptor.group === 'injected_fault'
    ? { seasonality: 0, drift: 0, noise: 0.7 }
    : controlFactors(descriptor.group);
  const length = descriptor.events.length;
  const labels = [];
  const values = [];
  const events = [];

  for (let index = 0; index < length; index++) {
    const dailyPhase = (2 * Math.PI * (index % 1_440)) / 1_440;
    const seasonal = factors.seasonality * config.scale * Math.sin(dailyPhase - Math.PI / 3);
    const drift = factors.drift * config.scale * (index / (length - 1));
    const noise = ((random() * 2 - 1) * factors.noise * config.scale);
    const inFault = descriptor.group === 'injected_fault'
      && index >= AI9_MULTIMETRIC_SERVICE_GENERATOR_V1_POLICY.fault_start_sample
      && index < AI9_MULTIMETRIC_SERVICE_GENERATOR_V1_POLICY.fault_start_sample
        + AI9_MULTIMETRIC_SERVICE_GENERATOR_V1_POLICY.positive_windows_per_fault_metric;
    const rawValue = config.baseline + seasonal + drift + noise + (inFault ? metricEffect.delta : 0);
    const value = normalizedValue(rawValue, config);
    labels.push(inFault);
    values.push(value);
    events.push(makeEvent(value, metric, config, descriptor.events[index].occurred_at));
  }

  return { metric, unit: config.unit, values, labels, events };
}

export function generateAi9MultimetricServicesV1(seed) {
  if (!Number.isInteger(seed) || seed < 0 || seed > 0xFFFF_FFFF) reject('invalid_seed');
  const source = generateAi9SyntheticScenariosV2(seed);
  const services = source.scenarios.map((descriptor, serviceIndex) => {
    const effects = descriptor.group === 'injected_fault'
      ? FAULT_EFFECTS[descriptor.id]
      : AI9_MULTIMETRIC_SERVICE_GENERATOR_V1_POLICY.control_metric_names.map(metric => ({
        metric,
        delta: 0,
      }));
    if (!effects || effects.length !== 3) reject('invalid_service_metric_effects');
    const metrics = effects.map((metricEffect, metricIndex) => makeMetricStream({
      descriptor,
      serviceIndex,
      metricIndex,
      metricEffect,
      seed,
    }));
    return { id: descriptor.id, group: descriptor.group, metrics };
  });
  return {
    classification: AI9_MULTIMETRIC_SERVICE_GENERATOR_V1_POLICY.classification,
    split: 'ai9_multimetric_confirmation_v1',
    seed,
    window_seconds: WINDOW_SECONDS,
    baseline_points: source.baseline_points,
    services,
  };
}

export function digestAi9MultimetricInputV1(dataset) {
  if (!dataset || !Array.isArray(dataset.services)) reject('invalid_multimetric_dataset');
  const digestShape = {
    classification: dataset.classification,
    split: dataset.split,
    seed: dataset.seed,
    window_seconds: dataset.window_seconds,
    baseline_points: dataset.baseline_points,
    services: dataset.services.map(service => ({
      id: service.id,
      group: service.group,
      metrics: service.metrics.map(metric => ({
        metric: metric.metric,
        unit: metric.unit,
        values: metric.values,
        labels: metric.labels,
      })),
    })),
  };
  return createHash('sha256').update(canonicalJson(digestShape)).digest('hex');
}
