import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { triageCineForgeCi } from '../scripts/integrations/cineforge_ci_runner_triage.mjs';

const THIS_DIR = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(THIS_DIR, '..', 'scripts', 'integrations', 'cineforge_ci_runner_triage.mjs');
const failed = kind => ({ kind, status: 'completed', conclusion: 'failure', runner_id: 0, executed_steps: 0 });
const success = kind => ({ kind, status: 'completed', conclusion: 'success', runner_id: 123, executed_steps: 9 });
const payload = (overrides = {}) => ({
  schema_version: 1, source: 'cineforge-ai', run_status: 'completed', run_conclusion: 'failure',
  jobs: [failed('android'), failed('devobs-policy')], ...overrides,
});

test('classifies blocked jobs as pre-run failure, never a Kotlin failure', () => {
  const result = triageCineForgeCi(payload());
  assert.equal(result.observed_classification, 'FAILURE_BEFORE_RUNNER');
  assert.equal(result.jobs_failed_before_runner, 2);
  assert.equal(result.underlying_root_cause, 'UNKNOWN');
  assert.equal(result.recommends_code_change, false);
  assert.equal(result.provenance_verified, false);
  assert.equal(result.automatic_execution, false);
  assert.match(result.next_read_only_check, /GitHub run-level error banner/);
});
test('recognizes an actual executed failure without assigning a cause', () => {
  const input = payload({ jobs: [{ ...failed('android'), runner_id: 77, executed_steps: 3 }] });
  const result = triageCineForgeCi(input);
  assert.equal(result.observed_classification, 'WORKFLOW_EXECUTED_WITH_FAILURE');
  assert.equal(result.underlying_root_cause, 'UNKNOWN');
  assert.equal(result.jobs_with_executed_steps, 1);
});
test('reports an unverified success claim and never grants deployment', () => {
  const result = triageCineForgeCi(payload({ run_conclusion: 'success', jobs: [success('android')] }));
  assert.equal(result.observed_classification, 'SUCCESS_CLAIM_UNVERIFIED');
  assert.equal(result.provenance_verified, false);
  assert.equal(result.automatic_execution, false);
});
test('queued jobs do not imply failure or trigger a retry', () => {
  const input = payload({
    run_status: 'queued', run_conclusion: null,
    jobs: [{ ...failed('android'), status: 'queued', conclusion: null }],
  });
  assert.equal(triageCineForgeCi(input).observed_classification, 'RUN_NOT_COMPLETE');
});
test('mixed pre-step state does not claim an application failure', () => {
  const input = payload({ jobs: [failed('android'), { ...failed('devobs-policy'), runner_id: 77 }] });
  assert.equal(triageCineForgeCi(input).observed_classification, 'MIXED_OR_PRESTEP_FAILURE');
});
test('fails closed on untrusted, inconsistent, malformed or private data', () => {
  const cases = [
    payload({ source: 'other' }), payload({ logs: 'private logs' }),
    payload({ jobs: [failed('android'), failed('android')] }), payload({ jobs: [] }),
    payload({ jobs: [failed('android'), failed('devobs-policy'), failed('android')] }),
    payload({ jobs: [{ ...failed('android'), secret: 'x' }] }),
    payload({ jobs: [{ ...failed('android'), runner_id: -1 }] }),
    payload({ jobs: [{ ...failed('android'), runner_id: 0, executed_steps: 1 }] }),
    payload({ jobs: [{ ...failed('android'), executed_steps: NaN }] }),
    payload({ run_conclusion: 'success' }), payload({ jobs: [success('android')] }),
    payload({ run_status: 'queued', run_conclusion: 'failure' }),
    payload({ jobs: [{ ...failed('android'), kind: '__proto__' }] }),
  ];
  for (const input of cases) assert.throws(() => triageCineForgeCi(input));
});
test('CLI accepts bounded synthetic JSON and reports only fixed failures', async t => {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'ci-triage-'));
  t.after(() => rm(folder, { recursive: true, force: true }));
  const input = path.join(folder, 'run.json');
  await writeFile(input, JSON.stringify(payload()));
  const good = spawnSync(process.execPath, [SCRIPT, '--input', input], { encoding: 'utf8' });
  assert.equal(good.status, 0, good.stderr);
  assert.equal(JSON.parse(good.stdout).observed_classification, 'FAILURE_BEFORE_RUNNER');
  await writeFile(input, JSON.stringify({ ...payload(), logs: 'a-private-log' }));
  const bad = spawnSync(process.execPath, [SCRIPT, '--input', input], { encoding: 'utf8' });
  assert.equal(bad.status, 2);
  assert.equal(bad.stdout, '');
  assert.equal(bad.stderr, 'cineforge-ci-triage: invalid_run\n');
  assert.equal(bad.stderr.includes('a-private-log'), false);
  await writeFile(input, 'x'.repeat(4097));
  const oversized = spawnSync(process.execPath, [SCRIPT, '--input', input], { encoding: 'utf8' });
  assert.equal(oversized.status, 2);
  assert.equal(oversized.stderr, 'cineforge-ci-triage: input_too_large\n');
});
