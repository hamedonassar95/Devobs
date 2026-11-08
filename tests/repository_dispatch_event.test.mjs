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
  LIVEOPS_DISPATCH_ACTION,
  LIVEOPS_SOURCE_REPOSITORY,
  LIVEOPS_SOURCE_WORKFLOW,
  renderDispatchSummary,
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

const validLiveOpsDispatch = (conclusion = 'success') => ({
  action: LIVEOPS_DISPATCH_ACTION,
  client_payload: {
    source_repository: LIVEOPS_SOURCE_REPOSITORY,
    source_branch: 'main',
    source_sha: sha,
    source_run_id: 789012,
    source_run_attempt: 2,
    source_workflow: LIVEOPS_SOURCE_WORKFLOW,
    source_conclusion: conclusion,
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

test('dispatch summary exposes only validated source provenance', () => {
  const summary = renderDispatchSummary(validDispatch());

  assert.match(summary, /Validated external CI dispatch metadata/);
  assert.match(summary, /Source run: \[123456\].*attempt 1/);
  assert.ok(summary.includes(`Source commit: [\`${sha}\`](https://github.com/${SOURCE_REPOSITORY}/commit/${sha})`));
  assert.match(summary, /not independent cryptographic authentication/);
  assert.doesNotMatch(summary, /client_payload|incident_log|Authorization/);
  assert.throws(() => renderDispatchSummary({
    ...validDispatch(), client_payload: { ...validDispatch().client_payload, source_run_id: '123456' },
  }), { code: 'repository_dispatch_out_of_scope' });
});

test('LiveOps dispatch accepts only bounded main-push build results', () => {
  const expected = [
    ['success', 'info'],
    ['failure', 'error'],
    ['cancelled', 'warning'],
  ];

  for (const [conclusion, severity] of expected) {
    const event = dispatchToAiEvent(validLiveOpsDispatch(conclusion), '2026-11-08T20:00:00Z');
    assert.equal(event.source, 'github_actions');
    assert.equal(event.kind, 'ci_result');
    assert.equal(event.severity, severity);
    assert.deepEqual(event.data, {
      workflow: 'LiveOps Integration - LiveOps CI',
      job: 'main build',
      conclusion,
      commit_sha: sha,
    });
  }

  const summary = renderDispatchSummary(validLiveOpsDispatch('failure'));
  assert.ok(summary.includes(`https://github.com/${LIVEOPS_SOURCE_REPOSITORY}/actions/runs/789012`));
  assert.match(summary, /LiveOps-Integration/);
  assert.throws(() => dispatchToAiEvent(validLiveOpsDispatch('skipped')), { code: 'repository_dispatch_out_of_scope' });
  for (const changes of [
    { source_repository: 'someone/other' },
    { source_branch: 'feature/private' },
    { source_workflow: 'unapproved workflow' },
    { source_event: 'pull_request' },
  ]) {
    assert.throws(() => dispatchToAiEvent({
      ...validLiveOpsDispatch(),
      client_payload: { ...validLiveOpsDispatch().client_payload, ...changes },
    }), { code: 'repository_dispatch_out_of_scope' });
  }
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

test('repository dispatch workflow subscribes to both approved source actions', async () => {
  const workflow = await readFile(path.join(ROOT, '.github/workflows/repository-dispatch.yml'), 'utf8');
  assert.match(workflow, /repository_dispatch:\s*\n\s*types:\s*\[[^\]]*devobs_ai_intelligence_ci_passed/);
  assert.match(workflow, /types:\s*\[[^\]]*liveops_ci_result/);
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
  const summary = spawnSync(process.execPath, [
    path.join(ROOT, 'scripts/ai_intelligence/repository_dispatch_event.mjs'), '--summary', inputPath,
  ], { cwd: ROOT, env, encoding: 'utf8', timeout: 10_000 });

  assert.equal(summary.status, 0, summary.stderr);
  assert.equal(summary.stderr, '');
  assert.match(summary.stdout, /Source run: \[123456\]/);
  assert.match(summary.stdout, new RegExp(sha));

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
