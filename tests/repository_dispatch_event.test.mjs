import assert from 'node:assert/strict';
import test from 'node:test';

import {
  dispatchToAiEvent,
  DISPATCH_ACTION,
  SOURCE_REPOSITORY,
  SOURCE_WORKFLOW,
} from '../scripts/ai_intelligence/repository_dispatch_event.mjs';

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
