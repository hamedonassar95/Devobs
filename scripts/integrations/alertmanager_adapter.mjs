#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readInputFile } from '../ai_intelligence/event_ingest.mjs';
import {
  canonicalJson, EVENT_SCHEMA_VERSION, MAX_EVENTS_PER_BATCH, MAX_INPUT_BYTES,
  normalizeEvent, parseEventLines, parseJsonLine,
} from '../ai_intelligence/event_schema.mjs';
import { ALLOWED_SOURCES } from './project_sources.mjs';

export { MAX_INPUT_BYTES, MAX_EVENTS_PER_BATCH };
// Selected upstream version, not an arbitrary custom webhook payload:
// https://github.com/prometheus/alertmanager/blob/v0.34.2/template/template.go
// https://github.com/prometheus/alertmanager/blob/v0.34.2/notify/webhook/webhook.go
const REQUIRED = ['version', 'groupKey', 'truncatedAlerts', 'receiver', 'status',
  'groupLabels', 'commonLabels', 'commonAnnotations', 'externalURL', 'alerts'];
const OPTIONAL = ['routeLabels', 'notification_reason'];
const ALERT_FIELDS = ['status', 'labels', 'annotations', 'startsAt', 'endsAt', 'generatorURL', 'fingerprint'];
const RULES = new Set(['HighCpuUsage', 'HighMemoryUsage', 'DiskSpaceRunningLow', 'ServiceDown']);
const LEVELS = Object.freeze({ warning: ['warning', 'minor'], critical: ['critical', 'critical'] });
const CODES = new Set(['invalid_arguments', 'invalid_scope', 'invalid_input', 'input_too_large',
  'input_required', 'input_unavailable', 'invalid_utf8', 'invalid_json', 'duplicate_json_key',
  'invalid_notification', 'unsupported_version', 'truncated_notification', 'invalid_batch_size',
  'invalid_alert', 'unknown_rule', 'invalid_severity', 'scope_mismatch', 'invalid_timestamp',
  'duplicate_alert', 'invalid_ai1_event', 'internal_error']);

export class AlertmanagerAdapterError extends Error {
  constructor(code) { super(code); this.name = 'AlertmanagerAdapterError'; this.code = code; }
}
function reject(code) { throw new AlertmanagerAdapterError(code); }
function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && [Object.prototype, null].includes(Object.getPrototypeOf(value));
}
function fields(value, required, optional = []) {
  return object(value) && required.every(key => Object.hasOwn(value, key))
    && Object.keys(value).every(key => required.includes(key) || optional.includes(key));
}
function stringMap(value) {
  return object(value) && Object.keys(value).length <= 64
    && Object.entries(value).every(([key, item]) => key.length <= 128
      && typeof item === 'string' && item.length <= 4096);
}
function status(value) { return value === 'firing' || value === 'resolved'; }
export function validateScope(scope) {
  if (!fields(scope, ['projectSource', 'serviceId'])
    || typeof scope.projectSource !== 'string'
    || !Object.hasOwn(ALLOWED_SOURCES, scope.projectSource)
    || typeof scope.serviceId !== 'string' || !/^[a-z][a-z0-9_-]{0,63}$/.test(scope.serviceId)) reject('invalid_scope');
  return ALLOWED_SOURCES[scope.projectSource];
}
function binding(labels, project, service) {
  if ((Object.hasOwn(labels, 'devobs_project') && labels.devobs_project !== project)
    || (Object.hasOwn(labels, 'devobs_service') && labels.devobs_service !== service)) reject('scope_mismatch');
}
function timestamp(value) {
  if (typeof value !== 'string'
    || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) reject('invalid_timestamp');
  let iso;
  try {
    iso = normalizeEvent({ schema_version: EVENT_SCHEMA_VERSION, occurred_at: value,
      source: 'operator', kind: 'incident', severity: 'unknown',
      data: { summary: 'Alertmanager timestamp validation', status: 'open', impact: 'unknown' } }).occurred_at;
  } catch { reject('invalid_timestamp'); }
  // AI-1 stores milliseconds. Keep nanoseconds in the episode identity so two
  // transitions inside one millisecond cannot collapse after normalization.
  const fraction = /\.(\d+)(?:Z|[+-]\d{2}:\d{2})$/.exec(value)?.[1] ?? '';
  return { iso, exact: `${iso.slice(0, 19)}.${fraction.padEnd(9, '0')}Z` };
}

export function convertText(text, scope) {
  const project = validateScope(scope);
  if (typeof text !== 'string') reject('invalid_input');
  if (Buffer.byteLength(text, 'utf8') > MAX_INPUT_BYTES) reject('input_too_large');
  let notification;
  try { notification = parseJsonLine(text); }
  catch (error) { reject(error?.code === 'duplicate_json_key' ? 'duplicate_json_key' : 'invalid_json'); }
  if (!fields(notification, REQUIRED, OPTIONAL)) reject('invalid_notification');
  if (notification.version !== '4') reject('unsupported_version');
  if (!Number.isSafeInteger(notification.truncatedAlerts) || notification.truncatedAlerts < 0) reject('invalid_notification');
  if (notification.truncatedAlerts !== 0) reject('truncated_notification');
  if (!status(notification.status) || !Array.isArray(notification.alerts)) reject('invalid_notification');
  if (notification.alerts.length === 0 || notification.alerts.length > MAX_EVENTS_PER_BATCH) reject('invalid_batch_size');
  for (const key of ['groupLabels', 'commonLabels', 'commonAnnotations', 'routeLabels']) {
    if ((key !== 'routeLabels' || Object.hasOwn(notification, key)) && !stringMap(notification[key])) reject('invalid_notification');
  }
  for (const key of ['groupKey', 'receiver', 'externalURL', 'notification_reason']) {
    if (Object.hasOwn(notification, key) && (typeof notification[key] !== 'string' || notification[key].length > 4096)) reject('invalid_notification');
  }
  for (const key of ['groupLabels', 'commonLabels', 'routeLabels']) {
    if (notification[key]) binding(notification[key], project, scope.serviceId);
  }
  const fingerprints = new Set();
  const records = notification.alerts.map(alert => {
    if (!fields(alert, ALERT_FIELDS) || !status(alert.status) || !stringMap(alert.labels)
      || !stringMap(alert.annotations) || typeof alert.generatorURL !== 'string' || alert.generatorURL.length > 4096
      || typeof alert.fingerprint !== 'string' || !/^[0-9a-f]{16}$/.test(alert.fingerprint)) reject('invalid_alert');
    if (!RULES.has(alert.labels.alertname)) reject('unknown_rule');
    if (!Object.hasOwn(LEVELS, alert.labels.severity)) reject('invalid_severity');
    binding(alert.labels, project, scope.serviceId);
    if (fingerprints.has(alert.fingerprint)) reject('duplicate_alert');
    fingerprints.add(alert.fingerprint);
    const start = timestamp(alert.startsAt);
    const end = timestamp(alert.endsAt);
    if (start.exact === '0001-01-01T00:00:00.000000000Z'
      || (alert.status === 'resolved' && end.exact < start.exact)) reject('invalid_timestamp');
    const episode = createHash('sha256').update(canonicalJson([
      scope.projectSource, scope.serviceId, alert.fingerprint, start.exact,
    ])).digest('hex');
    const [severity, impact] = LEVELS[alert.labels.severity];
    try {
      return normalizeEvent({ schema_version: EVENT_SCHEMA_VERSION,
        occurred_at: alert.status === 'firing' ? start.iso : end.iso,
        source: 'operator', kind: 'incident', severity,
        data: { summary: `Alertmanager ${project} ${scope.serviceId} ${alert.labels.alertname} ${episode}`,
          status: alert.status === 'firing' ? 'open' : 'resolved', impact } });
    } catch { reject('invalid_ai1_event'); }
  });
  const groupStatus = notification.alerts.some(alert => alert.status === 'firing') ? 'firing' : 'resolved';
  if (notification.status !== groupStatus) reject('invalid_notification');
  records.sort((a, b) => a.event_id.localeCompare(b.event_id));
  const output = `${records.map(({ event_id: _id, ...record }) => canonicalJson(record)).join('\n')}\n`;
  try {
    const verified = parseEventLines(output);
    if (verified.events.length !== records.length || verified.duplicatesInBatch !== 0) reject('invalid_ai1_event');
  } catch { reject('invalid_ai1_event'); }
  return output;
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
    const code = (error instanceof AlertmanagerAdapterError || error instanceof EventIngestError)
      && CODES.has(error.code) ? error.code : 'internal_error';
    process.stderr.write(`alertmanager-adapter: ${code}\n`);
    return 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) process.exitCode = await main();
