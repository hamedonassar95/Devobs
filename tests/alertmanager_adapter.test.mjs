import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { convertText, MAX_INPUT_BYTES, MAX_EVENTS_PER_BATCH } from '../scripts/integrations/alertmanager_adapter.mjs';
import { ALLOWED_SOURCES } from '../scripts/integrations/project_sources.mjs';
import { parseEventLines } from '../scripts/ai_intelligence/event_schema.mjs';
import { ingestText, readEventStore } from '../scripts/ai_intelligence/event_ingest.mjs';
import { buildDashboardSnapshot } from '../scripts/ai_intelligence/dashboard_server.mjs';

const script = fileURLToPath(new URL('../scripts/integrations/alertmanager_adapter.mjs', import.meta.url));
const fixturePath = fileURLToPath(new URL('../examples/integrations/synthetic-alertmanager.json', import.meta.url));
const sample = JSON.parse(await readFile(fixturePath, 'utf8'));
const scope = { projectSource: 'https://github.com/hamedonassar95/Devobs', serviceId: 'monitoring' };
const fresh = () => structuredClone(sample);
const convert = (value = fresh(), binding = scope) => convertText(JSON.stringify(value), binding);
const events = value => parseEventLines(convert(value)).events;
function denies(value, code, binding = scope) { assert.throws(() => convert(value, binding), { code }); }
const args = ['--input', '-', '--source', scope.projectSource, '--service', scope.serviceId];
function cli(input, cliArgs = args) {
  return spawnSync(process.execPath, [script, ...cliArgs], {
    input, encoding: 'utf8', env: { PATH: process.env.PATH ?? '' }, timeout: 10000,
  });
}

test('versioned v4 payload becomes individual open/resolved AI-1 incidents', () => {
  const output = events();
  assert.equal(output.length, 2);
  assert.equal(output.find(item => item.data.status === 'open').occurred_at, '2026-11-14T09:00:00.123Z');
  assert.equal(output.find(item => item.data.status === 'resolved').occurred_at, '2026-11-14T10:00:00.000Z');
  for (const item of output) {
    assert.equal(item.kind, 'incident');
    assert.equal(item.source, 'operator');
    assert.match(item.data.summary, /^Alertmanager Devobs monitoring (ServiceDown|HighCpuUsage) [0-9a-f]{64}$/);
  }
  assert.equal(output.find(item => item.data.status === 'open').severity, 'critical');
  const oldShape = fresh(); delete oldShape.routeLabels; delete oldShape.notification_reason;
  assert.equal(convert(oldShape), convert());
});

test('all four approved rules and all seven project namespaces are reusable without scope aliasing', () => {
  const ids = new Set();
  for (const projectSource of Object.keys(ALLOWED_SOURCES)) {
    for (const alertname of ['HighCpuUsage', 'HighMemoryUsage', 'DiskSpaceRunningLow', 'ServiceDown']) {
      const value = fresh(); value.alerts[0].labels.alertname = alertname;
      const output = parseEventLines(convert(value, { ...scope, projectSource })).events;
      assert.ok(output.every(item => item.data.summary.includes(ALLOWED_SOURCES[projectSource])));
      ids.add(output.find(item => item.data.status === 'open').event_id);
    }
  }
  assert.equal(ids.size, 28);
  assert.notEqual(convert(fresh(), { ...scope, serviceId: 'another-service' }), convert());
});

test('discarded annotations, URLs, routing metadata and arbitrary labels cannot reach output or change IDs', () => {
  const value = fresh();
  value.groupKey = value.receiver = value.externalURL = value.notification_reason = 'PRIVATE_SENTINEL';
  value.commonAnnotations = { email: 'operator@example.invalid' };
  for (const alert of value.alerts) {
    alert.annotations = { log: 'Authorization: Bearer PRIVATE_SENTINEL' };
    alert.generatorURL = 'https://private.example.invalid/PRIVATE_SENTINEL';
    alert.labels.instance = '10.0.0.1:9090'; alert.labels.tenant = 'PRIVATE_SENTINEL';
  }
  const output = convert(value);
  assert.equal(output, convert());
  for (const marker of ['PRIVATE_SENTINEL', 'operator@', '10.0.0.1', 'https://', '0123456789abcdef']) assert.equal(output.includes(marker), false);
});

test('explicit scope is mandatory and reserved project/service claims cannot redirect it', () => {
  for (const binding of [undefined, {}, { ...scope, projectSource: 'https://github.com/other/repo' },
    { ...scope, projectSource: [scope.projectSource] }, { ...scope, projectSource: 42 },
    { ...scope, projectSource: { toString: () => scope.projectSource } },
    { ...scope, projectSource: new String(scope.projectSource) },
    { ...scope, serviceId: 'operator@example.invalid' }, { ...scope, tenant: 'injected' }]) {
    assert.throws(() => convertText(JSON.stringify(fresh()), binding), { code: 'invalid_scope' });
  }
  for (const key of ['groupLabels', 'commonLabels', 'routeLabels']) {
    const value = fresh(); value[key] = { devobs_project: 'another-project' }; denies(value, 'scope_mismatch');
  }
  const value = fresh(); value.alerts[0].labels.devobs_service = 'another-service'; denies(value, 'scope_mismatch');
  value.alerts[0].labels.devobs_service = scope.serviceId;
  value.alerts[0].labels.devobs_project = 'Devobs'; assert.equal(convert(value), convert());
});

test('unknown versions, incomplete groups, bad statuses and unapproved rules fail closed', () => {
  for (const [key, item, code] of [['version', '3', 'unsupported_version'],
    ['truncatedAlerts', 1, 'truncated_notification'], ['truncatedAlerts', -1, 'invalid_notification'],
    ['status', 'resolved', 'invalid_notification'], ['status', 'healthy', 'invalid_notification'],
    ['alerts', [], 'invalid_batch_size'], ['routeLabels', [], 'invalid_notification'], ['extra', true, 'invalid_notification']]) {
    const value = fresh(); value[key] = item; denies(value, code);
  }
  for (const [key, item, code] of [['status', 'acknowledged', 'invalid_alert'], ['fingerprint', 'bad', 'invalid_alert'],
    ['labels', { alertname: 'InventedRootCause', severity: 'critical' }, 'unknown_rule'],
    ['labels', { alertname: 'ServiceDown', severity: 'emergency' }, 'invalid_severity']]) {
    const value = fresh(); value.alerts[0][key] = item; denies(value, code);
  }
});

test('timestamps retain episode nanoseconds, equivalent offsets, and long-running firing alerts', () => {
  const value = fresh(); value.alerts[0].startsAt = '2026-11-14T12:00:00.123456789+03:00';
  assert.equal(convert(value), convert());
  value.alerts[0].startsAt = '2026-11-14T09:00:00.123456788Z'; assert.notEqual(convert(value), convert());
  value.alerts[0].startsAt = '2020-01-01T00:00:00Z'; assert.equal(events(value).length, 2);
  value.alerts[0].endsAt = '2026-12-01T00:00:00Z'; assert.equal(events(value).length, 2);
  value.alerts[0].endsAt = '0001-01-01T00:00:00Z'; assert.equal(events(value).length, 2);
  for (const time of ['2026-02-30T00:00:00Z', '2026-11-14T00:00:60Z', '2026-11-14T00:00:00+24:00',
    '2026-11-14T00:00:00', '0001-01-01T00:00:00Z']) {
    const bad = fresh(); bad.alerts[0].startsAt = time; denies(bad, 'invalid_timestamp');
  }
  const bad = fresh(); bad.alerts[1].endsAt = '2020-01-01T00:00:00Z'; denies(bad, 'invalid_timestamp');
});

test('duplicate keys, duplicate fingerprints and malformed late alerts reject the whole notification', () => {
  assert.throws(() => convertText('{"version":"4","ver\\u0073ion":"3"}', scope), { code: 'duplicate_json_key' });
  assert.throws(() => convertText('{broken', scope), { code: 'invalid_json' });
  const value = fresh(); value.alerts.push(structuredClone(value.alerts[0])); denies(value, 'duplicate_alert');
  value.alerts.pop(); value.alerts[1].fingerprint = 'PRIVATE_SENTINEL';
  const failed = cli(JSON.stringify(value));
  assert.equal(failed.status, 2); assert.equal(failed.stdout, '');
  assert.equal(failed.stderr, 'alertmanager-adapter: invalid_alert\n');
});

test('whole-input and alert-count limits reject excess without output', () => {
  assert.throws(() => convertText(' '.repeat(MAX_INPUT_BYTES + 1), scope), { code: 'input_too_large' });
  const value = fresh(); value.alerts = Array(MAX_EVENTS_PER_BATCH + 1).fill(value.alerts[0]); denies(value, 'invalid_batch_size');
  value.alerts = Array.from({ length: MAX_EVENTS_PER_BATCH }, (_, index) => ({
    ...sample.alerts[0], fingerprint: index.toString(16).padStart(16, '0'),
  }));
  assert.equal(events(value).length, MAX_EVENTS_PER_BATCH);
});

test('permutation and replay remain deterministic through real local ingestion and dashboard counts', async () => {
  const value = fresh(); value.alerts.reverse(); assert.equal(convert(value), convert());
  const parent = await mkdtemp(path.join(os.tmpdir(), 'devobs-alertmanager-'));
  try {
    const store = path.join(parent, 'events.jsonl');
    assert.deepEqual(await ingestText(convert(), store), { accepted: 2, duplicateIgnored: 0 });
    assert.deepEqual(await ingestText(convert(), store), { accepted: 0, duplicateIgnored: 2 });
    const snapshot = buildDashboardSnapshot(await readEventStore(store));
    assert.equal(snapshot.summary.kind_counts.incident, 2);
    assert.equal(snapshot.summary.metric_series_count, 0);
    assert.equal(snapshot.summary.recommendation_count, 0);
    assert.equal(snapshot.pipeline.mode, 'local_advisory_only');
  } finally { await rm(parent, { recursive: true, force: true }); }
});

test('CLI reads files/stdin and emits only fixed errors for missing scope, invalid UTF-8 and private paths', async () => {
  const parent = await mkdtemp(path.join(os.tmpdir(), 'devobs-alertmanager-cli-'));
  try {
    const file = path.join(parent, 'synthetic.json'); await writeFile(file, JSON.stringify(fresh()));
    for (const result of [cli(JSON.stringify(fresh())), cli('', ['--input', file, ...args.slice(2)])]) {
      assert.equal(result.status, 0, result.stderr); assert.equal(result.stderr, ''); assert.equal(result.stdout, convert());
    }
    for (const [input, arguments_, code] of [['{}', ['--input', '-'], 'invalid_arguments'],
      [Buffer.from([0xff]), args, 'invalid_utf8'], ['', ['--input', path.join(parent, 'PRIVATE_SENTINEL'), ...args.slice(2)], 'input_unavailable']]) {
      const result = cli(input, arguments_); assert.equal(result.status, 2); assert.equal(result.stdout, '');
      assert.equal(result.stderr, `alertmanager-adapter: ${code}\n`);
    }
  } finally { await rm(parent, { recursive: true, force: true }); }
});
