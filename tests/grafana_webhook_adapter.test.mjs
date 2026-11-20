import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { requireNoFollowCapability } from './node_platform_support.mjs';
import { fileURLToPath } from 'node:url';
import { convertText as alertmanager, MAX_INPUT_BYTES, MAX_EVENTS_PER_BATCH } from '../scripts/integrations/alertmanager_adapter.mjs';
import { ALLOWED_SOURCES } from '../scripts/integrations/project_sources.mjs';
import { parseEventLines } from '../scripts/ai_intelligence/event_schema.mjs';
import { ingestText, readEventStore } from '../scripts/ai_intelligence/event_ingest.mjs';
import { buildDashboardSnapshot } from '../scripts/ai_intelligence/dashboard_server.mjs';

const script = fileURLToPath(new URL('../scripts/integrations/grafana_webhook_adapter.mjs', import.meta.url));
const sample = JSON.parse(await readFile(new URL('../examples/integrations/synthetic-grafana.json', import.meta.url), 'utf8'));
const amSample = JSON.parse(await readFile(new URL('../examples/integrations/synthetic-alertmanager.json', import.meta.url), 'utf8'));
const scope = { projectSource: 'https://github.com/hamedonassar95/Devobs', serviceId: 'monitoring' };
const fresh = () => structuredClone(sample);
const args = binding => ['--input', '-', '--source', binding.projectSource, '--service', binding.serviceId];
function cli(input, cliArgs = args(scope)) {
  return spawnSync(process.execPath, [script, ...cliArgs], {
    input, encoding: 'utf8', env: { PATH: process.env.PATH ?? '' }, timeout: 10000,
  });
}
function convert(value = fresh(), binding = scope) {
  const r = cli(JSON.stringify(value), args(binding));
  assert.equal(r.status, 0, r.stderr); assert.equal(r.stderr, ''); return r.stdout;
}
const events = (value, binding) => parseEventLines(convert(value, binding)).events;
function denies(value, code, binding = scope) {
  const r = cli(JSON.stringify(value), args(binding));
  assert.equal(r.status, 2); assert.equal(r.stdout, '');
  assert.equal(r.stderr, `grafana-webhook-adapter: ${code}\n`);
}

test('default Grafana v1 produces individual open/resolved AI-1 incidents', () => {
  const result = events(); assert.equal(result.length, 2);
  const open = result.find(e => e.data.status === 'open');
  const resolved = result.find(e => e.data.status === 'resolved');
  assert.equal(open.occurred_at, '2026-11-14T09:00:00.123Z');
  assert.equal(open.severity, 'critical');
  assert.equal(resolved.occurred_at, '2026-11-14T10:00:00.000Z');
  assert.equal(resolved.severity, 'warning');
  for (const event of result) {
    assert.equal(event.source, 'operator'); assert.equal(event.kind, 'incident');
    assert.match(event.data.summary, /^Grafana Devobs monitoring (ServiceDown|HighCpuUsage) [0-9a-f]{64}$/);
  }
});

test('upstream null values and documentation without valueString are compatible', () => {
  const v = fresh(); delete v.appVersion;
  for (const a of v.alerts) { a.values = null; delete a.valueString; delete a.orgId; }
  assert.equal(convert(v), convert());
});

test('all seven namespaces and four approved rules have distinct scoped identities', () => {
  const ids = new Set();
  for (const projectSource of Object.keys(ALLOWED_SOURCES)) {
    for (const alertname of ['HighCpuUsage', 'HighMemoryUsage', 'DiskSpaceRunningLow', 'ServiceDown']) {
      const v = fresh(); v.alerts[0].labels.alertname = alertname;
      const list = events(v, { ...scope, projectSource });
      assert.ok(list.every(e => e.data.summary.startsWith(`Grafana ${ALLOWED_SOURCES[projectSource]} monitoring `)));
      ids.add(list.find(e => e.data.status === 'open').event_id);
    }
  }
  assert.equal(ids.size, 28);
  assert.notEqual(convert(fresh(), { ...scope, serviceId: 'other' }), convert());
});

test('provider and organization namespaces prevent accidental cross-source deduplication', () => {
  const am = new Set(parseEventLines(alertmanager(JSON.stringify(amSample), scope)).events.map(e => e.event_id));
  assert.ok(events().every(e => !am.has(e.event_id)));
  const other = fresh(); other.orgId = 43; for (const a of other.alerts) a.orgId = 43;
  assert.notEqual(convert(other), convert());
});

test('discarded private display, value, URL and rule metadata cannot affect output', () => {
  const v = fresh(); v.title = v.message = v.receiver = v.externalURL = v.groupKey = 'PRIVATE_SENTINEL';
  v.commonAnnotations = { note: 'PRIVATE_SENTINEL' };
  for (const a of v.alerts) {
    a.annotations = { token: 'Bearer PRIVATE_SENTINEL' }; a.labels.instance = '10.0.0.1';
    a.generatorURL = a.silenceURL = a.dashboardURL = a.panelURL = a.imageURL = 'https://private.example.invalid/PRIVATE_SENTINEL';
    a.ruleUID = a.valueString = 'PRIVATE_SENTINEL'; a.values = { PRIVATE_SENTINEL: 99 };
  }
  const output = convert(v); assert.equal(output, convert());
  for (const sentinel of ['PRIVATE_SENTINEL', 'Bearer', '10.0.0.1', 'https://', 'orgId', '0123456789abcdef']) assert.equal(output.includes(sentinel), false);
});

test('malformed protocol metadata, contradictory state and unsupported extensions reject all output', () => {
  for (const [key, value, code] of [
    ['version', '4', 'unsupported_version'], ['state', 'ok', 'invalid_notification'],
    ['status', 'resolved', 'invalid_notification'], ['orgId', 0, 'invalid_notification'],
    ['orgId', 1.2, 'invalid_notification'], ['message', {}, 'invalid_notification'],
    ['appVersion', [], 'invalid_notification'], ['custom', {}, 'invalid_notification'],
    ['truncatedAlerts', 1, 'truncated_notification'], ['alerts', [], 'invalid_batch_size'],
  ]) { const v = fresh(); v[key] = value; denies(v, code); }
  for (const [key, value] of [['values', []], ['values', { A: 'private' }], ['silenceURL', {}],
    ['valueString', 1], ['orgId', 43], ['ruleUID', {}], ['embeddedImage', {}], ['enrichments', []]]) {
    const v = fresh(); v.alerts[1][key] = value; denies(v, 'invalid_alert');
  }
});

test('existing rule, scope, time and duplicate protections remain enforced', () => {
  for (const [key, value, code] of [
    ['labels', { alertname: 'TestAlert', severity: 'critical' }, 'unknown_rule'],
    ['labels', { alertname: 'ServiceDown', severity: 'unknown' }, 'invalid_severity'],
    ['startsAt', '2026-02-30T00:00:00Z', 'invalid_timestamp'],
    ['fingerprint', 'private', 'invalid_alert'],
  ]) { const v = fresh(); v.alerts[1][key] = value; denies(v, code); }
  for (const field of ['groupLabels', 'commonLabels']) {
    const v = fresh(); v[field] = { devobs_project: 'other-project' }; denies(v, 'scope_mismatch');
  }
  const v = fresh(); v.alerts[1].labels.devobs_service = 'other-service'; denies(v, 'scope_mismatch');
  v.alerts[1] = structuredClone(v.alerts[0]); denies(v, 'duplicate_alert');
  denies(fresh(), 'invalid_scope', { ...scope, projectSource: 'https://github.com/other/repo' });
  const r = cli('{"version":"1","ver\\u0073ion":"2"}');
  assert.equal(r.status, 2); assert.equal(r.stdout, ''); assert.equal(r.stderr, 'grafana-webhook-adapter: duplicate_json_key\n');
});

test('batch bounds and late malformed alerts never produce partial output', () => {
  const v = fresh(); v.alerts = Array(MAX_EVENTS_PER_BATCH + 1).fill(v.alerts[0]); denies(v, 'invalid_batch_size');
  v.alerts = Array.from({ length: MAX_EVENTS_PER_BATCH }, (_, i) => ({ ...sample.alerts[0], fingerprint: i.toString(16).padStart(16, '0') }));
  assert.equal(events(v).length, MAX_EVENTS_PER_BATCH);
  const r = cli(' '.repeat(MAX_INPUT_BYTES + 1)); assert.equal(r.status, 2); assert.equal(r.stdout, '');
  assert.equal(r.stderr, 'grafana-webhook-adapter: input_too_large\n');
});

test('deterministic replay reaches the actual local event store and AI-7 snapshot', async t => {
  if (!requireNoFollowCapability(t)) return;
  const reversed = fresh(); reversed.alerts.reverse(); assert.equal(convert(reversed), convert());
  const folder = await mkdtemp(path.join(os.tmpdir(), 'devobs-grafana-'));
  try {
    const store = path.join(folder, 'events.jsonl');
    assert.deepEqual(await ingestText(convert(), store), { accepted: 2, duplicateIgnored: 0 });
    assert.deepEqual(await ingestText(convert(), store), { accepted: 0, duplicateIgnored: 2 });
    const snapshot = buildDashboardSnapshot(await readEventStore(store));
    assert.equal(snapshot.summary.kind_counts.incident, 2);
    assert.equal(snapshot.summary.recommendation_count, 0);
    assert.equal(snapshot.pipeline.mode, 'local_advisory_only');
    assert.equal(snapshot.pipeline.stages.length, 7);
  } finally { await rm(folder, { recursive: true, force: true }); }
});

test('CLI supports regular files and returns fixed non-sensitive input errors', async t => {
  if (!requireNoFollowCapability(t)) return;
  const folder = await mkdtemp(path.join(os.tmpdir(), 'devobs-grafana-cli-'));
  try {
    const file = path.join(folder, 'synthetic.json'); await writeFile(file, JSON.stringify(fresh()));
    const r = cli('', ['--input', file, ...args(scope).slice(2)]);
    assert.equal(r.status, 0, r.stderr); assert.equal(r.stdout, convert());
    for (const [input, cliArgs, code] of [[Buffer.from([0xff]), args(scope), 'invalid_utf8'],
      ['{}', ['--input', '-'], 'invalid_arguments'],
      ['', ['--input', path.join(folder, 'PRIVATE_SENTINEL'), ...args(scope).slice(2)], 'input_unavailable'],
      ['{broken', args(scope), 'invalid_json']]) {
      const bad = cli(input, cliArgs); assert.equal(bad.status, 2); assert.equal(bad.stdout, '');
      assert.equal(bad.stderr, `grafana-webhook-adapter: ${code}\n`);
    }
  } finally { await rm(folder, { recursive: true, force: true }); }
});
