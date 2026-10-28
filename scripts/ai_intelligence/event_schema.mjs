import { createHash } from 'node:crypto';

export const EVENT_SCHEMA_VERSION = 1;
export const MAX_INPUT_BYTES = 1_048_576;
export const MAX_EVENTS_PER_BATCH = 100;

const SOURCES = new Set(['application', 'github_actions', 'gitlab_ci', 'server', 'operator']);
const KINDS = new Set(['log', 'incident', 'ci_result', 'server_metric']);
const SEVERITIES = new Set(['debug', 'info', 'warning', 'error', 'critical', 'unknown']);
const SOURCE_BY_KIND = {
  log: SOURCES,
  incident: new Set(['application', 'operator']),
  ci_result: new Set(['github_actions', 'gitlab_ci']),
  server_metric: new Set(['server']),
};
const METRIC_UNITS = {
  cpu_percent: 'percent',
  memory_percent: 'percent',
  disk_percent: 'percent',
  error_rate: 'percent',
  request_rate: 'per_second',
  latency_ms: 'milliseconds',
  uptime_seconds: 'seconds',
};
const CONCLUSIONS = new Set(['success', 'failure', 'cancelled', 'skipped', 'timed_out', 'action_required', 'neutral', 'unknown']);
const TEXT_RISK_PATTERNS = [
  /\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b/i,
  /\bsk-(?:proj|svcacct|live)-[A-Za-z0-9_-]{20,}\b/i,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bAuthorization\s*:\s*Bearer\s+\S+/i,
  /\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)\:\/\/[^/\s:@]+:[^@\s/]+@/i,
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i,
  /\b[\w.+-]+@[a-z0-9.-]+\.[a-z]{2,}\b/i,
  /\b(?:https?:\/\/|www\.)[^\s<>]+/i,
  /\bgit@[a-z0-9.-]+:[^\s<>]+/i,
  /\b(?:phone|mobile|telephone|tel)\s*[:=]\s*\+?\d[\d .()/-]{5,}\d\b/i,
];

const INPUT_FIELDS = new Set(['schema_version', 'occurred_at', 'source', 'kind', 'severity', 'data']);
const STORED_FIELDS = new Set([...INPUT_FIELDS, 'event_id']);

export class EventIngestError extends Error {
  constructor(code) {
    super(code);
    this.name = 'EventIngestError';
    this.code = code;
  }
}

function reject(code) {
  throw new EventIngestError(code);
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function hasExactKeys(value, expected) {
  return isPlainObject(value) && Object.keys(value).length === expected.size
    && Object.keys(value).every(key => expected.has(key));
}

export function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (isPlainObject(value)) {
    const entries = Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`);
    return `{${entries.join(',')}}`;
  }
  return JSON.stringify(value);
}

function parseJsonWithoutDuplicateKeys(text) {
  let index = 0;
  const whitespace = () => {
    while (index < text.length && /\s/.test(text[index])) index++;
  };
  const readString = () => {
    const start = index;
    index++;
    while (index < text.length) {
      if (text[index] === '\\') {
        index += 2;
      } else if (text[index++] === '"') {
        try {
          return JSON.parse(text.slice(start, index));
        } catch {
          reject('invalid_json');
        }
      }
    }
    reject('invalid_json');
  };
  const parseValue = () => {
    whitespace();
    if (text[index] === '{') return parseObject();
    if (text[index] === '[') return parseArray();
    if (text[index] === '"') {
      readString();
      return;
    }
    const start = index;
    while (index < text.length && !/[\s,\]}]/.test(text[index])) index++;
    if (index === start) reject('invalid_json');
  };
  const parseObject = () => {
    index++;
    whitespace();
    if (text[index] === '}') {
      index++;
      return;
    }
    const keys = new Set();
    while (index < text.length) {
      whitespace();
      if (text[index] !== '"') reject('invalid_json');
      const key = readString();
      if (keys.has(key)) reject('duplicate_json_key');
      keys.add(key);
      whitespace();
      if (text[index++] !== ':') reject('invalid_json');
      parseValue();
      whitespace();
      if (text[index] === '}') {
        index++;
        return;
      }
      if (text[index++] !== ',') reject('invalid_json');
    }
    reject('invalid_json');
  };
  const parseArray = () => {
    index++;
    whitespace();
    if (text[index] === ']') {
      index++;
      return;
    }
    while (index < text.length) {
      parseValue();
      whitespace();
      if (text[index] === ']') {
        index++;
        return;
      }
      if (text[index++] !== ',') reject('invalid_json');
    }
    reject('invalid_json');
  };

  parseValue();
  whitespace();
  if (index !== text.length) reject('invalid_json');
  try {
    return JSON.parse(text);
  } catch {
    reject('invalid_json');
  }
}

function boundedText(value, maximum) {
  if (typeof value !== 'string' || value.length === 0 || value.length > maximum || value.trim() !== value) {
    reject('invalid_text');
  }
  if ([...value].some(character => {
    const code = character.codePointAt(0);
    return code < 32 && character !== '\n' && character !== '\t';
  })) reject('invalid_text');
  if (TEXT_RISK_PATTERNS.some(pattern => pattern.test(value))) reject('sensitive_text_rejected');
  return value;
}

function boundedLabel(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_. -]{0,99}$/.test(value) || value.trim() !== value) {
    reject('invalid_label');
  }
  if (TEXT_RISK_PATTERNS.some(pattern => pattern.test(value))) reject('sensitive_text_rejected');
  return value;
}

function normalizeTimestamp(value) {
  if (typeof value !== 'string' || value.length > 40 || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) {
    reject('invalid_timestamp');
  }
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) reject('invalid_timestamp');
  return new Date(milliseconds).toISOString();
}

function normalizeData(kind, data) {
  if (!isPlainObject(data)) reject('invalid_data');
  if (kind === 'log') {
    const fields = new Set(['stream', 'message']);
    if (!hasExactKeys(data, fields)) reject('invalid_data_fields');
    if (!new Set(['stdout', 'stderr', 'application']).has(data.stream)) reject('invalid_log_stream');
    return { stream: data.stream, message: boundedText(data.message, 2_000) };
  }
  if (kind === 'incident') {
    const fields = new Set(['summary', 'status', 'impact']);
    if (!hasExactKeys(data, fields)) reject('invalid_data_fields');
    if (!new Set(['open', 'acknowledged', 'resolved']).has(data.status)) reject('invalid_incident_status');
    if (!new Set(['none', 'minor', 'major', 'critical', 'unknown']).has(data.impact)) reject('invalid_incident_impact');
    return { summary: boundedText(data.summary, 500), status: data.status, impact: data.impact };
  }
  if (kind === 'ci_result') {
    const fields = new Set(['workflow', 'job', 'conclusion', 'commit_sha']);
    if (!hasExactKeys(data, fields)) reject('invalid_data_fields');
    if (!CONCLUSIONS.has(data.conclusion)) reject('invalid_ci_conclusion');
    if (data.commit_sha !== null && (typeof data.commit_sha !== 'string' || !/^[0-9a-f]{40}$/.test(data.commit_sha))) {
      reject('invalid_commit_sha');
    }
    return {
      workflow: boundedLabel(data.workflow),
      job: boundedLabel(data.job),
      conclusion: data.conclusion,
      commit_sha: data.commit_sha,
    };
  }
  if (kind === 'server_metric') {
    const fields = new Set(['name', 'value', 'unit']);
    if (!hasExactKeys(data, fields)) reject('invalid_data_fields');
    const expectedUnit = METRIC_UNITS[data.name];
    if (!expectedUnit || data.unit !== expectedUnit) reject('invalid_metric_unit');
    if (typeof data.value !== 'number' || !Number.isFinite(data.value) || data.value < 0) reject('invalid_metric_value');
    if (expectedUnit === 'percent' && data.value > 100) reject('invalid_metric_value');
    return { name: data.name, value: data.value, unit: data.unit };
  }
  reject('unsupported_kind');
}

function normalizeCore(record) {
  if (!hasExactKeys(record, INPUT_FIELDS)) reject('invalid_event_fields');
  if (record.schema_version !== EVENT_SCHEMA_VERSION) reject('unsupported_schema');
  if (typeof record.source !== 'string' || !SOURCES.has(record.source)) reject('unsupported_source');
  if (typeof record.kind !== 'string' || !KINDS.has(record.kind)) reject('unsupported_kind');
  if (!SOURCE_BY_KIND[record.kind].has(record.source)) reject('source_kind_mismatch');
  if (typeof record.severity !== 'string' || !SEVERITIES.has(record.severity)) reject('invalid_severity');
  return {
    schema_version: EVENT_SCHEMA_VERSION,
    occurred_at: normalizeTimestamp(record.occurred_at),
    source: record.source,
    kind: record.kind,
    severity: record.severity,
    data: normalizeData(record.kind, record.data),
  };
}

export function normalizeEvent(record) {
  const core = normalizeCore(record);
  const digest = createHash('sha256').update(canonicalJson(core), 'utf8').digest('hex');
  return { schema_version: EVENT_SCHEMA_VERSION, event_id: `sha256:${digest}`, ...core };
}

export function parseStoredEvent(record) {
  if (!hasExactKeys(record, STORED_FIELDS) || typeof record.event_id !== 'string' || !/^sha256:[0-9a-f]{64}$/.test(record.event_id)) {
    reject('invalid_store');
  }
  let normalized;
  try {
    normalized = normalizeEvent({
      schema_version: record.schema_version,
      occurred_at: record.occurred_at,
      source: record.source,
      kind: record.kind,
      severity: record.severity,
      data: record.data,
    });
  } catch {
    reject('invalid_store');
  }
  if (normalized.event_id !== record.event_id || canonicalJson(normalized) !== canonicalJson(record)) reject('invalid_store');
  return normalized;
}

export function parseJsonLine(line) {
  try {
    return parseJsonWithoutDuplicateKeys(line);
  } catch (error) {
    if (error instanceof EventIngestError) throw error;
    reject('invalid_json');
  }
}

export function parseEventLines(text) {
  if (typeof text !== 'string' || text.length === 0) reject('empty_input');
  if (Buffer.byteLength(text, 'utf8') > MAX_INPUT_BYTES) reject('input_too_large');
  const lines = text.split(/\r?\n/);
  if (lines.at(-1) === '') lines.pop();
  if (lines.length === 0 || lines.length > MAX_EVENTS_PER_BATCH) reject('invalid_batch_size');
  if (lines.some(line => line.trim() === '')) reject('empty_line');
  const inputEvents = lines.map(line => parseJsonLine(line));
  const normalized = inputEvents.map(normalizeEvent);
  const unique = new Map();
  for (const event of normalized) {
    const previous = unique.get(event.event_id);
    if (previous && canonicalJson(previous) !== canonicalJson(event)) reject('event_id_conflict');
    unique.set(event.event_id, event);
  }
  return { events: [...unique.values()], duplicatesInBatch: normalized.length - unique.size };
}
