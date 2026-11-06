import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createDispatchBody,
  DISPATCH_EVENT_TYPE,
  sendDispatch,
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

test('sender posts only the prepared event to the fixed Devobs target', async () => {
  const body = createDispatchBody(validRun());
  let request;
  await sendDispatch(body, 'test-only-token', async (url, options) => {
    request = { url, options };
    return { status: 204 };
  });
  assert.equal(request.url, 'https://api.github.com/repos/hamedonassar95/Devobs/dispatches');
  assert.equal(request.options.method, 'POST');
  assert.equal(request.options.headers.Authorization, 'Bearer test-only-token');
  assert.deepEqual(JSON.parse(request.options.body), body);
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
