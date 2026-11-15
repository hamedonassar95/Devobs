#!/usr/bin/env node
/** Offline, synthetic-only OTLP JSON gauge subset -> existing AI-1 server_metric. */
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { EventIngestError, readInputFile } from '../ai_intelligence/event_ingest.mjs';
import {
  canonicalJson, EVENT_SCHEMA_VERSION, MAX_EVENTS_PER_BATCH, MAX_INPUT_BYTES,
  normalizeEvent, parseEventLines, parseJsonLine,
} from '../ai_intelligence/event_schema.mjs';

export { MAX_EVENTS_PER_BATCH, MAX_INPUT_BYTES };
const ERROR_CODES = new Set([
  'invalid_arguments', 'invalid_input', 'input_unavailable', 'input_required',
  'input_too_large', 'invalid_utf8', 'invalid_json', 'duplicate_json_key',
  'invalid_otlp_structure', 'invalid_service', 'unsupported_metric',
  'invalid_batch_size', 'invalid_point', 'invalid_timestamp',
  'duplicate_point_time', 'invalid_ai1_event', 'internal_error',
]);
const EPOCH_2000_NS = 946684800000000000n;
const EPOCH_2100_NS = 4102444800000000000n;

export class OtlpErrorRateError extends Error {
  constructor(code) { super(code); this.name = 'OtlpErrorRateError'; this.code = code; }
}
function reject(code) { throw new OtlpErrorRateError(code); }
function exact(value, keys) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && [Object.prototype, null].includes(Object.getPrototypeOf(value))
    && Object.keys(value).length === keys.length
    && keys.every(key => Object.hasOwn(value, key));
}
function timestamp(nanos) {
  if (typeof nanos !== 'string' || !/^[1-9][0-9]{15,19}$/.test(nanos)) reject('invalid_timestamp');
  const value = BigInt(nanos);
  if (value < EPOCH_2000_NS || value >= EPOCH_2100_NS) reject('invalid_timestamp');
  const milliseconds = Number(value / 1000000n);
  const date = new Date(milliseconds);
  if (!Number.isFinite(date.getTime())) reject('invalid_timestamp');
  return date.toISOString();
}

/**
 * A deliberate fail-closed subset, not a general OTLP decoder.
 * Requires one devobs service, one error_rate_pct gauge, and 1..100 unlabeled points.
 * Never reads a network endpoint or authenticates telemetry provenance.
 */
export function convertText(raw) {
  if (typeof raw !== 'string') reject('invalid_input');
  if (Buffer.byteLength(raw, 'utf8') > MAX_INPUT_BYTES) reject('input_too_large');
  let input;
  try { input = parseJsonLine(raw); }
  catch (error) { reject(error?.code === 'duplicate_json_key' ? 'duplicate_json_key' : 'invalid_json'); }
  if (!exact(input, ['resourceMetrics']) || !Array.isArray(input.resourceMetrics)
    || input.resourceMetrics.length !== 1) reject('invalid_otlp_structure');
  const resourceMetric = input.resourceMetrics[0];
  if (!exact(resourceMetric, ['resource', 'scopeMetrics'])
    || !exact(resourceMetric.resource, ['attributes'])) reject('invalid_otlp_structure');
  const attrs = resourceMetric.resource.attributes;
  if (!Array.isArray(attrs) || attrs.length !== 1
    || !exact(attrs[0], ['key', 'value'])
    || attrs[0].key !== 'service.name'
    || !exact(attrs[0].value, ['stringValue'])
    || attrs[0].value.stringValue !== 'devobs') reject('invalid_service');
  if (!Array.isArray(resourceMetric.scopeMetrics) || resourceMetric.scopeMetrics.length !== 1
    || !exact(resourceMetric.scopeMetrics[0], ['metrics'])
    || !Array.isArray(resourceMetric.scopeMetrics[0].metrics)
    || resourceMetric.scopeMetrics[0].metrics.length !== 1) reject('invalid_otlp_structure');
  const metric = resourceMetric.scopeMetrics[0].metrics[0];
  if (!exact(metric, ['name', 'unit', 'gauge'])
    || metric.name !== 'error_rate_pct' || metric.unit !== '%'
    || !exact(metric.gauge, ['dataPoints'])
    || !Array.isArray(metric.gauge.dataPoints)) reject('unsupported_metric');
  const points = metric.gauge.dataPoints;
  if (points.length === 0 || points.length > MAX_EVENTS_PER_BATCH) reject('invalid_batch_size');
  const observedTimes = new Set();
  const records = points.map(point => {
    if (!exact(point, ['timeUnixNano', 'asDouble'])
      || typeof point.asDouble !== 'number' || !Number.isFinite(point.asDouble)
      || point.asDouble < 0 || point.asDouble > 100) reject('invalid_point');
    const occurredAt = timestamp(point.timeUnixNano);
    if (observedTimes.has(occurredAt)) reject('duplicate_point_time');
    observedTimes.add(occurredAt);
    try {
      const { event_id: _id, ...event } = normalizeEvent({
        schema_version: EVENT_SCHEMA_VERSION, occurred_at: occurredAt,
        source: 'server', kind: 'server_metric', severity: 'info',
        data: { name: 'error_rate', value: point.asDouble, unit: 'percent' },
      });
      return event;
    } catch { reject('invalid_ai1_event'); }
  });
  records.sort((a, b) => a.occurred_at.localeCompare(b.occurred_at));
  const output = records.map(canonicalJson).join('\n') + '\n';
  try {
    const checked = parseEventLines(output);
    if (checked.events.length !== records.length || checked.duplicatesInBatch !== 0) reject('invalid_ai1_event');
  } catch { reject('invalid_ai1_event'); }
  return output;
}

export async function main(args = process.argv.slice(2)) {
  try {
    if (args.length !== 2 || args[0] !== '--input'
      || typeof args[1] !== 'string' || !args[1] || (args[1].startsWith('-') && args[1] !== '-')) {
      reject('invalid_arguments');
    }
    const output = convertText(await readInputFile(args[1]));
    process.stdout.write(output);
    return 0;
  } catch (error) {
    const code = (error instanceof OtlpErrorRateError || error instanceof EventIngestError)
      && ERROR_CODES.has(error.code) ? error.code : 'internal_error';
    process.stderr.write('otlp-error-rate-adapter: ' + code + '\n');
    return 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
