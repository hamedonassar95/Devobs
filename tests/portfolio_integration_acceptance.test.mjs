import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const scriptUrl = new URL('../scripts/portfolio_integration_acceptance.mjs', import.meta.url);
const script = fileURLToPath(scriptUrl);
const fixtureTexts = Object.fromEntries(await Promise.all([
  ['cloudevents', 'synthetic-ci-events.jsonl'], ['alertmanager', 'synthetic-alertmanager.json'], ['grafana', 'synthetic-grafana.json'],
].map(async ([key, file]) => [key, await readFile(new URL('../examples/integrations/' + file, import.meta.url), 'utf8')])));
const projects = ['Devobs', 'devobs-saas', 'phone-repair-assistant-v2', 'al-dala-mobile', 'LiveOps-Integration', 'DevObs-ai-Intelligence-', 'CineForge-AI'];
const libraryRunner = `
import { runAcceptance } from ${JSON.stringify(scriptUrl.href)};
let text = ''; for await (const chunk of process.stdin) text += chunk;
try { process.stdout.write(JSON.stringify(await runAcceptance(JSON.parse(text)))); }
catch (error) { process.stderr.write('library: ' + error.code + '\\n'); process.exitCode = 2; }
`;
function child(args, input = '', folder) {
  return spawnSync(process.execPath, args, { input, encoding: 'utf8', timeout: 20000,
    env: { PATH: process.env.PATH ?? '', ...(folder ? { TMPDIR: folder } : {}) } });
}
function library(fixtures = fixtureTexts, folder) {
  return child(['--input-type=module', '-e', libraryRunner], JSON.stringify(fixtures), folder);
}
function report(result) {
  assert.equal(result.status, 0, result.stderr); assert.equal(result.stderr, '');
  return JSON.parse(result.stdout);
}

test('one command proves three-provider ingestion and replay in seven separate local stores', () => {
  const r = report(child([script]));
  assert.equal(r.schema_version, 1); assert.equal(r.status, 'PASS');
  assert.equal(r.scope, 'offline_synthetic_namespaces_only');
  assert.equal(r.production_ready, false); assert.equal(r.live_integrations_verified, false);
  assert.equal(r.cleanup, 'complete');
  assert.deepEqual(r.totals, { projects: 7, unique_events: 35, accepted: 35,
    duplicate_ignored_on_replay: 35, severity_counts: { critical: 14, warning: 15, info: 5, error: 1, unknown: 0 } });
  assert.deepEqual(r.results.map(x => x.project), projects);
  assert.deepEqual(r.results.map(x => x.synthetic_ci_conclusion), ['success', 'success', 'failure', 'skipped', 'neutral', 'success', 'success']);
  for (const p of r.results) {
    assert.deepEqual(p.provider_counts, { cloudevents_ci: 1, alertmanager_v4: 2, grafana_v1: 2 });
    assert.equal(p.accepted, 5); assert.equal(p.stored_events, 5); assert.equal(p.duplicate_ignored_on_replay, 5);
    assert.deepEqual(p.incident_counts, { open: 2, resolved: 2 });
    assert.deepEqual(p.pipeline_stage_counts, [5, 0, 0, 0, 0, 0, 1]);
    assert.equal(p.log_clusters, 0); assert.equal(p.recommendations, 0);
  }
});

test('published aggregate report equals the real acceptance run', async () => {
  const expected = report(child([script]));
  const published = JSON.parse(await readFile(new URL('../assets/free-devobs/integration-acceptance.json', import.meta.url), 'utf8'));
  assert.deepEqual(published, expected);
  assert.doesNotMatch(JSON.stringify(published), /PRIVATE_SENTINEL|https?:\/\/|[a-f0-9]{40}/);
});

test('aggregate values come from converted events rather than fixed success counters', () => {
  const fixtures = { ...fixtureTexts };
  const rows = fixtures.cloudevents.trim().split('\n').map(JSON.parse); rows[0].data.conclusion = 'timed_out';
  fixtures.cloudevents = rows.map(JSON.stringify).join('\n') + '\n';
  const r = report(library(fixtures));
  assert.equal(r.results[0].synthetic_ci_conclusion, 'timed_out');
  assert.deepEqual(r.totals.severity_counts, { critical: 14, warning: 15, info: 4, error: 2, unknown: 0 });
});

test('discarded private display fields cannot reach the aggregate report', () => {
  const fixtures = { ...fixtureTexts };
  for (const key of ['alertmanager', 'grafana']) {
    const value = JSON.parse(fixtures[key]); value.commonAnnotations = { log: 'Bearer PRIVATE_SENTINEL' };
    for (const a of value.alerts) { a.annotations = { log: 'PRIVATE_SENTINEL' }; a.generatorURL = 'https://private.example.invalid/PRIVATE_SENTINEL'; }
    if (key === 'grafana') { value.title = value.message = 'PRIVATE_SENTINEL'; for (const a of value.alerts) a.valueString = 'PRIVATE_SENTINEL'; }
    fixtures[key] = JSON.stringify(value);
  }
  const r = library(fixtures); assert.deepEqual(report(r), report(child([script])));
  assert.doesNotMatch(r.stdout + r.stderr, /PRIVATE_SENTINEL|Bearer|https?:\/\/|[a-f0-9]{40}/);
});

test('missing or duplicate namespace coverage and invalid fixtures reject the entire report', () => {
  const variants = [];
  const missing = { ...fixtureTexts }; delete missing.grafana; variants.push([missing, 'invalid_fixture']);
  variants.push([{ ...fixtureTexts, unexpected: 'private' }, 'invalid_fixture']);
  variants.push([{ ...fixtureTexts, grafana: null }, 'invalid_fixture']);
  const rows = fixtureTexts.cloudevents.trim().split('\n').map(JSON.parse);
  variants.push([{ ...fixtureTexts, cloudevents: rows.slice(1).map(JSON.stringify).join('\n') }, 'invalid_fixture']);
  rows[1].source = rows[0].source; rows[1].id = 'another-valid-ci-id';
  variants.push([{ ...fixtureTexts, cloudevents: rows.map(JSON.stringify).join('\n') }, 'invalid_fixture']);
  variants.push([{ ...fixtureTexts, grafana: '{bad' }, 'acceptance_failed']);
  for (const [fixtures, code] of variants) {
    const r = library(fixtures); assert.equal(r.status, 2); assert.equal(r.stdout, '');
    assert.equal(r.stderr, `library: ${code}\n`);
  }
});

test('success and a later project scope failure clean up all task-owned files', async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'devobs-acceptance-test-'));
  try {
    report(child([script], '', folder)); assert.deepEqual(await readdir(folder), []);
    const fixtures = { ...fixtureTexts }; const value = JSON.parse(fixtures.grafana);
    value.alerts[0].labels.devobs_project = 'Devobs'; fixtures.grafana = JSON.stringify(value);
    const r = library(fixtures, folder); assert.equal(r.status, 2); assert.equal(r.stdout, '');
    assert.equal(r.stderr, 'library: acceptance_failed\n');
    assert.deepEqual(await readdir(folder), []);
  } finally { await rm(folder, { recursive: true, force: true }); }
});

test('CLI accepts no arbitrary paths or modes and emits fixed errors without partial output', () => {
  for (const args of [['--input', '/PRIVATE_SENTINEL'], ['--source', 'other'], ['--live']]) {
    const r = child([script, ...args]); assert.equal(r.status, 2); assert.equal(r.stdout, '');
    assert.equal(r.stderr, 'integration-acceptance: invalid_arguments\n');
  }
});
