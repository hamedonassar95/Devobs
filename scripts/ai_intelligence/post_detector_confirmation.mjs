import { createHash } from 'node:crypto';

const POLICY = Object.freeze({
  version: 'ai9-post-detector-confirmation-v1',
  cadence_seconds: 60,
  coincidence_window_seconds: 120,
  persistence_window_count: 3,
  persistence_required_count: 2,
  distinct_metric_names_required: 2,
  quiet_windows_to_close: 2,
  allowed_channels: Object.freeze(['z_score', 'moving_average', 'ewma', 'error_rate_spike']),
});
const CADENCE_MS = POLICY.cadence_seconds * 1_000;
const COINCIDENCE_MS = POLICY.coincidence_window_seconds * 1_000;
export const POST_DETECTOR_CONFIRMATION_CHECKPOINT_VERSION = 'ai9-confirmation-checkpoint-v1';
const CONFIRMATION_REASONS = Object.freeze([
  'persistent_same_channel_2_of_3',
  'cross_metric_coincidence_within_120s',
]);

function reject(code) {
  const error = new Error(code);
  error.code = code;
  throw error;
}

function validIdentifier(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 128
    && value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
}

function validateWindow(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) reject('invalid_service_window');
  if (!validIdentifier(input.serviceId)) reject('invalid_service_id');
  if (typeof input.occurredAt !== 'string' || !Number.isFinite(Date.parse(input.occurredAt))) {
    reject('invalid_timestamp');
  }
  if (!Array.isArray(input.metrics)) reject('invalid_metric_list');
  const metricNames = new Set();
  const metrics = input.metrics.map(item => {
    if (!item || typeof item !== 'object' || Array.isArray(item)
      || !validIdentifier(item.metric)) reject('invalid_metric');
    if (metricNames.has(item.metric)) reject('duplicate_metric_in_service_window');
    metricNames.add(item.metric);
    if (!Array.isArray(item.channels)) reject('invalid_channel_list');
    const channelSet = new Set();
    for (const channel of item.channels) {
      if (!POLICY.allowed_channels.includes(channel)) reject('unsupported_channel');
      if (channelSet.has(channel)) reject('duplicate_channel');
      channelSet.add(channel);
    }
    return { metric: item.metric, channels: [...channelSet] };
  });
  return { serviceId: input.serviceId, occurredAt: input.occurredAt, atMs: Date.parse(input.occurredAt), metrics };
}

function newMetricState() {
  return {
    history: [],
    lastObservedAt: null,
    nextIncidentNumber: 1,
    activeIncident: null,
    quietWindows: 0,
    startedIncidents: 0,
    closedIncidents: 0,
    interruptedIncidents: 0,
  };
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
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

function validCounter(value, minimum = 0) {
  return Number.isSafeInteger(value) && value >= minimum;
}

function validTimestampMs(value) {
  return Number.isSafeInteger(value) && Number.isFinite(new Date(value).getTime());
}

function validateCheckpointResult(value, serviceId, lastWindowAt) {
  if (!hasExactKeys(value, ['service_id', 'occurred_at', 'interrupted_incidents', 'metrics'])
    || value.service_id !== serviceId
    || typeof value.occurred_at !== 'string'
    || Date.parse(value.occurred_at) !== lastWindowAt
    || !Array.isArray(value.interrupted_incidents)
    || !Array.isArray(value.metrics)) reject('invalid_checkpoint');

  for (const interruption of value.interrupted_incidents) {
    if (!hasExactKeys(interruption, ['metric', 'incident_id', 'reason'])
      || !validIdentifier(interruption.metric)
      || typeof interruption.incident_id !== 'string'
      || !['service_window_gap', 'metric_observation_gap'].includes(interruption.reason)) {
      reject('invalid_checkpoint');
    }
  }
  const metricNames = new Set();
  for (const metric of value.metrics) {
    if (!hasExactKeys(metric, [
      'metric', 'raw_signal_count', 'confirmed', 'confirmation_reasons', 'incident_id',
      'incident_started', 'incident_closed', 'interrupted_incident', 'incident_open', 'quiet_windows',
    ])
      || !validIdentifier(metric.metric)
      || metricNames.has(metric.metric)
      || !validCounter(metric.raw_signal_count)
      || metric.raw_signal_count > POLICY.allowed_channels.length
      || typeof metric.confirmed !== 'boolean'
      || !Array.isArray(metric.confirmation_reasons)
      || metric.confirmation_reasons.some(reason => !CONFIRMATION_REASONS.includes(reason))
      || new Set(metric.confirmation_reasons).size !== metric.confirmation_reasons.length
      || !(metric.incident_id === null || typeof metric.incident_id === 'string')
      || typeof metric.incident_started !== 'boolean'
      || typeof metric.incident_closed !== 'boolean'
      || !(metric.interrupted_incident === null || typeof metric.interrupted_incident === 'string')
      || typeof metric.incident_open !== 'boolean'
      || !validCounter(metric.quiet_windows, 0)
      || metric.quiet_windows > POLICY.quiet_windows_to_close - 1
      || (metric.confirmed && metric.raw_signal_count === 0)
      || (metric.incident_started && metric.incident_closed)
      || (metric.incident_open && metric.incident_closed)) reject('invalid_checkpoint');
    metricNames.add(metric.metric);
  }
}

function checkpointToServices(checkpoint) {
  if (!isRecord(checkpoint)) reject('invalid_checkpoint');
  if (checkpoint.checkpoint_version !== POST_DETECTOR_CONFIRMATION_CHECKPOINT_VERSION) {
    reject('unsupported_checkpoint_version');
  }
  if (checkpoint.policy_version !== POLICY.version) reject('checkpoint_policy_mismatch');
  if (!hasExactKeys(checkpoint, ['checkpoint_version', 'policy_version', 'services'])
    || !Array.isArray(checkpoint.services)) reject('invalid_checkpoint');

  const services = new Map();
  for (const savedService of checkpoint.services) {
    if (!hasExactKeys(savedService, [
      'service_id', 'last_window_at', 'last_window_fingerprint', 'last_result',
      'coincidence_history', 'metrics',
    ])
      || !validIdentifier(savedService.service_id)
      || services.has(savedService.service_id)
      || !(savedService.last_window_at === null || validTimestampMs(savedService.last_window_at))
      || !(savedService.last_window_fingerprint === null
        || (typeof savedService.last_window_fingerprint === 'string'
          && /^[a-f0-9]{64}$/.test(savedService.last_window_fingerprint)))
      || !(savedService.last_result === null || isRecord(savedService.last_result))
      || !Array.isArray(savedService.coincidence_history)
      || !Array.isArray(savedService.metrics)) reject('invalid_checkpoint');

    const hasLastWindow = savedService.last_window_at !== null;
    if (hasLastWindow !== (savedService.last_window_fingerprint !== null)
      || hasLastWindow !== (savedService.last_result !== null)) reject('invalid_checkpoint');
    if (hasLastWindow) validateCheckpointResult(
      savedService.last_result,
      savedService.service_id,
      savedService.last_window_at,
    );

    const service = {
      lastWindowAt: savedService.last_window_at,
      lastWindowFingerprint: savedService.last_window_fingerprint,
      lastResult: savedService.last_result === null ? null : cloneJson(savedService.last_result),
      coincidenceHistory: [],
      metrics: new Map(),
    };

    for (const evidence of savedService.coincidence_history) {
      if (!hasExactKeys(evidence, ['metric', 'at_ms'])
        || !validIdentifier(evidence.metric)
        || !validTimestampMs(evidence.at_ms)
        || !hasLastWindow
        || evidence.at_ms > savedService.last_window_at
        || evidence.at_ms < savedService.last_window_at - COINCIDENCE_MS) reject('invalid_checkpoint');
      service.coincidenceHistory.push({ metric: evidence.metric, atMs: evidence.at_ms });
    }

    for (const savedMetric of savedService.metrics) {
      if (!hasExactKeys(savedMetric, [
        'metric', 'history', 'last_observed_at', 'next_incident_number', 'active_incident',
        'quiet_windows', 'started_incidents', 'closed_incidents', 'interrupted_incidents',
      ])
        || !validIdentifier(savedMetric.metric)
        || service.metrics.has(savedMetric.metric)
        || !Array.isArray(savedMetric.history)
        || savedMetric.history.length > POLICY.persistence_window_count
        || !(savedMetric.last_observed_at === null || validTimestampMs(savedMetric.last_observed_at))
        || !validCounter(savedMetric.next_incident_number, 1)
        || !(savedMetric.active_incident === null || isRecord(savedMetric.active_incident))
        || !validCounter(savedMetric.quiet_windows)
        || savedMetric.quiet_windows >= POLICY.quiet_windows_to_close
        || !validCounter(savedMetric.started_incidents)
        || !validCounter(savedMetric.closed_incidents)
        || !validCounter(savedMetric.interrupted_incidents)) reject('invalid_checkpoint');

      let previousAt = null;
      const history = savedMetric.history.map(record => {
        if (!hasExactKeys(record, ['at_ms', 'channels'])
          || !validTimestampMs(record.at_ms)
          || (previousAt !== null && record.at_ms - previousAt !== CADENCE_MS)
          || record.at_ms > savedMetric.last_observed_at
          || !Array.isArray(record.channels)) reject('invalid_checkpoint');
        previousAt = record.at_ms;
        const channels = new Set();
        for (const channel of record.channels) {
          if (!POLICY.allowed_channels.includes(channel) || channels.has(channel)) reject('invalid_checkpoint');
          channels.add(channel);
        }
        return { atMs: record.at_ms, channels: [...channels] };
      });

      if ((savedMetric.last_observed_at === null) !== (history.length === 0)
        || (history.length > 0 && history.at(-1).atMs !== savedMetric.last_observed_at)
        || (savedMetric.last_observed_at !== null
          && (!hasLastWindow || savedMetric.last_observed_at > savedService.last_window_at))) {
        reject('invalid_checkpoint');
      }

      let activeIncident = null;
      if (savedMetric.active_incident !== null) {
        const incident = savedMetric.active_incident;
        if (!hasExactKeys(incident, ['id', 'metric', 'started_at'])
          || typeof incident.id !== 'string'
          || incident.metric !== savedMetric.metric
          || typeof incident.started_at !== 'string'
          || !Number.isFinite(Date.parse(incident.started_at))
          || Date.parse(incident.started_at) > savedMetric.last_observed_at) reject('invalid_checkpoint');
        activeIncident = { id: incident.id, metric: incident.metric, startedAt: incident.started_at };
      }
      if ((activeIncident === null && savedMetric.quiet_windows !== 0)
        || savedMetric.started_incidents !== savedMetric.closed_incidents
          + savedMetric.interrupted_incidents + (activeIncident ? 1 : 0)
        || savedMetric.next_incident_number !== savedMetric.started_incidents + 1) reject('invalid_checkpoint');

      service.metrics.set(savedMetric.metric, {
        history,
        lastObservedAt: savedMetric.last_observed_at,
        nextIncidentNumber: savedMetric.next_incident_number,
        activeIncident,
        quietWindows: savedMetric.quiet_windows,
        startedIncidents: savedMetric.started_incidents,
        closedIncidents: savedMetric.closed_incidents,
        interruptedIncidents: savedMetric.interrupted_incidents,
      });
    }

    services.set(savedService.service_id, service);
  }
  return services;
}

function interruptMetric(metric, reason) {
  const interrupted = metric.activeIncident
    ? { incident_id: metric.activeIncident.id, reason }
    : null;
  if (interrupted) metric.interruptedIncidents++;
  metric.activeIncident = null;
  metric.quietWindows = 0;
  metric.history = [];
  return interrupted;
}

function updateIncident(metricState, metric, atMs, confirmed) {
  let incidentStarted = false;
  let incidentClosed = null;
  if (confirmed) {
    if (!metricState.activeIncident) {
      const id = `incident-${metricState.nextIncidentNumber++}`;
      metricState.activeIncident = { id, metric, startedAt: new Date(atMs).toISOString() };
      metricState.startedIncidents++;
      incidentStarted = true;
    }
    metricState.quietWindows = 0;
  } else if (metricState.activeIncident) {
    metricState.quietWindows++;
    if (metricState.quietWindows === POLICY.quiet_windows_to_close) {
      incidentClosed = metricState.activeIncident.id;
      metricState.activeIncident = null;
      metricState.closedIncidents++;
      metricState.quietWindows = 0;
    }
  }
  return { incidentStarted, incidentClosed };
}

/**
 * Stateful post-detector confirmation. It consumes channel names only; it never
 * reads metric values or modifies detector outputs. Create one instance per
 * worker/process and provide stable service IDs with time-ordered windows.
 */
export function createPostDetectorConfirmationLayer(options = {}) {
  if (!isRecord(options)
    || Object.keys(options).some(key => key !== 'checkpoint')) reject('invalid_checkpoint_options');
  const services = options.checkpoint === undefined || options.checkpoint === null
    ? new Map()
    : checkpointToServices(options.checkpoint);

  function serviceState(serviceId) {
    if (!services.has(serviceId)) {
      services.set(serviceId, {
        lastWindowAt: null,
        lastWindowFingerprint: null,
        lastResult: null,
        coincidenceHistory: [],
        metrics: new Map(),
      });
    }
    return services.get(serviceId);
  }

  function processServiceWindow(input) {
    const window = validateWindow(input);
    const fingerprint = createHash('sha256').update(JSON.stringify(window)).digest('hex');
    const service = serviceState(window.serviceId);
    if (service.lastWindowAt === window.atMs) {
      if (service.lastWindowFingerprint === fingerprint) return cloneJson(service.lastResult);
      reject('idempotency_conflict');
    }
    const interruptedIncidents = [];
    if (service.lastWindowAt !== null) {
      const difference = window.atMs - service.lastWindowAt;
      if (difference <= 0) reject('timestamp_not_increasing');
      if (difference < CADENCE_MS) reject('unexpected_subcadence_window');
      if (difference > CADENCE_MS) {
        for (const [metricName, metricState] of service.metrics) {
          const interrupted = interruptMetric(metricState, 'service_window_gap');
          if (interrupted) interruptedIncidents.push({ metric: metricName, ...interrupted });
        }
        service.coincidenceHistory = [];
      }
    }

    const currentSignals = window.metrics
      .filter(item => item.channels.length > 0)
      .map(item => ({ metric: item.metric, atMs: window.atMs }));
    const recentCoincidence = service.coincidenceHistory
      .filter(item => window.atMs - item.atMs <= COINCIDENCE_MS && window.atMs >= item.atMs);
    const coincidenceEvidence = [...recentCoincidence, ...currentSignals];
    const results = [];

    for (const metricInput of window.metrics) {
      if (!service.metrics.has(metricInput.metric)) service.metrics.set(metricInput.metric, newMetricState());
      const metricState = service.metrics.get(metricInput.metric);
      let metricInterruption = null;
      if (metricState.lastObservedAt !== null && window.atMs - metricState.lastObservedAt !== CADENCE_MS) {
        metricInterruption = interruptMetric(metricState, 'metric_observation_gap');
        if (metricInterruption) interruptedIncidents.push({ metric: metricInput.metric, ...metricInterruption });
      }

      const currentRecord = { atMs: window.atMs, channels: metricInput.channels };
      const history = [...metricState.history, currentRecord].slice(-POLICY.persistence_window_count);
      const persistentChannels = metricInput.channels.filter(channel => history
        .filter(record => record.channels.includes(channel)).length >= POLICY.persistence_required_count);
      const hasOtherMetricSignal = metricInput.channels.length > 0
        && coincidenceEvidence.some(item => item.metric !== metricInput.metric
          && window.atMs - item.atMs <= COINCIDENCE_MS);
      const reasons = [];
      if (persistentChannels.length > 0) reasons.push('persistent_same_channel_2_of_3');
      if (hasOtherMetricSignal) reasons.push('cross_metric_coincidence_within_120s');
      const confirmed = metricInput.channels.length > 0 && reasons.length > 0;
      const incident = updateIncident(metricState, metricInput.metric, window.atMs, confirmed);
      metricState.history = history;
      metricState.lastObservedAt = window.atMs;
      results.push({
        metric: metricInput.metric,
        raw_signal_count: metricInput.channels.length,
        confirmed,
        confirmation_reasons: reasons,
        incident_id: metricState.activeIncident?.id ?? incident.incidentClosed,
        incident_started: incident.incidentStarted,
        incident_closed: incident.incidentClosed !== null,
        interrupted_incident: metricInterruption?.incident_id ?? null,
        incident_open: metricState.activeIncident !== null,
        quiet_windows: metricState.quietWindows,
      });
    }

    service.coincidenceHistory = coincidenceEvidence;
    service.lastWindowAt = window.atMs;
    const result = {
      service_id: window.serviceId,
      occurred_at: window.occurredAt,
      interrupted_incidents: interruptedIncidents,
      metrics: results,
    };
    service.lastWindowFingerprint = fingerprint;
    service.lastResult = cloneJson(result);
    return result;
  }

  function getSnapshot() {
    const streams = [];
    let startedIncidents = 0;
    let closedIncidents = 0;
    let interruptedIncidents = 0;
    for (const [serviceId, service] of services) {
      for (const [metricName, metric] of service.metrics) {
        startedIncidents += metric.startedIncidents;
        closedIncidents += metric.closedIncidents;
        interruptedIncidents += metric.interruptedIncidents;
        streams.push({
          service_id: serviceId,
          metric: metricName,
          last_observed_at: metric.lastObservedAt === null ? null : new Date(metric.lastObservedAt).toISOString(),
          active_incident_id: metric.activeIncident?.id ?? null,
          incident_open: metric.activeIncident !== null,
          quiet_windows: metric.quietWindows,
          buffered_observation_count: metric.history.length,
        });
      }
    }
    return {
      policy_version: POLICY.version,
      service_count: services.size,
      stream_count: streams.length,
      started_incidents: startedIncidents,
      closed_incidents: closedIncidents,
      interrupted_incidents: interruptedIncidents,
      open_incidents: streams.filter(stream => stream.incident_open).length,
      streams,
    };
  }

  function getCheckpoint() {
    const savedServices = [...services.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([serviceId, service]) => ({
        service_id: serviceId,
        last_window_at: service.lastWindowAt,
        last_window_fingerprint: service.lastWindowFingerprint,
        last_result: service.lastResult === null ? null : cloneJson(service.lastResult),
        coincidence_history: service.coincidenceHistory.map(item => ({ metric: item.metric, at_ms: item.atMs })),
        metrics: [...service.metrics.entries()]
          .sort(([left], [right]) => left.localeCompare(right))
          .map(([metricName, metric]) => ({
            metric: metricName,
            history: metric.history.map(record => ({ at_ms: record.atMs, channels: [...record.channels] })),
            last_observed_at: metric.lastObservedAt,
            next_incident_number: metric.nextIncidentNumber,
            active_incident: metric.activeIncident === null ? null : {
              id: metric.activeIncident.id,
              metric: metric.activeIncident.metric,
              started_at: metric.activeIncident.startedAt,
            },
            quiet_windows: metric.quietWindows,
            started_incidents: metric.startedIncidents,
            closed_incidents: metric.closedIncidents,
            interrupted_incidents: metric.interruptedIncidents,
          })),
      }));
    return {
      checkpoint_version: POST_DETECTOR_CONFIRMATION_CHECKPOINT_VERSION,
      policy_version: POLICY.version,
      services: savedServices,
    };
  }

  return Object.freeze({ processServiceWindow, getSnapshot, getCheckpoint });
}

export const POST_DETECTOR_CONFIRMATION_POLICY = POLICY;
