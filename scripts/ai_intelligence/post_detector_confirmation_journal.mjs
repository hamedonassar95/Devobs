import { createHash, randomUUID } from 'node:crypto';
import {
  constants as fsConstants,
  open,
  realpath,
  rename,
  stat,
  unlink,
} from 'node:fs/promises';
import path from 'node:path';
import {
  createPostDetectorConfirmationLayer,
  POST_DETECTOR_CONFIRMATION_POLICY,
} from './post_detector_confirmation.mjs';

export const POST_DETECTOR_CONFIRMATION_JOURNAL_VERSION = 'ai9-confirmation-journal-v1';
export const POST_DETECTOR_CONFIRMATION_JOURNAL_LIMITS = Object.freeze({
  max_bytes: 8 * 1024 * 1024,
  max_pending_events: 10_000,
  max_acknowledgements: 1_000,
});

const EVENT_TYPES = Object.freeze([
  'incident_started',
  'incident_closed',
  'incident_interrupted',
]);
const INTERRUPTION_REASONS = Object.freeze([
  'service_window_gap',
  'metric_observation_gap',
]);
const SHA256_PATTERN = /^[a-f0-9]{64}$/;

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function isRecord(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function hasExactKeys(value, keys) {
  return isRecord(value)
    && Object.keys(value).length === keys.length
    && keys.every(key => Object.hasOwn(value, key));
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function hashJson(value) {
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function validId(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 128
    && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
}

function makeOutboxEvent({ eventType, serviceId, metric, incidentId, occurredAt, reason = null }) {
  const payload = {
    event_type: eventType,
    service_id: serviceId,
    metric,
    incident_id: incidentId,
    occurred_at: occurredAt,
    policy_version: POST_DETECTOR_CONFIRMATION_POLICY.version,
    reason,
  };
  return { event_id: hashJson(payload), ...payload };
}

function validateOutboxEvent(event) {
  if (!hasExactKeys(event, [
    'event_id', 'event_type', 'service_id', 'metric', 'incident_id', 'occurred_at',
    'policy_version', 'reason',
  ])
    || !SHA256_PATTERN.test(event.event_id)
    || !EVENT_TYPES.includes(event.event_type)
    || !validId(event.service_id)
    || !validId(event.metric)
    || !validId(event.incident_id)
    || typeof event.occurred_at !== 'string'
    || !Number.isFinite(Date.parse(event.occurred_at))
    || event.policy_version !== POST_DETECTOR_CONFIRMATION_POLICY.version
    || !(event.reason === null || INTERRUPTION_REASONS.includes(event.reason))) {
    reject('invalid_journal_document');
  }
  if ((event.event_type === 'incident_interrupted') !== (event.reason !== null)) {
    reject('invalid_journal_document');
  }
  const { event_id: actualId, ...payload } = event;
  if (hashJson(payload) !== actualId) reject('invalid_journal_document');
}

function validateDocument(document) {
  if (!hasExactKeys(document, ['journal_version', 'checkpoint', 'outbox_events'])
    || document.journal_version !== POST_DETECTOR_CONFIRMATION_JOURNAL_VERSION
    || !Array.isArray(document.outbox_events)
    || document.outbox_events.length > POST_DETECTOR_CONFIRMATION_JOURNAL_LIMITS.max_pending_events) {
    reject('invalid_journal_document');
  }
  const layer = createPostDetectorConfirmationLayer({ checkpoint: document.checkpoint });
  const ids = new Set();
  for (const event of document.outbox_events) {
    validateOutboxEvent(event);
    if (ids.has(event.event_id)) reject('invalid_journal_document');
    ids.add(event.event_id);
  }
  return layer;
}

function initialDocument() {
  return {
    journal_version: POST_DETECTOR_CONFIRMATION_JOURNAL_VERSION,
    checkpoint: createPostDetectorConfirmationLayer().getCheckpoint(),
    outbox_events: [],
  };
}

function eventsFromResult(result) {
  const events = [];
  for (const item of result.metrics) {
    if (item.incident_started) {
      events.push(makeOutboxEvent({
        eventType: 'incident_started',
        serviceId: result.service_id,
        metric: item.metric,
        incidentId: item.incident_id,
        occurredAt: result.occurred_at,
      }));
    }
    if (item.incident_closed) {
      events.push(makeOutboxEvent({
        eventType: 'incident_closed',
        serviceId: result.service_id,
        metric: item.metric,
        incidentId: item.incident_id,
        occurredAt: result.occurred_at,
      }));
    }
  }
  for (const interruption of result.interrupted_incidents) {
    events.push(makeOutboxEvent({
      eventType: 'incident_interrupted',
      serviceId: result.service_id,
      metric: interruption.metric,
      incidentId: interruption.incident_id,
      occurredAt: result.occurred_at,
      reason: interruption.reason,
    }));
  }
  return events.sort((left, right) => left.metric.localeCompare(right.metric)
    || left.event_type.localeCompare(right.event_type)
    || left.incident_id.localeCompare(right.incident_id));
}

async function ensurePrivateDirectory(directory) {
  let directoryStat;
  let canonicalDirectory;
  try {
    [directoryStat, canonicalDirectory] = await Promise.all([stat(directory), realpath(directory)]);
  } catch {
    reject('journal_directory_unavailable');
  }
  if (!directoryStat.isDirectory() || canonicalDirectory !== directory
    || (directoryStat.mode & 0o077) !== 0) reject('unsafe_journal_directory');
}

async function readDocument(filePath) {
  const directory = path.dirname(filePath);
  await ensurePrivateDirectory(directory);
  let fileHandle;
  try {
    fileHandle = await open(filePath, fsConstants.O_RDONLY | fsConstants.O_NOFOLLOW);
  } catch (error) {
    if (error?.code === 'ENOENT') return initialDocument();
    if (error?.code === 'ELOOP') reject('unsafe_journal_file');
    reject('journal_read_failed');
  }

  try {
    const fileStat = await fileHandle.stat();
    if (!fileStat.isFile()) reject('unsafe_journal_file');
    if ((fileStat.mode & 0o077) !== 0) reject('unsafe_journal_permissions');
    if (fileStat.size > POST_DETECTOR_CONFIRMATION_JOURNAL_LIMITS.max_bytes) {
      reject('journal_size_limit');
    }
    let raw;
    try {
      raw = await fileHandle.readFile('utf8');
    } catch {
      reject('journal_read_failed');
    }
    if (Buffer.byteLength(raw, 'utf8') > POST_DETECTOR_CONFIRMATION_JOURNAL_LIMITS.max_bytes) {
      reject('journal_size_limit');
    }
    let document;
    try {
      document = JSON.parse(raw);
    } catch {
      reject('invalid_journal_document');
    }
    validateDocument(document);
    return document;
  } finally {
    await fileHandle.close();
  }
}

async function writeDocumentAtomically(filePath, document) {
  const serialized = `${JSON.stringify(document)}\n`;
  if (Buffer.byteLength(serialized, 'utf8') > POST_DETECTOR_CONFIRMATION_JOURNAL_LIMITS.max_bytes) {
    reject('journal_size_limit');
  }
  if (document.outbox_events.length > POST_DETECTOR_CONFIRMATION_JOURNAL_LIMITS.max_pending_events) {
    reject('journal_outbox_limit');
  }
  validateDocument(document);

  const directory = path.dirname(filePath);
  const temporaryPath = path.join(directory, `.${path.basename(filePath)}.${randomUUID()}.tmp`);
  let temporaryHandle;
  try {
    temporaryHandle = await open(temporaryPath, 'wx', 0o600);
    await temporaryHandle.writeFile(serialized, 'utf8');
    await temporaryHandle.sync();
    await temporaryHandle.close();
    temporaryHandle = null;
    await rename(temporaryPath, filePath);
    const directoryHandle = await open(directory, fsConstants.O_RDONLY);
    try {
      await directoryHandle.sync();
    } finally {
      await directoryHandle.close();
    }
  } catch {
    reject('journal_write_failed');
  } finally {
    if (temporaryHandle) await temporaryHandle.close().catch(() => {});
    await unlink(temporaryPath).catch(() => {});
  }
}

async function withExclusiveLock(filePath, operation) {
  const lockPath = `${filePath}.lock`;
  let lockHandle;
  try {
    lockHandle = await open(lockPath, 'wx', 0o600);
  } catch (error) {
    if (error?.code === 'EEXIST') reject('journal_locked');
    reject('journal_lock_failed');
  }
  let operationError;
  try {
    await lockHandle.writeFile(`${process.pid}\n`, 'utf8');
    await lockHandle.sync();
    return await operation();
  } catch (error) {
    operationError = error;
    throw error;
  } finally {
    await lockHandle.close().catch(() => {});
    try {
      await unlink(lockPath);
    } catch {
      if (!operationError) reject('journal_lock_release_failed');
    }
  }
}

function validateFilePath(filePath) {
  if (typeof filePath !== 'string' || !path.isAbsolute(filePath)
    || path.resolve(filePath) !== filePath || path.basename(filePath).length === 0
    || path.basename(filePath) === '.' || path.basename(filePath) === '..') {
    reject('invalid_journal_path');
  }
  return filePath;
}

/**
 * Local development journal for atomic confirmation checkpoint + event outbox.
 * The parent directory must exist, be private (mode 0700 or stricter), and be trusted.
 */
export function createPostDetectorConfirmationJournal({ filePath } = {}) {
  if (typeof fsConstants.O_NOFOLLOW !== 'number') reject('unsupported_journal_platform');
  const absoluteFilePath = validateFilePath(filePath);

  async function processServiceWindow(input) {
    return withExclusiveLock(absoluteFilePath, async () => {
      const document = await readDocument(absoluteFilePath);
      const layer = validateDocument(document);
      const oldService = document.checkpoint.services
        .find(service => service.service_id === input?.serviceId);
      const inputAt = typeof input?.occurredAt === 'string' ? Date.parse(input.occurredAt) : NaN;
      const retryOfLatestWindow = oldService?.last_window_at === inputAt;
      const result = layer.processServiceWindow(input);
      const outbox = [...document.outbox_events];
      const known = new Set(outbox.map(event => event.event_id));
      const queuedEvents = [];
      if (!retryOfLatestWindow) {
        for (const event of eventsFromResult(result)) {
          if (!known.has(event.event_id)) {
            outbox.push(event);
            known.add(event.event_id);
            queuedEvents.push(event);
          }
        }
      }
      const next = {
        journal_version: POST_DETECTOR_CONFIRMATION_JOURNAL_VERSION,
        checkpoint: layer.getCheckpoint(),
        outbox_events: outbox,
      };
      await writeDocumentAtomically(absoluteFilePath, next);
      return { result: cloneJson(result), queued_events: cloneJson(queuedEvents) };
    });
  }

  async function listPendingEvents({ limit = 100 } = {}) {
    if (!Number.isSafeInteger(limit) || limit < 1 || limit > 1_000) reject('invalid_outbox_limit');
    const document = await readDocument(absoluteFilePath);
    return cloneJson(document.outbox_events.slice(0, limit));
  }

  async function acknowledgeEvents(eventIds) {
    if (!Array.isArray(eventIds) || eventIds.length > POST_DETECTOR_CONFIRMATION_JOURNAL_LIMITS.max_acknowledgements
      || eventIds.some(id => typeof id !== 'string' || !SHA256_PATTERN.test(id))
      || new Set(eventIds).size !== eventIds.length) reject('invalid_outbox_acknowledgement');
    return withExclusiveLock(absoluteFilePath, async () => {
      const document = await readDocument(absoluteFilePath);
      const requested = new Set(eventIds);
      const remaining = document.outbox_events.filter(event => !requested.has(event.event_id));
      const acknowledgedCount = document.outbox_events.length - remaining.length;
      if (acknowledgedCount > 0) {
        await writeDocumentAtomically(absoluteFilePath, {
          journal_version: POST_DETECTOR_CONFIRMATION_JOURNAL_VERSION,
          checkpoint: document.checkpoint,
          outbox_events: remaining,
        });
      }
      return { acknowledged_count: acknowledgedCount };
    });
  }

  return Object.freeze({ processServiceWindow, listPendingEvents, acknowledgeEvents });
}
