import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { readEventStore } from '../scripts/ai_intelligence/event_ingest.mjs';
import {
  dispatchToAiEvent,
  DISPATCH_ACTION,
  SOURCE_REPOSITORY,
  SOURCE_WORKFLOW,
} from '../scripts/ai_intelligence/repository_dispatch_event.mjs';

const ROOT = path.resolve(import.meta.dirname, '..');
const sha = 'b'.repeat(40);
const validDispatch = () => ({
  action: DISPATCH_ACTION,
  client_payload: {
    source_repository: SOURCE_REPOSITORY,
    source_branch: 'main',
    source_sha: sha,
    source_run_id: 123456,
    source_run_attempt: 1,
    source_workflow: SOURCE_WORKFLOW,
    source_conclusion: 'success',
    source_event: 'push',
  },
});

test('approved dispatch becomes a synthetic CI metadata event', () => {
  const event = dispatchToAiEvent(validDispatch(), '2026-11-06T00:00:00Z');
  const { event_id, ...record } = event;
  assert.deepEqual(record, {
    schema_version: 1,
    occurred_at: '2026-11-06T00:00:00.000Z',
    source: 'github_actions',
    kind: 'ci_result',
    severity: 'info',
    data: {
      workflow: SOURCE_WORKFLOW,
      job: 'build-and-validate',
      conclusion: 'success',
      commit_sha: sha,
    },
  });
  assert.match(event_id, /^sha256:[0-9a-f]{64}$/);
});

test('dispatch rejects wrong action, extra fields, and out-of-scope source metadata', () => {
  assert.throws(() => dispatchToAiEvent({ ...validDispatch(), action: 'other' }), { code: 'invalid_repository_dispatch' });
  assert.throws(() => dispatchToAiEvent({
    ...validDispatch(), client_payload: { ...validDispatch().client_payload, incident_log: 'must not pass' },
  }), { code: 'invalid_repository_dispatch_fields' });

  for (const changes of [
    { source_repository: 'someone/other' },
    { source_branch: 'feature/private' },
    { source_conclusion: 'failure' },
    { source_event: 'pull_request' },
    { source_run_id: 0 },
    { source_run_attempt: -1 },
    { source_sha: 'invalid' },
  ]) {
    assert.throws(() => dispatchToAiEvent({
      ...validDispatch(), client_payload: { ...validDispatch().client_payload, ...changes },
    }), { code: 'repository_dispatch_out_of_scope' });
  }
});

test('receiver CLI validates and ingests only bounded CI metadata locally', async t => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-dispatch-contract-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const inputPath = path.join(directory, 'dispatch.json');
  const storePath = path.join(directory, 'events.jsonl');
  await writeFile(inputPath, JSON.stringify(validDispatch()), 'utf8');

  const env = { PATH: process.env.PATH ?? '' };
  const parsed = spawnSync(process.execPath, [
    path.join(ROOT, 'scripts/ai_intelligence/repository_dispatch_event.mjs'), inputPath,
  ], { cwd: ROOT, env, encoding: 'utf8', timeout: 10_000 });

  assert.equal(parsed.status, 0, parsed.stderr);
  assert.equal(parsed.stderr, '');
  assert.equal(parsed.stdout.includes('client_payload'), false);
  const ingested = spawnSync(process.execPath, [
    path.join(ROOT, 'scripts/ai_intelligence/event_ingest.mjs'),
    '--input', '-', '--store', storePath,
  ], { cwd: ROOT, env, input: parsed.stdout, encoding: 'utf8', timeout: 10_000 });

  assert.equal(ingested.status, 0, ingested.stderr);
  assert.equal(ingested.stderr, '');
  assert.deepEqual(JSON.parse(ingested.stdout), {
    schema_version: 1,
    accepted: 1,
    duplicateIgnored: 0,
  });
  const events = await readEventStore(storePath);
  assert.equal(events.length, 1);
  assert.equal(events[0].source, 'github_actions');
  assert.equal(events[0].kind, 'ci_result');
  assert.equal(events[0].severity, 'info');
  assert.deepEqual(events[0].data, {
    workflow: SOURCE_WORKFLOW,
    job: 'build-and-validate',
    conclusion: 'success',
    commit_sha: sha,
  });
  const storedText = await readFile(storePath, 'utf8');
  assert.equal(storedText.includes('incident_log'), false);
  assert.equal(storedText.includes('Authorization'), false);
});
