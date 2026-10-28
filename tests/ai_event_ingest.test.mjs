import assert from 'node:assert/strict';
import { chmod, lstat, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import {
  EventIngestError,
  ingestText,
  normalizeEvent,
  readInputFile,
  readEventStore,
} from '../scripts/ai_intelligence/event_ingest.mjs';

const SCRIPT_PATH = fileURLToPath(new URL('../scripts/ai_intelligence/event_ingest.mjs', import.meta.url));

const sha = 'a'.repeat(40);
const fixtures = [
  {
    schema_version: 1,
    occurred_at: '2026-10-28T11:10:00+03:00',
    source: 'application',
    kind: 'log',
    severity: 'error',
    data: { stream: 'application', message: 'Synthetic timeout in request handler.' },
  },
  {
    schema_version: 1,
    occurred_at: '2026-10-28T08:12:00Z',
    source: 'operator',
    kind: 'incident',
    severity: 'warning',
    data: { summary: 'Synthetic service interruption.', status: 'open', impact: 'minor' },
  },
  {
    schema_version: 1,
    occurred_at: '2026-10-28T08:14:00Z',
    source: 'github_actions',
    kind: 'ci_result',
    severity: 'error',
    data: { workflow: 'CI', job: 'python-tests', conclusion: 'failure', commit_sha: sha },
  },
  {
    schema_version: 1,
    occurred_at: '2026-10-28T08:15:00Z',
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: { name: 'cpu_percent', value: 23.5, unit: 'percent' },
  },
];

function toJsonl(records) {
  return records.map(record => JSON.stringify(record)).join('\n') + '\n';
}

async function temporaryStore(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-event-ingest-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  return { directory, storePath: path.join(directory, 'events.jsonl') };
}

test('normalizes and locally stores log, incident, CI, and metric events', async t => {
  const { storePath } = await temporaryStore(t);
  const result = await ingestText(toJsonl(fixtures), storePath);
  const events = await readEventStore(storePath);

  assert.deepEqual(result, { accepted: 4, duplicateIgnored: 0 });
  assert.equal(events.length, 4);
  assert.deepEqual(events.map(event => event.kind), ['log', 'incident', 'ci_result', 'server_metric']);
  assert.equal(events[0].occurred_at, '2026-10-28T08:10:00.000Z');
  assert.match(events[0].event_id, /^sha256:[0-9a-f]{64}$/);
  assert.equal(events[2].data.commit_sha, sha);
  assert.equal(events[3].data.value, 23.5);
  assert.equal((await lstat(storePath)).mode & 0o777, 0o600);
  const stored = await readFile(storePath, 'utf8');
  assert.equal(stored.trim().split('\n').length, 4);
});

test('repeated deterministic events are ignored without rewriting the store', async t => {
  const { storePath } = await temporaryStore(t);
  await ingestText(toJsonl([fixtures[0]]), storePath);
  const before = await readFile(storePath);

  assert.deepEqual(await ingestText(toJsonl([fixtures[0]]), storePath), { accepted: 0, duplicateIgnored: 1 });
  assert.deepEqual(await readFile(storePath), before);
});

test('invalid record rejects the entire batch before storage writes', async t => {
  const { storePath } = await temporaryStore(t);
  const invalid = { ...fixtures[1], data: { ...fixtures[1].data, unexpected: 'value' } };

  await assert.rejects(ingestText(toJsonl([fixtures[0], invalid]), storePath), error => {
    assert.ok(error instanceof EventIngestError);
    assert.equal(error.code, 'invalid_data_fields');
    return true;
  });
  await assert.rejects(lstat(storePath), { code: 'ENOENT' });
});

test('rejects malformed, oversized, and duplicate-key JSON without echoing data', async t => {
  const { storePath } = await temporaryStore(t);
  const nestedDuplicate = '{"schema_version":1,"occurred_at":"2026-10-28T08:10:00Z","source":"application","kind":"log","severity":"error","data":{"stream":"application","stream":"stderr","message":"synthetic"}}\n';
  const cases = [
    ['not json\n', 'invalid_json'],
    ['{"schema_version":1,"schema_version":1}\n', 'duplicate_json_key'],
    [nestedDuplicate, 'duplicate_json_key'],
    [' '.repeat(1_048_577), 'input_too_large'],
  ];
  for (const [input, code] of cases) {
    await assert.rejects(ingestText(input, storePath), error => error.code === code);
  }
  await assert.rejects(lstat(storePath), { code: 'ENOENT' });
});

test('rejects unknown fields, invalid source-kind combinations, and invalid timestamps', () => {
  assert.throws(() => normalizeEvent({ ...fixtures[0], private_ref: 'synthetic' }), { code: 'invalid_event_fields' });
  assert.throws(() => normalizeEvent({ ...fixtures[2], source: 'server' }), { code: 'source_kind_mismatch' });
  assert.throws(() => normalizeEvent({ ...fixtures[0], occurred_at: '2026-10-28T08:00:00' }), { code: 'invalid_timestamp' });
});

test('rejects common sensitive-looking text locally and does not echo values', async t => {
  const { storePath } = await temporaryStore(t);
  const markers = [
    'Authorization: Bearer synthetic-placeholder-token',
    'Contact synthetic.user@example.test',
    'Review https://example.invalid/private',
    'Git remote git@example.invalid:sample/repo.git',
    'Phone: +000 000 0000',
  ];
  for (const marker of markers) {
    const record = { ...fixtures[0], data: { ...fixtures[0].data, message: marker } };
    await assert.rejects(ingestText(toJsonl([record]), storePath), error => {
      assert.equal(error.code, 'sensitive_text_rejected');
      assert.equal(error.message.includes(marker), false);
      return true;
    });
  }
  await assert.rejects(lstat(storePath), { code: 'ENOENT' });
});

test('rejects symlinked input store paths and malformed existing storage', async t => {
  const { directory, storePath } = await temporaryStore(t);
  const targetPath = path.join(directory, 'target.jsonl');
  await writeFile(targetPath, '');
  const linkPath = path.join(directory, 'linked.jsonl');
  await symlink(targetPath, linkPath);
  await assert.rejects(readInputFile(linkPath), { code: 'unsafe_path' });
  await assert.rejects(ingestText(toJsonl([fixtures[0]]), linkPath), { code: 'unsafe_store_path' });

  await writeFile(storePath, '{broken}\n');
  await chmod(storePath, 0o600);
  await assert.rejects(readEventStore(storePath), { code: 'invalid_store' });
});

test('rejects an active writer lock instead of racing concurrent appends', async t => {
  const { directory, storePath } = await temporaryStore(t);
  const lockPath = `${storePath}.lock`;
  await writeFile(lockPath, '');

  await assert.rejects(ingestText(toJsonl([fixtures[0]]), storePath), { code: 'store_locked' });
  await assert.rejects(lstat(storePath), { code: 'ENOENT' });
});

test('offline CLI stores synthetic records and prints counts without event content or paths', async t => {
  const { directory, storePath } = await temporaryStore(t);
  const inputPath = path.join(directory, 'input.jsonl');
  await writeFile(inputPath, toJsonl([fixtures[0]]), 'utf8');
  const result = spawnSync(process.execPath, [SCRIPT_PATH, '--input', inputPath, '--store', storePath], {
    cwd: path.resolve(path.dirname(SCRIPT_PATH), '../..'),
    env: { PATH: process.env.PATH ?? '' },
    encoding: 'utf8',
    timeout: 10_000,
  });

  assert.equal(result.status, 0);
  assert.equal(result.stderr, '');
  assert.deepEqual(JSON.parse(result.stdout), { schema_version: 1, accepted: 1, duplicateIgnored: 0 });
  assert.equal(result.stdout.includes(fixtures[0].data.message), false);
  assert.equal(result.stdout.includes(storePath), false);
  assert.equal((await readEventStore(storePath)).length, 1);
});
