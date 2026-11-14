#!/usr/bin/env node
import { pathToFileURL } from 'node:url';
import {
  EventIngestError,
  readInputFile,
} from '../ai_intelligence/event_ingest.mjs';
import {
  canonicalJson,
  EVENT_SCHEMA_VERSION,
  MAX_EVENTS_PER_BATCH,
  MAX_INPUT_BYTES,
  normalizeEvent,
  parseEventLines,
  parseJsonLine,
} from '../ai_intelligence/event_schema.mjs';

export { MAX_EVENTS_PER_BATCH, MAX_INPUT_BYTES };

export const ALLOWED_SOURCES = Object.freeze({
  'https://github.com/hamedonassar95/Devobs': 'Devobs',
  'https://github.com/hamedonassar95/devobs-saas': 'devobs-saas',
  'https://github.com/hamedonassar95/phone-repair-assistant-v2': 'phone-repair-assistant-v2',
  'https://github.com/hamedonassar95/al-dala-mobile': 'al-dala-mobile',
  'https://github.com/hamedonassar95/LiveOps-Integration': 'LiveOps-Integration',
  'https://github.com/hamedonassar95/DevObs-ai-Intelligence-': 'DevObs-ai-Intelligence-',
});

const EVENT_TYPE = 'devobs.ci.result.v1';
const CLOUDEVENT_FIELDS = new Set([
  'specversion', 'id', 'source', 'type', 'time', 'datacontenttype', 'data',
]);
const CI_DATA_FIELDS = new Set(['workflow', 'job', 'conclusion', 'commit_sha']);
const SAFE_CLOUDEVENT_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/;
const PERSONAL_PHONE_PATTERN = /(?<![A-Za-z0-9])\+?\d{3}[ -]\d{3}[ -]\d{4}(?![A-Za-z0-9])|(?<![A-Za-z0-9])\d{3}[ -]\d{4}(?![A-Za-z0-9])/;
const CONCLUSION_SEVERITY = Object.freeze({
  success: 'info',
  neutral: 'info',
  skipped: 'warning',
  cancelled: 'warning',
  action_required: 'warning',
  failure: 'error',
  timed_out: 'error',
  unknown: 'unknown',
});
const ERROR_CODES = new Set([
  'invalid_arguments', 'invalid_input', 'input_required', 'input_unavailable',
  'input_too_large', 'invalid_utf8', 'empty_input', 'invalid_json',
  'duplicate_json_key', 'invalid_batch_size', 'empty_line',
  'invalid_cloudevent_fields', 'unsupported_specversion', 'invalid_id',
  'invalid_or_sensitive_id', 'unknown_source', 'unsupported_type',
  'invalid_timestamp', 'unsupported_content_type', 'invalid_ci_data',
  'invalid_ci_data_fields', 'invalid_conclusion', 'invalid_commit_sha',
  'duplicate_source_id', 'invalid_ai1_event', 'duplicate_ai1_event',
  'internal_error',
]);

export class CloudEventsAdapterError extends Error {
  constructor(code) {
    super(code);
    this.name = 'CloudEventsAdapterError';
    this.code = code;
  }
}

function reject(code) {
  throw new CloudEventsAdapterError(code);
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function hasExactKeys(value, expected) {
  return isPlainObject(value) && Object.keys(value).length === expected.size
    && Object.keys(value).every(key => expected.has(key));
}

function normalizeRfc3339(value) {
  if (typeof value !== 'string' || value.length > 40) reject('invalid_timestamp');
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) reject('invalid_timestamp');
  const [, yearText, monthText, dayText, hourText, minuteText, secondText, , zone] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  if (month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59 || second > 59) {
    reject('invalid_timestamp');
  }
  if (zone !== 'Z') {
    const offsetHour = Number(zone.slice(1, 3));
    const offsetMinute = Number(zone.slice(4, 6));
    if (offsetHour > 23 || offsetMinute > 59) reject('invalid_timestamp');
  }
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
    reject('invalid_timestamp');
  }
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) reject('invalid_timestamp');
  return new Date(milliseconds).toISOString();
}

function validateUntrustedId(id, occurredAt) {
  if (typeof id !== 'string' || id.length === 0) reject('invalid_id');
  if (!SAFE_CLOUDEVENT_ID.test(id) || !/[A-Za-z]/.test(id) || PERSONAL_PHONE_PATTERN.test(id)) {
    reject('invalid_or_sensitive_id');
  }
  try {
    // Reuse AI-1's bounded-label and sensitive-text checks for this untrusted,
    // non-persisted CloudEvents identifier rather than creating a second policy.
    normalizeEvent({
      schema_version: EVENT_SCHEMA_VERSION,
      occurred_at: occurredAt,
      source: 'github_actions',
      kind: 'ci_result',
      severity: 'info',
      data: { workflow: id, job: 'id-validation', conclusion: 'unknown', commit_sha: null },
    });
  } catch {
    reject('invalid_or_sensitive_id');
  }
}

function parseCloudEvent(value) {
  if (!hasExactKeys(value, CLOUDEVENT_FIELDS)) reject('invalid_cloudevent_fields');
  if (value.specversion !== '1.0') reject('unsupported_specversion');
  if (typeof value.id !== 'string' || value.id.length === 0) reject('invalid_id');
  if (typeof value.source !== 'string' || !Object.hasOwn(ALLOWED_SOURCES, value.source)) reject('unknown_source');
  if (value.type !== EVENT_TYPE) reject('unsupported_type');
  if (value.datacontenttype !== 'application/json') reject('unsupported_content_type');
  const occurredAt = normalizeRfc3339(value.time);
  validateUntrustedId(value.id, occurredAt);
  if (!hasExactKeys(value.data, CI_DATA_FIELDS)) reject('invalid_ci_data_fields');
  if (typeof value.data.workflow !== 'string' || typeof value.data.job !== 'string') reject('invalid_ci_data');
  if (PERSONAL_PHONE_PATTERN.test(value.data.workflow) || PERSONAL_PHONE_PATTERN.test(value.data.job)) {
    reject('invalid_ci_data');
  }
  if (!Object.hasOwn(CONCLUSION_SEVERITY, value.data.conclusion)) reject('invalid_conclusion');
  if (value.data.commit_sha !== null
    && (typeof value.data.commit_sha !== 'string' || !/^[0-9a-f]{40}$/.test(value.data.commit_sha))) {
    reject('invalid_commit_sha');
  }

  const sourceId = `${value.source}\u0000${value.id}`;
  return {
    sourceId,
    record: {
      schema_version: EVENT_SCHEMA_VERSION,
      occurred_at: occurredAt,
      source: 'github_actions',
      kind: 'ci_result',
      severity: CONCLUSION_SEVERITY[value.data.conclusion],
      data: {
        workflow: `${ALLOWED_SOURCES[value.source]} - ${value.data.workflow}`,
        job: value.data.job,
        conclusion: value.data.conclusion,
        commit_sha: value.data.commit_sha,
      },
    },
  };
}

export function convertText(text) {
  if (typeof text !== 'string') reject('invalid_input');
  if (Buffer.byteLength(text, 'utf8') > MAX_INPUT_BYTES) reject('input_too_large');
  if (text.length === 0) reject('empty_input');
  const lines = text.split(/\r?\n/);
  if (lines.at(-1) === '') lines.pop();
  if (lines.length === 0 || lines.length > MAX_EVENTS_PER_BATCH) reject('invalid_batch_size');
  if (lines.some(line => line.trim() === '')) reject('empty_line');

  const sourceIds = new Set();
  const records = lines.map(line => {
    let parsed;
    try {
      parsed = parseJsonLine(line);
    } catch (error) {
      if (error?.code === 'duplicate_json_key') reject('duplicate_json_key');
      reject('invalid_json');
    }
    const converted = parseCloudEvent(parsed);
    if (sourceIds.has(converted.sourceId)) reject('duplicate_source_id');
    sourceIds.add(converted.sourceId);
    try {
      const { event_id: _eventId, ...record } = normalizeEvent(converted.record);
      return record;
    } catch {
      reject('invalid_ai1_event');
    }
  });

  const output = `${records.map(canonicalJson).join('\n')}\n`;
  try {
    const verified = parseEventLines(output);
    if (verified.events.length !== records.length || verified.duplicatesInBatch !== 0) {
      reject('duplicate_ai1_event');
    }
  } catch (error) {
    if (error instanceof CloudEventsAdapterError) throw error;
    reject('invalid_ai1_event');
  }
  return output;
}

function parseArgs(args) {
  if (args.length !== 2 || args[0] !== '--input' || typeof args[1] !== 'string'
    || args[1].length === 0 || (args[1] !== '-' && args[1].startsWith('--'))) {
    reject('invalid_arguments');
  }
  return { input: args[1] };
}

function safeErrorCode(error) {
  if (error instanceof CloudEventsAdapterError && ERROR_CODES.has(error.code)) return error.code;
  if (error instanceof EventIngestError) {
    if (error.code === 'input_too_large') return 'input_too_large';
    if (error.code === 'input_required') return 'input_required';
    if (error.code === 'invalid_utf8') return 'invalid_utf8';
    return 'input_unavailable';
  }
  return 'internal_error';
}

export async function main(args = process.argv.slice(2)) {
  try {
    const { input } = parseArgs(args);
    const text = await readInputFile(input);
    process.stdout.write(convertText(text));
    return 0;
  } catch (error) {
    process.stderr.write(`cloudevents-ci-adapter: ${safeErrorCode(error)}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
