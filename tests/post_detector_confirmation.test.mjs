import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createPostDetectorConfirmationLayer,
  POST_DETECTOR_CONFIRMATION_POLICY,
} from '../scripts/ai_intelligence/post_detector_confirmation.mjs';

const timestamp = index => new Date(Date.parse('2027-01-01T00:00:00.000Z') + index * 60_000).toISOString();

function window(index, metrics, serviceId = 'service-a') {
  return { serviceId, occurredAt: timestamp(index), metrics };
}

test('one isolated detector warning does not become a final alert', () => {
  const layer = createPostDetectorConfirmationLayer();
  const result = layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['z_score'] }]));

  assert.equal(result.metrics[0].confirmed, false);
  assert.deepEqual(result.metrics[0].confirmation_reasons, []);
  assert.equal(result.metrics[0].incident_open, false);
});

test('two detector channels on one metric are not treated as independent confirmation', () => {
  const layer = createPostDetectorConfirmationLayer();
  const result = layer.processServiceWindow(window(0, [
    { metric: 'cpu_percent', channels: ['z_score', 'ewma'] },
  ]));

  assert.equal(result.metrics[0].confirmed, false);
  assert.equal(result.metrics[0].incident_open, false);
});

test('the same channel persisting in two of three observed windows confirms', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['z_score'] }]));
  const result = layer.processServiceWindow(window(1, [{ metric: 'cpu_percent', channels: ['z_score'] }]));

  assert.equal(result.metrics[0].confirmed, true);
  assert.deepEqual(result.metrics[0].confirmation_reasons, ['persistent_same_channel_2_of_3']);
  assert.equal(result.metrics[0].incident_started, true);
  assert.equal(layer.getSnapshot().open_incidents, 1);
});

test('signals from two distinct metrics in one service can confirm within 120 seconds', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['z_score'] }]));
  const result = layer.processServiceWindow(window(1, [
    { metric: 'cpu_percent', channels: [] },
    { metric: 'latency_ms', channels: ['ewma'] },
  ]));
  const latency = result.metrics.find(metric => metric.metric === 'latency_ms');

  assert.equal(latency.confirmed, true);
  assert.deepEqual(latency.confirmation_reasons, ['cross_metric_coincidence_within_120s']);
  assert.equal(latency.incident_started, true);
});

test('cross-metric coincidence includes the exact 120-second boundary', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['z_score'] }]));
  layer.processServiceWindow(window(1, [{ metric: 'latency_ms', channels: [] }]));
  const atBoundary = layer.processServiceWindow(window(2, [
    { metric: 'latency_ms', channels: ['ewma'] },
  ]));

  assert.equal(atBoundary.metrics[0].confirmed, true);
  assert.ok(atBoundary.metrics[0].confirmation_reasons.includes('cross_metric_coincidence_within_120s'));
});

test('same-timestamp signals in one service window support cross-metric coincidence', () => {
  const layer = createPostDetectorConfirmationLayer();
  const result = layer.processServiceWindow(window(0, [
    { metric: 'cpu_percent', channels: ['moving_average'] },
    { metric: 'latency_ms', channels: ['ewma'] },
  ]));

  assert.ok(result.metrics.every(metric => metric.confirmed));
  assert.ok(result.metrics.every(metric => metric.confirmation_reasons.includes('cross_metric_coincidence_within_120s')));
});

test('two quiet observed windows close an incident without filling alert windows', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['z_score'] }]));
  const start = layer.processServiceWindow(window(1, [{ metric: 'cpu_percent', channels: ['z_score'] }]));
  const firstQuiet = layer.processServiceWindow(window(2, [{ metric: 'cpu_percent', channels: [] }]));
  const secondQuiet = layer.processServiceWindow(window(3, [{ metric: 'cpu_percent', channels: [] }]));

  assert.equal(start.metrics[0].incident_started, true);
  assert.equal(firstQuiet.metrics[0].incident_open, true);
  assert.equal(firstQuiet.metrics[0].quiet_windows, 1);
  assert.equal(secondQuiet.metrics[0].incident_closed, true);
  assert.equal(secondQuiet.metrics[0].confirmed, false);
  assert.equal(layer.getSnapshot().closed_incidents, 1);
  assert.equal(layer.getSnapshot().open_incidents, 0);
});

test('missing metric observations do not count as quiet or as persistence windows', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['ewma'] }]));
  layer.processServiceWindow(window(1, []));
  const returned = layer.processServiceWindow(window(2, [{ metric: 'cpu_percent', channels: ['ewma'] }]));

  assert.equal(returned.metrics[0].confirmed, false);
  assert.equal(returned.metrics[0].incident_open, false);
});

test('a missing metric does not close an open incident and interrupts it on return', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['ewma'] }]));
  const started = layer.processServiceWindow(window(1, [{ metric: 'cpu_percent', channels: ['ewma'] }]));
  layer.processServiceWindow(window(2, []));
  assert.equal(layer.getSnapshot().open_incidents, 1);
  const returned = layer.processServiceWindow(window(3, [{ metric: 'cpu_percent', channels: [] }]));

  assert.equal(returned.interrupted_incidents.length, 1);
  assert.equal(returned.metrics[0].incident_open, false);
  assert.equal(layer.getSnapshot().interrupted_incidents, 1);
  assert.equal(started.metrics[0].incident_started, true);
});

test('service time gaps interrupt open incidents and reset evidence', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['ewma'] }]));
  layer.processServiceWindow(window(1, [{ metric: 'cpu_percent', channels: ['ewma'] }]));
  const afterGap = layer.processServiceWindow(window(3, [{ metric: 'cpu_percent', channels: ['ewma'] }]));

  assert.equal(afterGap.metrics[0].confirmed, false);
  assert.equal(afterGap.metrics[0].incident_open, false);
  assert.equal(afterGap.interrupted_incidents.length, 1);
  assert.equal(layer.getSnapshot().interrupted_incidents, 1);
});

test('duplicate, out-of-order, and sub-cadence windows fail closed', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(1, []));
  assert.throws(() => layer.processServiceWindow(window(1, [])), { code: 'timestamp_not_increasing' });
  assert.throws(() => layer.processServiceWindow(window(0, [])), { code: 'timestamp_not_increasing' });
  assert.throws(() => layer.processServiceWindow({
    serviceId: 'service-a',
    occurredAt: new Date(Date.parse(timestamp(1)) + 30_000).toISOString(),
    metrics: [],
  }), { code: 'unexpected_subcadence_window' });
});

test('invalid or duplicated metric/channel inputs are rejected', () => {
  const layer = createPostDetectorConfirmationLayer();
  assert.throws(() => layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['unknown'] }])), {
    code: 'unsupported_channel',
  });
  assert.throws(() => layer.processServiceWindow(window(0, [
    { metric: 'cpu_percent', channels: [] },
    { metric: 'cpu_percent', channels: [] },
  ])), { code: 'duplicate_metric_in_service_window' });
});

test('policy records the preregistered temporal parameters', () => {
  assert.equal(POST_DETECTOR_CONFIRMATION_POLICY.version, 'ai9-post-detector-confirmation-v1');
  assert.equal(POST_DETECTOR_CONFIRMATION_POLICY.coincidence_window_seconds, 120);
  assert.equal(POST_DETECTOR_CONFIRMATION_POLICY.persistence_required_count, 2);
  assert.equal(POST_DETECTOR_CONFIRMATION_POLICY.persistence_window_count, 3);
  assert.equal(POST_DETECTOR_CONFIRMATION_POLICY.quiet_windows_to_close, 2);
});
