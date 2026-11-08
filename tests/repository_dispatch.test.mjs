import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  classifyDispatchError,
  createDispatchBody,
  DISPATCH_EVENT_TYPE,
  prepareDispatchPayload,
  SOURCE_REPOSITORY,
  SOURCE_WORKFLOW,
  TARGET_REPOSITORY,
} from '../scripts/repository_dispatch.mjs';

const sha = 'a'.repeat(40);
const validRun = () => ({
  name: SOURCE_WORKFLOW,
  event: 'push',
  head_branch: 'main',
  conclusion: 'success',
  head_repository: { full_name: SOURCE_REPOSITORY },
  id: 123456,
  run_attempt: 1,
  head_sha: sha,
});

test('payload preparation writes only the approved metadata event', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-dispatch-'));
  const eventPath = path.join(directory, 'event.json');
  const outputPath = path.join(directory, 'payload.json');
  const event = { workflow_run: validRun() };
  try {
    await writeFile(eventPath, JSON.stringify(event));
    const body = await prepareDispatchPayload(eventPath, outputPath);
    assert.deepEqual(body, createDispatchBody(event.workflow_run));
    assert.deepEqual(JSON.parse(await readFile(outputPath, 'utf8')), body);
    await assert.rejects(prepareDispatchPayload(eventPath, outputPath));
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('payload preparation errors never surface input contents', () => {
  assert.equal(classifyDispatchError(new Error('untrusted detail')), 'dispatch_failed');
  assert.equal(classifyDispatchError(new Error('dispatch_out_of_scope')), 'dispatch_out_of_scope');
});

test('dispatch body contains only bounded source build metadata', () => {
  assert.deepEqual(createDispatchBody(validRun()), {
    event_type: DISPATCH_EVENT_TYPE,
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
  assert.equal(TARGET_REPOSITORY, 'hamedonassar95/Devobs');
});

test('dispatch is skipped unless the exact source workflow succeeded on a main push', () => {
  for (const changes of [
    { name: 'Other workflow' },
    { event: 'pull_request' },
    { head_branch: 'feature/example' },
    { conclusion: 'failure' },
    { head_repository: { full_name: 'someone/fork' } },
    { id: 0 },
    { run_attempt: 0 },
    { head_sha: 'not-a-commit' },
  ]) {
    assert.equal(createDispatchBody({ ...validRun(), ...changes }), null);
  }
  assert.equal(createDispatchBody(null), null);
});
