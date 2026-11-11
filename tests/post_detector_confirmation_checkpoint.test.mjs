import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createPostDetectorConfirmationLayer,
  POST_DETECTOR_CONFIRMATION_CHECKPOINT_VERSION,
  POST_DETECTOR_CONFIRMATION_POLICY,
} from '../scripts/ai_intelligence/post_detector_confirmation.mjs';

const timestamp = index => new Date(Date.parse('2027-01-01T00:00:00.000Z') + index * 60_000).toISOString();

function window(index, metrics, serviceId = 'service-a') {
  return { serviceId, occurredAt: timestamp(index), metrics };
}

test('exact retry of the latest service window returns its prior result without changing state', () => {
  const layer = createPostDetectorConfirmationLayer();
  const input = window(0, [{ metric: 'cpu_percent', channels: ['ewma'] }]);
  const first = layer.processServiceWindow(input);
  const beforeRetry = layer.getCheckpoint();
  first.metrics[0].confirmed = true;

  const retry = layer.processServiceWindow(input);

  assert.equal(retry.metrics[0].confirmed, false);
  assert.deepEqual(layer.getCheckpoint(), beforeRetry);
});

test('same service timestamp with a different payload fails closed', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['ewma'] }]));

  assert.throws(
    () => layer.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['z_score'] }])),
    { code: 'idempotency_conflict' },
  );
});

test('checkpoint JSON restore preserves incidents and next-window behavior', () => {
  const uninterrupted = createPostDetectorConfirmationLayer();
  uninterrupted.processServiceWindow(window(0, [
    { metric: 'cpu_percent', channels: ['ewma'] },
    { metric: 'latency_ms', channels: [] },
  ]));
  uninterrupted.processServiceWindow(window(1, [
    { metric: 'cpu_percent', channels: ['ewma'] },
    { metric: 'latency_ms', channels: ['z_score'] },
  ]));

  const encoded = JSON.stringify(uninterrupted.getCheckpoint());
  const restored = createPostDetectorConfirmationLayer({ checkpoint: JSON.parse(encoded) });
  assert.deepEqual(restored.getSnapshot(), uninterrupted.getSnapshot());

  const nextWindow = window(2, [
    { metric: 'cpu_percent', channels: [] },
    { metric: 'latency_ms', channels: [] },
  ]);
  assert.deepEqual(restored.processServiceWindow(nextWindow), uninterrupted.processServiceWindow(nextWindow));
  assert.deepEqual(restored.getCheckpoint(), uninterrupted.getCheckpoint());
});

test('restored checkpoint makes the last accepted window retry idempotently', () => {
  const original = createPostDetectorConfirmationLayer();
  const input = window(0, [{ metric: 'cpu_percent', channels: ['ewma'] }]);
  const result = original.processServiceWindow(input);
  const restored = createPostDetectorConfirmationLayer({
    checkpoint: JSON.parse(JSON.stringify(original.getCheckpoint())),
  });

  assert.deepEqual(restored.processServiceWindow(input), result);
  assert.deepEqual(restored.getCheckpoint(), original.getCheckpoint());
});

test('checkpoint version and confirmation policy must match exactly', () => {
  const source = createPostDetectorConfirmationLayer();
  const empty = source.getCheckpoint();

  assert.equal(empty.checkpoint_version, POST_DETECTOR_CONFIRMATION_CHECKPOINT_VERSION);
  assert.equal(empty.policy_version, POST_DETECTOR_CONFIRMATION_POLICY.version);
  assert.throws(() => createPostDetectorConfirmationLayer({
    checkpoint: { ...empty, checkpoint_version: 'future-version' },
  }), { code: 'unsupported_checkpoint_version' });
  assert.throws(() => createPostDetectorConfirmationLayer({
    checkpoint: { ...empty, policy_version: 'different-policy' },
  }), { code: 'checkpoint_policy_mismatch' });
  assert.throws(() => createPostDetectorConfirmationLayer({
    checkpoint: { ...empty, services: null },
  }), { code: 'invalid_checkpoint' });
});

test('malformed checkpoint state and cached results are rejected before restore', () => {
  const source = createPostDetectorConfirmationLayer();
  source.processServiceWindow(window(0, [{ metric: 'cpu_percent', channels: ['ewma'] }]));
  const checkpoint = JSON.parse(JSON.stringify(source.getCheckpoint()));
  checkpoint.services[0].metrics[0].history[0].channels = ['not-a-detector'];

  assert.throws(() => createPostDetectorConfirmationLayer({ checkpoint }), { code: 'invalid_checkpoint' });
});

test('checkpoint service and metric ordering is deterministic', () => {
  const layer = createPostDetectorConfirmationLayer();
  layer.processServiceWindow(window(0, [
    { metric: 'latency_ms', channels: [] },
    { metric: 'cpu_percent', channels: [] },
  ], 'service-z'));
  layer.processServiceWindow(window(0, [{ metric: 'error_rate', channels: [] }], 'service-a'));

  const checkpoint = layer.getCheckpoint();
  assert.deepEqual(checkpoint.services.map(service => service.service_id), ['service-a', 'service-z']);
  assert.deepEqual(checkpoint.services[1].metrics.map(metric => metric.metric), ['cpu_percent', 'latency_ms']);
});
