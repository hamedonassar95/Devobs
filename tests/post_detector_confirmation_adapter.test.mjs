import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { normalizeEvent } from '../scripts/ai_intelligence/event_ingest.mjs';
import { createPostDetectorConfirmationLayer } from '../scripts/ai_intelligence/post_detector_confirmation.mjs';
import { createPostDetectorConfirmationJournal } from '../scripts/ai_intelligence/post_detector_confirmation_journal.mjs';
import {
  createDetectorConfirmationAdapter,
  POST_DETECTOR_CONFIRMATION_ADAPTER_VERSION,
} from '../scripts/ai_intelligence/post_detector_confirmation_adapter.mjs';

const BASE_TIME = Date.parse('2027-03-01T00:00:00.000Z');
const at = minute => new Date(BASE_TIME + minute * 60_000).toISOString();
const UNITS = Object.freeze({ cpu_percent: 'percent', latency_ms: 'milliseconds' });

function metricEvent(name, value, minute) {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: at(minute),
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: { name, value, unit: UNITS[name] },
  });
}

function history(name, values) {
  return values.map((value, minute) => metricEvent(name, value, minute));
}

function input(serviceId, minute, events) {
  return { serviceId, occurredAt: at(minute), events };
}

const allowService = async ({ serviceId }) => serviceId === 'service-a';

test('an isolated real detector signal remains unconfirmed by the composed layer', async () => {
  const confirmationLayer = createPostDetectorConfirmationLayer();
  const adapter = createDetectorConfirmationAdapter({ confirmationLayer, authorizeService: allowService });
  const events = history('cpu_percent', [20, 20, 20, 20, 20, 20, 60]);
  const result = await adapter.processEventWindow(input('service-a', 6, events));

  assert.equal(result.adapter_version, POST_DETECTOR_CONFIRMATION_ADAPTER_VERSION);
  assert.equal(result.confirmation_policy_version, 'ai9-post-detector-confirmation-v1');
  assert.equal(result.confirmation_output.metrics[0].raw_signal_count > 0, true);
  assert.equal(result.confirmation_output.metrics[0].confirmed, false);
  assert.equal(result.confirmation_output.metrics[0].incident_open, false);
  assert.equal(confirmationLayer.getSnapshot().open_incidents, 0);
});

test('persistent detector output starts one journaled incident without persisting metric values', async t => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-ai9-adapter-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const filePath = path.join(directory, 'journal.json');
  const journal = createPostDetectorConfirmationJournal({ filePath });
  const adapter = createDetectorConfirmationAdapter({
    confirmationLayer: journal,
    authorizeService: allowService,
  });
  const events = history('cpu_percent', [20, 20, 20, 20, 20, 20, 60, 60]);

  for (let minute = 0; minute < 7; minute++) {
    await adapter.processEventWindow(input('service-a', minute, events.slice(0, minute + 1)));
  }
  const started = await adapter.processEventWindow(input('service-a', 7, events));
  assert.equal(started.confirmation_output.result.metrics[0].incident_started, true);
  assert.equal(started.confirmation_output.queued_events.length, 1);

  const pendingBeforeAck = await journal.listPendingEvents({ limit: 10 });
  assert.equal(pendingBeforeAck.length, 1);
  assert.equal(pendingBeforeAck[0].event_type, 'incident_started');
  const document = JSON.parse(await readFile(filePath, 'utf8'));
  assert.equal(JSON.stringify(document).includes('"value"'), false);
  assert.equal(JSON.stringify(document).includes('"detectors"'), false);

  await journal.acknowledgeEvents([pendingBeforeAck[0].event_id]);
  const replay = await adapter.processEventWindow(input('service-a', 7, events));
  assert.deepEqual(replay.confirmation_output.result, started.confirmation_output.result);
  assert.deepEqual(replay.confirmation_output.queued_events, []);
  assert.deepEqual(await journal.listPendingEvents({ limit: 10 }), []);
});

test('simultaneous detector signals on distinct metrics reach confirmation as one aligned window', async () => {
  const confirmationLayer = createPostDetectorConfirmationLayer();
  const adapter = createDetectorConfirmationAdapter({ confirmationLayer, authorizeService: allowService });
  const events = [
    ...history('cpu_percent', [20, 20, 20, 20, 20, 20, 60]),
    ...history('latency_ms', [100, 100, 100, 100, 100, 100, 500]),
  ];
  const result = await adapter.processEventWindow(input('service-a', 6, events));

  assert.equal(result.confirmation_output.metrics.length, 2);
  assert.ok(result.confirmation_output.metrics.every(metric => metric.confirmed));
  assert.ok(result.confirmation_output.metrics.every(metric =>
    metric.confirmation_reasons.includes('cross_metric_coincidence_within_120s')));
});

test('misaligned metric observations fail before confirmation state changes', async () => {
  const confirmationLayer = createPostDetectorConfirmationLayer();
  const adapter = createDetectorConfirmationAdapter({ confirmationLayer, authorizeService: allowService });
  const before = confirmationLayer.getCheckpoint();

  await assert.rejects(async () => adapter.processEventWindow(input(
    'service-a',
    1,
    history('cpu_percent', [20, 20, 20, 20, 20, 30]),
  )), { code: 'misaligned_metric_window' });
  assert.deepEqual(confirmationLayer.getCheckpoint(), before);
});

test('non-metric, duplicate, empty, and non-canonical inputs fail closed', async () => {
  const confirmationLayer = createPostDetectorConfirmationLayer();
  const adapter = createDetectorConfirmationAdapter({ confirmationLayer, authorizeService: allowService });
  const valid = metricEvent('cpu_percent', 20, 0);
  const nonMetric = normalizeEvent({
    schema_version: 1,
    occurred_at: at(0),
    source: 'operator',
    kind: 'incident',
    severity: 'warning',
    data: { summary: 'Synthetic incident', status: 'open', impact: 'minor' },
  });

  await assert.rejects(async () => adapter.processEventWindow(input('service-a', 0, [nonMetric])), {
    code: 'metric_event_required',
  });
  await assert.rejects(async () => adapter.processEventWindow(input('service-a', 0, [valid, valid])), {
    code: 'duplicate_event_id',
  });
  await assert.rejects(async () => adapter.processEventWindow(input('service-a', 0, [])), {
    code: 'invalid_metric_event_batch',
  });
  await assert.rejects(async () => adapter.processEventWindow({
    serviceId: 'service-a',
    occurredAt: '2027-03-01T00:00:00Z',
    events: [valid],
  }), { code: 'invalid_timestamp' });
  assert.deepEqual(confirmationLayer.getSnapshot().service_count, 0);
});

test('authorization runs before metric parsing and receives only an immutable service ID', async () => {
  const confirmationLayer = createPostDetectorConfirmationLayer();
  let received;
  const adapter = createDetectorConfirmationAdapter({
    confirmationLayer,
    authorizeService: async scope => {
      received = scope;
      return false;
    },
  });

  await assert.rejects(async () => adapter.processEventWindow({
    serviceId: 'service-a',
    occurredAt: 'not-a-timestamp',
    events: { malformed: true },
  }), { code: 'service_not_authorized' });
  assert.deepEqual(Object.keys(received), ['serviceId']);
  assert.deepEqual(received, { serviceId: 'service-a' });
  assert.equal(Object.isFrozen(received), true);
  assert.equal(confirmationLayer.getSnapshot().service_count, 0);
});

test('non-boolean and throwing authorization decisions fail closed without leaking errors', async () => {
  const confirmationLayer = createPostDetectorConfirmationLayer();
  const nonBoolean = createDetectorConfirmationAdapter({
    confirmationLayer,
    authorizeService: () => 1,
  });
  await assert.rejects(async () => nonBoolean.processEventWindow(
    input('service-a', 0, [metricEvent('cpu_percent', 20, 0)]),
  ), { code: 'service_not_authorized' });

  const throwing = createDetectorConfirmationAdapter({
    confirmationLayer,
    authorizeService: () => { throw new Error('synthetic private callback detail'); },
  });
  await assert.rejects(async () => throwing.processEventWindow(
    input('service-a', 0, [metricEvent('cpu_percent', 20, 0)]),
  ), error => error.code === 'service_authorization_failed'
    && error.message === 'service_authorization_failed'
    && !error.message.includes('private'));
  assert.equal(confirmationLayer.getSnapshot().service_count, 0);
});

test('adapter and confirmation construction reject ambiguous dependencies and options', () => {
  assert.throws(() => createDetectorConfirmationAdapter(), { code: 'invalid_adapter_options' });
  assert.throws(() => createDetectorConfirmationAdapter({
    confirmationLayer: createPostDetectorConfirmationLayer(),
  }), { code: 'invalid_adapter_options' });
  assert.throws(() => createDetectorConfirmationAdapter({
    confirmationLayer: {},
    authorizeService: allowService,
  }), {
    code: 'invalid_confirmation_implementation',
  });
  assert.throws(() => createDetectorConfirmationAdapter({
    confirmationLayer: createPostDetectorConfirmationLayer(),
    authorizeService: true,
  }), { code: 'invalid_service_authorizer' });
  assert.throws(() => createDetectorConfirmationAdapter({
    confirmationLayer: createPostDetectorConfirmationLayer(),
    authorizeService: allowService,
    unused: true,
  }), { code: 'invalid_adapter_options' });
});
