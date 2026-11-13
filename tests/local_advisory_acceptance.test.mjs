import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import {
  parseSyntheticFixture,
  runLocalAdvisoryAcceptance,
} from '../scripts/local_advisory_acceptance.mjs';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const SCRIPT = fileURLToPath(new URL('../scripts/local_advisory_acceptance.mjs', import.meta.url));
const FIXTURE = fileURLToPath(new URL('./fixtures/intelligence_eval_cases.json', import.meta.url));
const RAW_LOG_SENTINEL = 'LOCAL_ADVISORY_RAW_LOG_SENTINEL';

async function temporaryParent() {
  return mkdtemp(path.join(os.tmpdir(), 'devobs-local-advisory-test-'));
}

async function withTemporaryParent(run) {
  const parent = await temporaryParent();
  try {
    return await run(parent);
  } finally {
    await rm(parent, { recursive: true, force: true });
  }
}

test('CLI executes AI-1 through AI-7 locally, checks the read-only API, and shuts down cleanly', () => {
  const result = spawnSync(process.execPath, [SCRIPT], {
    cwd: ROOT,
    env: { PATH: process.env.PATH ?? '' },
    encoding: 'utf8',
    timeout: 30_000,
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
  const output = JSON.parse(result.stdout);
  assert.equal(output.status, 'LOCAL_ACCEPTANCE_PASSED');
  assert.equal(output.scope, 'offline_synthetic_only');
  assert.equal(output.pipeline_mode, 'local_advisory_only');
  assert.deepEqual(output.stages.map(stage => stage.id), ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7']);
  assert.equal(output.api.method, 'GET');
  assert.equal(output.api.status, 200);
  assert.ok(output.api.response_bytes > 0);
  assert.ok(output.api.response_bytes <= output.api.response_limit_bytes);
  assert.equal(output.safeguards.dashboard_shutdown, 'graceful');
  assert.equal(output.safeguards.temporary_artifacts_removed, true);
  assert.equal(output.safeguards.automatic_execution, false);
  assert.equal(output.safeguards.deployment_executed, false);
  assert.equal(output.safeguards.remediation_executed, false);
  assert.equal(output.safeguards.google_configs_enabled, false);
  assert.equal(output.production_ready, false);
});

test('rejects malformed or oversized fixture data without echoing it or starting a server', async () => withTemporaryParent(async parent => {
  const privateMarker = 'MALFORMED_FIXTURE_PRIVATE_MARKER';
  assert.throws(() => parseSyntheticFixture(`{"private":"${privateMarker}"}`), error => {
    assert.equal(error.code, 'invalid_fixture');
    assert.equal(error.message.includes(privateMarker), false);
    return true;
  });
  await assert.rejects(runLocalAdvisoryAcceptance({ fixtureText: 'not-json', tempParent: parent }), error => {
    assert.equal(error.code, 'invalid_fixture');
    assert.equal(error.message.includes('not-json'), false);
    return true;
  });
  await assert.rejects(runLocalAdvisoryAcceptance({ fixtureText: ' '.repeat(65_537), tempParent: parent }), {
    code: 'invalid_fixture',
  });
  assert.deepEqual(await readdir(parent), []);
}));

test('keeps logs private, closes the dashboard, and removes temporary files', async () => withTemporaryParent(async parent => {
  const fixtureText = await readFile(FIXTURE, 'utf8');
  const output = await runLocalAdvisoryAcceptance({ fixtureText, tempParent: parent });
  const serialized = JSON.stringify(output);
  assert.equal(serialized.includes(RAW_LOG_SENTINEL), false);
  assert.equal(serialized.includes(parent), false);
  assert.equal(output.safeguards.raw_log_exposed, false);
  assert.equal(output.safeguards.automatic_execution, false);
  assert.equal(output.safeguards.deployment_executed, false);
  assert.equal(output.safeguards.remediation_executed, false);
  assert.ok(output.event_count <= 100);
  assert.ok(output.recommendation_count <= 100);
  assert.equal(output.safeguards.dashboard_shutdown, 'graceful');
  assert.equal(output.safeguards.temporary_artifacts_removed, true);
  assert.deepEqual(await readdir(parent), []);
}));
