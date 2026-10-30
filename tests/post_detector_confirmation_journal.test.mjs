import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile, chmod, symlink } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {
  createPostDetectorConfirmationJournal,
  POST_DETECTOR_CONFIRMATION_JOURNAL_VERSION,
} from '../scripts/ai_intelligence/post_detector_confirmation_journal.mjs';

const BASE = Date.parse('2027-01-01T00:00:00.000Z');
const at = index => new Date(BASE + index * 60_000).toISOString();
const window = (index, channels = ['z_score']) => ({
  serviceId: 'service-a',
  occurredAt: at(index),
  metrics: [{ metric: 'cpu_percent', channels }],
});

async function withJournal(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-ai9-journal-'));
  const filePath = path.join(directory, 'journal.json');
  try {
    await run({ directory, filePath, journal: createPostDetectorConfirmationJournal({ filePath }) });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test('checkpoint and incident outbox survive journal reconstruction and share the same commit', async () => {
  await withJournal(async ({ filePath, journal }) => {
    assert.deepEqual(await journal.listPendingEvents(), []);
    await journal.processServiceWindow(window(0));
    const started = await journal.processServiceWindow(window(1));
    assert.equal(started.queued_events.length, 1);
    assert.equal(started.queued_events[0].event_type, 'incident_started');
    assert.equal(started.queued_events[0].metric, 'cpu_percent');
    assert.equal(Object.hasOwn(started.queued_events[0], 'channels'), false);

    const restored = createPostDetectorConfirmationJournal({ filePath });
    const pending = await restored.listPendingEvents();
    assert.deepEqual(pending, started.queued_events);
    const firstQuiet = await restored.processServiceWindow(window(2, []));
    const secondQuiet = await restored.processServiceWindow(window(3, []));
    assert.equal(firstQuiet.result.metrics[0].incident_open, true);
    assert.equal(secondQuiet.result.metrics[0].incident_closed, true);
    assert.equal(secondQuiet.queued_events[0].event_type, 'incident_closed');
    assert.equal(secondQuiet.queued_events[0].incident_id, pending[0].incident_id);
    assert.equal((await restored.listPendingEvents()).length, 2);
  });
});

test('event identifiers are deterministic for the same synthetic transitions', async () => {
  const eventIds = [];
  for (let run = 0; run < 2; run++) {
    await withJournal(async ({ journal }) => {
      await journal.processServiceWindow(window(0));
      const result = await journal.processServiceWindow(window(1));
      eventIds.push(result.queued_events[0].event_id);
    });
  }
  assert.equal(eventIds[0], eventIds[1]);
});

test('an exact retry does not duplicate or resurrect an acknowledged event', async () => {
  await withJournal(async ({ filePath, journal }) => {
    await journal.processServiceWindow(window(0));
    const accepted = await journal.processServiceWindow(window(1));
    const id = accepted.queued_events[0].event_id;
    const retryWhilePending = await journal.processServiceWindow(window(1));
    assert.deepEqual(retryWhilePending.queued_events, []);
    assert.equal((await journal.listPendingEvents()).length, 1);
    assert.deepEqual(await journal.acknowledgeEvents([id]), { acknowledged_count: 1 });
    assert.deepEqual(await journal.acknowledgeEvents([id]), { acknowledged_count: 0 });

    const restored = createPostDetectorConfirmationJournal({ filePath });
    const retry = await restored.processServiceWindow(window(1));
    assert.equal(retry.result.metrics[0].incident_started, true);
    assert.deepEqual(retry.queued_events, []);
    assert.deepEqual(await restored.listPendingEvents(), []);
  });
});

test('interrupted incidents create a distinct outbox event with a fixed reason', async () => {
  await withJournal(async ({ journal }) => {
    await journal.processServiceWindow(window(0));
    await journal.processServiceWindow(window(1));
    const interrupted = await journal.processServiceWindow(window(3, []));
    assert.equal(interrupted.queued_events.length, 1);
    assert.equal(interrupted.queued_events[0].event_type, 'incident_interrupted');
    assert.equal(interrupted.queued_events[0].reason, 'service_window_gap');
  });
});

test('invalid or conflicting input leaves the previous checkpoint and outbox bytes unchanged', async () => {
  await withJournal(async ({ filePath, journal }) => {
    await journal.processServiceWindow(window(0));
    await journal.processServiceWindow(window(1));
    const before = await readFile(filePath);
    await assert.rejects(journal.processServiceWindow({ ...window(1), metrics: [] }), {
      code: 'idempotency_conflict',
    });
    await assert.rejects(journal.processServiceWindow(window(0)), {
      code: 'timestamp_not_increasing',
    });
    await assert.rejects(journal.processServiceWindow({ ...window(2), metrics: [{ metric: '', channels: [] }] }), {
      code: 'invalid_metric',
    });
    assert.deepEqual(await readFile(filePath), before);
  });
});

test('an existing exclusive lock fails closed without modifying the journal', async () => {
  await withJournal(async ({ filePath, journal }) => {
    await journal.processServiceWindow(window(0));
    const before = await readFile(filePath);
    await writeFile(`${filePath}.lock`, 'synthetic active writer\n', { mode: 0o600, flag: 'wx' });
    await assert.rejects(journal.processServiceWindow(window(1)), { code: 'journal_locked' });
    assert.deepEqual(await readFile(filePath), before);
  });
});

test('insecure permissions, symlinks, and malformed journal documents are refused', async () => {
  await withJournal(async ({ directory, filePath, journal }) => {
    await journal.processServiceWindow(window(0));
    await chmod(filePath, 0o644);
    await assert.rejects(journal.listPendingEvents(), { code: 'unsafe_journal_permissions' });
    await chmod(filePath, 0o600);
    await rm(filePath);
    await symlink(path.join(directory, 'missing-target'), filePath);
    await assert.rejects(journal.listPendingEvents(), { code: 'unsafe_journal_file' });
    await rm(filePath);
    await writeFile(filePath, '{not-json', { mode: 0o600 });
    await assert.rejects(journal.listPendingEvents(), { code: 'invalid_journal_document' });
  });
});

test('acknowledgement and list limits reject malformed callers', async () => {
  await withJournal(async ({ journal }) => {
    await assert.rejects(journal.listPendingEvents({ limit: 0 }), { code: 'invalid_outbox_limit' });
    await assert.rejects(journal.acknowledgeEvents(['not-a-sha']), {
      code: 'invalid_outbox_acknowledgement',
    });
    await assert.rejects(journal.acknowledgeEvents(['a'.repeat(64), 'a'.repeat(64)]), {
      code: 'invalid_outbox_acknowledgement',
    });
    assert.equal(POST_DETECTOR_CONFIRMATION_JOURNAL_VERSION, 'ai9-confirmation-journal-v1');
  });
});

test('directories must already be canonical, private, and writable by the caller', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-ai9-public-dir-'));
  const filePath = path.join(directory, 'journal.json');
  try {
    await chmod(directory, 0o755);
    const journal = createPostDetectorConfirmationJournal({ filePath });
    await assert.rejects(journal.listPendingEvents(), { code: 'unsafe_journal_directory' });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('oversized journal files and excessive pending outbox counts fail closed', async () => {
  await withJournal(async ({ filePath, journal }) => {
    await writeFile(filePath, Buffer.alloc(8 * 1024 * 1024 + 1, 0x20), { mode: 0o600 });
    await assert.rejects(journal.listPendingEvents(), { code: 'journal_size_limit' });
    await writeFile(filePath, JSON.stringify({
      journal_version: 'ai9-confirmation-journal-v1',
      checkpoint: {},
      outbox_events: Array.from({ length: 10_001 }, () => ({})),
    }), { mode: 0o600 });
    await assert.rejects(journal.listPendingEvents(), { code: 'invalid_journal_document' });
  });
});
