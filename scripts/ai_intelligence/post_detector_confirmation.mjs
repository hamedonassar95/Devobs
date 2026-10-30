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
export function createPostDetectorConfirmationLayer() {
  const services = new Map();

  function serviceState(serviceId) {
    if (!services.has(serviceId)) {
      services.set(serviceId, {
        lastWindowAt: null,
        coincidenceHistory: [],
        metrics: new Map(),
      });
    }
    return services.get(serviceId);
  }

  function processServiceWindow(input) {
    const window = validateWindow(input);
    const service = serviceState(window.serviceId);
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
    return {
      service_id: window.serviceId,
      occurred_at: window.occurredAt,
      interrupted_incidents: interruptedIncidents,
      metrics: results,
    };
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

  return Object.freeze({ processServiceWindow, getSnapshot });
}

export const POST_DETECTOR_CONFIRMATION_POLICY = POLICY;
