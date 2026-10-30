import {
  analyzeMetricEvents,
  MAX_ANALYSIS_EVENTS,
  MIN_HISTORY_POINTS,
} from './anomaly_detector.mjs';
import { parseStoredEvent } from './event_schema.mjs';
import { POST_DETECTOR_CONFIRMATION_POLICY } from './post_detector_confirmation.mjs';

export const POST_DETECTOR_CONFIRMATION_ADAPTER_VERSION = 'ai9-detector-confirmation-adapter-v1';

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

function validIdentifier(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 128
    && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
}

function canonicalUtcTimestamp(value) {
  if (typeof value !== 'string') reject('invalid_timestamp');
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp) || new Date(timestamp).toISOString() !== value) {
    reject('invalid_timestamp');
  }
  return timestamp;
}

function sameStrings(left, right) {
  return Array.isArray(left) && left.length === right.length
    && left.every((value, index) => value === right[index]);
}

function validateAdapterEnvelope(input) {
  if (!isRecord(input) || Object.keys(input).length !== 3
    || !Object.hasOwn(input, 'serviceId') || !Object.hasOwn(input, 'occurredAt')
    || !Object.hasOwn(input, 'events')) reject('invalid_adapter_input');
  if (!validIdentifier(input.serviceId)) reject('invalid_service_id');
  return {
    serviceId: input.serviceId,
    occurredAt: input.occurredAt,
    events: input.events,
  };
}

function validateAnalysis(analysis, occurredAt, seenMetrics) {
  if (!isRecord(analysis) || !validIdentifier(analysis.metric)
    || seenMetrics.has(analysis.metric)
    || !isRecord(analysis.latest)
    || !Array.isArray(analysis.signals)
    || new Set(analysis.signals).size !== analysis.signals.length
    || analysis.signals.some(channel => !POST_DETECTOR_CONFIRMATION_POLICY.allowed_channels.includes(channel))) {
    reject('invalid_detector_result');
  }
  seenMetrics.add(analysis.metric);
  if (analysis.latest.occurred_at !== occurredAt) reject('misaligned_metric_window');

  if (analysis.status === 'insufficient_data') {
    if (!Number.isSafeInteger(analysis.observations)
      || analysis.observations < 0 || analysis.observations >= MIN_HISTORY_POINTS
      || Object.hasOwn(analysis, 'detectors') || analysis.signals.length !== 0) {
      reject('invalid_detector_result');
    }
    return { metric: analysis.metric, channels: [] };
  }

  if (!['no_signal', 'anomaly_candidate'].includes(analysis.status)
    || !isRecord(analysis.detectors)) reject('invalid_detector_result');
  const detectorNames = Object.keys(analysis.detectors).sort();
  const allowedNames = [...POST_DETECTOR_CONFIRMATION_POLICY.allowed_channels].sort();
  if (!sameStrings(detectorNames, allowedNames)
    || detectorNames.some(name => !isRecord(analysis.detectors[name])
      || typeof analysis.detectors[name].flagged !== 'boolean')) reject('invalid_detector_result');

  const expectedSignals = POST_DETECTOR_CONFIRMATION_POLICY.allowed_channels
    .filter(channel => analysis.detectors[channel].flagged);
  if (!sameStrings(analysis.signals, expectedSignals)
    || (analysis.status === 'anomaly_candidate') !== (expectedSignals.length > 0)) {
    reject('invalid_detector_result');
  }
  return { metric: analysis.metric, channels: expectedSignals };
}

function toServiceWindow(input) {
  canonicalUtcTimestamp(input.occurredAt);
  if (!Array.isArray(input.events) || input.events.length === 0
    || input.events.length > MAX_ANALYSIS_EVENTS) reject('invalid_metric_event_batch');

  const eventIds = new Set();
  const metricEvents = input.events.map(record => {
    if (!isRecord(record) || record.kind !== 'server_metric') reject('metric_event_required');
    let event;
    try {
      event = parseStoredEvent(record);
    } catch {
      reject('invalid_metric_event');
    }
    if (event.kind !== 'server_metric') reject('metric_event_required');
    if (eventIds.has(event.event_id)) reject('duplicate_event_id');
    eventIds.add(event.event_id);
    return event;
  });

  let analyses;
  try {
    analyses = analyzeMetricEvents(metricEvents);
  } catch (error) {
    if (typeof error?.code === 'string') reject(error.code);
    reject('detector_analysis_failed');
  }
  if (analyses.length === 0) reject('empty_detector_result');

  const seenMetrics = new Set();
  const metrics = analyses.map(analysis => validateAnalysis(analysis, input.occurredAt, seenMetrics));
  return { serviceId: input.serviceId, occurredAt: input.occurredAt, metrics };
}

/**
 * Composes the existing event detector with an isolated post-detector
 * confirmation implementation. `authorizeService` must close over a trusted,
 * separately authenticated caller scope; this module requires the callback but
 * does not establish that the callback is correct.
 */
export function createDetectorConfirmationAdapter(options = {}) {
  if (!isRecord(options) || Object.keys(options).length !== 2
    || !Object.hasOwn(options, 'confirmationLayer') || !Object.hasOwn(options, 'authorizeService')) {
    reject('invalid_adapter_options');
  }
  const { confirmationLayer, authorizeService } = options;
  if (!isRecord(confirmationLayer) || typeof confirmationLayer.processServiceWindow !== 'function') {
    reject('invalid_confirmation_implementation');
  }
  if (typeof authorizeService !== 'function') reject('invalid_service_authorizer');

  async function processEventWindow(input) {
    const envelope = validateAdapterEnvelope(input);
    let authorized;
    try {
      authorized = await authorizeService(Object.freeze({ serviceId: envelope.serviceId }));
    } catch {
      reject('service_authorization_failed');
    }
    if (authorized !== true) reject('service_not_authorized');
    const serviceWindow = toServiceWindow(envelope);
    const confirmationOutput = await confirmationLayer.processServiceWindow(serviceWindow);
    return {
      adapter_version: POST_DETECTOR_CONFIRMATION_ADAPTER_VERSION,
      confirmation_policy_version: POST_DETECTOR_CONFIRMATION_POLICY.version,
      confirmation_output: confirmationOutput,
    };
  }

  return Object.freeze({ processEventWindow });
}
