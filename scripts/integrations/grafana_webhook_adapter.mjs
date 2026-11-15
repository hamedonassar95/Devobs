#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readInputFile } from '../ai_intelligence/event_ingest.mjs';
import { canonicalJson, normalizeEvent, parseEventLines, parseJsonLine } from '../ai_intelligence/event_schema.mjs';
import {
  AlertmanagerAdapterError, convertText as alertmanager, validateScope,
  MAX_INPUT_BYTES, MAX_EVENTS_PER_BATCH,
} from './alertmanager_adapter.mjs';

export { MAX_INPUT_BYTES, MAX_EVENTS_PER_BATCH };
// Grafana 13.2.4 pins this alerting revision; protocol version is "1".
// https://github.com/grafana/alerting/blob/7f02604ca93b1d6db805848d6a9b4d3c82540507/receivers/webhook/v1/webhook.go
// https://github.com/grafana/alerting/blob/7f02604ca93b1d6db805848d6a9b4d3c82540507/templates/template_data.go
const COMMON = ['receiver', 'status', 'groupLabels', 'commonLabels', 'commonAnnotations', 'externalURL', 'groupKey', 'truncatedAlerts'];
const ROOT = [...COMMON, 'version', 'orgId', 'alerts', 'title', 'state', 'message'];
const ALERT = ['status', 'labels', 'annotations', 'startsAt', 'endsAt', 'generatorURL', 'fingerprint'];
const URLS = ['silenceURL', 'dashboardURL', 'panelURL'];
const OPTIONAL_ALERT = ['valueString', 'orgId', 'ruleUID', 'imageURL'];
const CODES = new Set(['invalid_arguments', 'invalid_scope', 'invalid_input', 'input_too_large',
  'input_required', 'input_unavailable', 'invalid_utf8', 'invalid_json', 'duplicate_json_key',
  'invalid_notification', 'unsupported_version', 'truncated_notification', 'invalid_batch_size',
  'invalid_alert', 'unknown_rule', 'invalid_severity', 'scope_mismatch', 'invalid_timestamp',
  'duplicate_alert', 'invalid_ai1_event', 'internal_error']);

export class GrafanaWebhookAdapterError extends Error {
  constructor(code) { super(code); this.name = 'GrafanaWebhookAdapterError'; this.code = code; }
}
function reject(code) { throw new GrafanaWebhookAdapterError(code); }
function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && [Object.prototype, null].includes(Object.getPrototypeOf(value));
}
function fields(value, required, optional = []) {
  return object(value) && required.every(key => Object.hasOwn(value, key))
    && Object.keys(value).every(key => required.includes(key) || optional.includes(key));
}
function text(value, limit = 4096) { return typeof value === 'string' && value.length <= limit; }
function values(value) {
  return value === null || (object(value) && Object.keys(value).length <= 64
    && Object.entries(value).every(([key, item]) => key.length > 0 && key.length <= 128
      && typeof item === 'number' && Number.isFinite(item)));
}
const pick = (value, keys) => Object.fromEntries(keys.map(key => [key, value[key]]));

export function convertText(input, scope) {
  validateScope(scope);
  if (typeof input !== 'string') reject('invalid_input');
  if (Buffer.byteLength(input, 'utf8') > MAX_INPUT_BYTES) reject('input_too_large');
  let payload;
  try { payload = parseJsonLine(input); }
  catch (error) { reject(error?.code === 'duplicate_json_key' ? 'duplicate_json_key' : 'invalid_json'); }
  if (!fields(payload, ROOT, ['appVersion'])) reject('invalid_notification');
  if (payload.version !== '1') reject('unsupported_version');
  if (!Number.isSafeInteger(payload.orgId) || payload.orgId <= 0
    || !['firing', 'resolved'].includes(payload.status)
    || payload.state !== (payload.status === 'firing' ? 'alerting' : 'ok')
    || !text(payload.title) || !text(payload.message)
    || (Object.hasOwn(payload, 'appVersion') && !text(payload.appVersion, 128))) reject('invalid_notification');
  if (!Array.isArray(payload.alerts) || payload.alerts.length === 0
    || payload.alerts.length > MAX_EVENTS_PER_BATCH) reject('invalid_batch_size');
  const alerts = payload.alerts.map(alert => {
    if (!fields(alert, [...ALERT, ...URLS, 'values'], OPTIONAL_ALERT)
      || !URLS.every(key => text(alert[key])) || !values(alert.values)
      || (Object.hasOwn(alert, 'valueString') && !text(alert.valueString))
      || (Object.hasOwn(alert, 'orgId') && alert.orgId !== payload.orgId)
      || (Object.hasOwn(alert, 'ruleUID') && !text(alert.ruleUID, 128))
      || (Object.hasOwn(alert, 'imageURL') && !text(alert.imageURL))) reject('invalid_alert');
    return pick(alert, ALERT);
  });
  // Delegate rule, severity, time, scope, duplicate and group consistency
  // checks to the existing converter. No supplied URLs are fetched.
  const canonical = alertmanager(canonicalJson({ ...pick(payload, COMMON), version: '4', alerts }), scope);
  const records = parseEventLines(canonical).events.map(({ event_id: _id, ...event }) => {
    const parts = event.data.summary.split(' ');
    if (parts.length !== 5 || parts[0] !== 'Alertmanager') reject('internal_error');
    const episode = createHash('sha256').update(canonicalJson([payload.orgId, parts[4]])).digest('hex');
    return normalizeEvent({ ...event, data: { ...event.data,
      summary: `Grafana ${parts[1]} ${parts[2]} ${parts[3]} ${episode}` } });
  });
  records.sort((a, b) => a.event_id.localeCompare(b.event_id));
  return `${records.map(({ event_id: _id, ...record }) => canonicalJson(record)).join('\n')}\n`;
}

export async function main(args = process.argv.slice(2)) {
  try {
    if (args.length !== 6 || args[0] !== '--input' || args[2] !== '--source' || args[4] !== '--service'
      || typeof args[1] !== 'string' || args[1].length === 0 || args[1].startsWith('--')) reject('invalid_arguments');
    const scope = { projectSource: args[3], serviceId: args[5] };
    validateScope(scope);
    process.stdout.write(convertText(await readInputFile(args[1]), scope));
    return 0;
  } catch (error) {
    const code = (error instanceof GrafanaWebhookAdapterError || error instanceof AlertmanagerAdapterError
      || error instanceof EventIngestError) && CODES.has(error.code) ? error.code : 'internal_error';
    process.stderr.write(`grafana-webhook-adapter: ${code}\n`);
    return 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) process.exitCode = await main();
