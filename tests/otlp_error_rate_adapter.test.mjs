import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { requireNoFollowCapability } from './node_platform_support.mjs';
import { parseEventLines } from '../scripts/ai_intelligence/event_schema.mjs';
import { convertText, MAX_EVENTS_PER_BATCH, MAX_INPUT_BYTES } from '../scripts/integrations/otlp_error_rate_adapter.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.resolve(HERE, '../scripts/integrations/otlp_error_rate_adapter.mjs');
const nanos = timestamp => (BigInt(Date.parse(timestamp)) * 1000000n).toString();
const point = (timestamp = '2026-11-15T12:00:00Z', asDouble = 12.5) =>
  ({ timeUnixNano: nanos(timestamp), asDouble });
function request(points = [point()]) {
  return { resourceMetrics: [{
    resource: { attributes: [{ key: 'service.name', value: { stringValue: 'devobs' } }] },
    scopeMetrics: [{ metrics: [{
      name: 'error_rate_pct', unit: '%', gauge: { dataPoints: points },
    }] }],
  }] };
}

test('converts the approved synthetic OTLP gauge to the existing AI-1 metric', () => {
  const result = convertText(JSON.stringify(request()));
  const parsed = parseEventLines(result);
  assert.equal(parsed.events.length, 1);
  const event = parsed.events[0];
  assert.equal(event.occurred_at, '2026-11-15T12:00:00.000Z');
  assert.equal(event.source, 'server');
  assert.equal(event.kind, 'server_metric');
  assert.equal(event.severity, 'info');
  assert.deepEqual(event.data, { name: 'error_rate', value: 12.5, unit: 'percent' });
  assert.deepEqual(Object.keys(JSON.parse(result.trim())).sort(), [
    'data', 'kind', 'occurred_at', 'schema_version', 'severity', 'source',
  ]);
});

test('sorts accepted gauge points and rejects duplicate normalized timestamps', () => {
  const text = JSON.stringify(request([
    point('2026-11-15T12:01:00Z', 4.2),
    point('2026-11-15T12:00:00Z', 3.1),
  ]));
  const events = parseEventLines(convertText(text)).events;
  assert.deepEqual(events.map(e => e.data.value), [3.1, 4.2]);
  assert.throws(() => convertText(JSON.stringify(request([point(), point()]))));
  assert.throws(() => convertText(JSON.stringify(request([
    { timeUnixNano: nanos('2026-11-15T12:00:00Z'), asDouble: 5 },
    { timeUnixNano: (BigInt(nanos('2026-11-15T12:00:00Z')) + 1n).toString(), asDouble: 6 },
  ]))));
});

test('rejects telemetry with any unreviewed attributes, identity, format or scope', () => {
  const examples = [
    (() => { const x = request(); x.resourceMetrics[0].resource.attributes.push({ key: 'user.email', value: { stringValue: 'private' } }); return x; })(),
    (() => { const x = request(); x.resourceMetrics[0].resource.attributes[0].value.stringValue = 'another-project'; return x; })(),
    (() => { const x = request(); x.resourceMetrics[0].scopeMetrics[0].scope = { name: 'unknown' }; return x; })(),
    (() => { const x = request(); x.resourceMetrics[0].scopeMetrics[0].metrics[0].unit = '1'; return x; })(),
    (() => { const x = request(); x.resourceMetrics[0].scopeMetrics[0].metrics[0].name = 'cpu_percent'; return x; })(),
    (() => { const x = request(); x.resourceMetrics[0].scopeMetrics[0].metrics[0].gauge.dataPoints[0].attributes = []; return x; })(),
    (() => { const x = request(); x.resourceMetrics[0].scopeMetrics[0].metrics[0].histogram = {}; return x; })(),
    (() => { const x = request(); x.resourceMetrics[0].scopeMetrics.push({ metrics: [] }); return x; })(),
    (() => { const x = request(); x.resourceMetrics.push(x.resourceMetrics[0]); return x; })(),
    request([]),
    request(Array.from({ length: MAX_EVENTS_PER_BATCH + 1 }, (_, i) =>
      point(new Date(Date.parse('2026-11-15T12:00:00Z') + i * 1000).toISOString(), 3))),
    request([point('2026-11-15T12:00:00Z', -1)]),
    request([point('2026-11-15T12:00:00Z', 100.1)]),
    request([point('2026-11-15T12:00:00Z', null)]),
    request([{ asDouble: 5, timeUnixNano: '99999999999999999999' }]),
    request([{ asDouble: 5, timeUnixNano: 'not-a-time' }]),
  ];
  for (const item of examples) {
    assert.throws(() => convertText(JSON.stringify(item)));
  }
});

test('rejects duplicate JSON keys, including nested keys, before any output', () => {
  const valid = JSON.stringify(request());
  const duplicates = [
    valid.replace('"resourceMetrics":', '"resourceMetrics":[],"resourceMetrics":'),
    valid.replace('"stringValue":"devobs"', '"stringValue":"other","stringValue":"devobs"'),
    valid.replace('"asDouble":12.5', '"asDouble":100,"asDouble":12.5'),
  ];
  for (const input of duplicates) assert.throws(() => convertText(input));
});

test('CLI emits approved output only after validation and fixed non-sensitive errors', () => {
  const valid = JSON.stringify(request());
  const stdin = spawnSync(process.execPath, [SCRIPT, '--input', '-'], { encoding: 'utf8', input: valid });
  assert.equal(stdin.status, 0, stdin.stderr);

  const poisoned = valid.replace('"asDouble":12.5', '"asDouble":20,"asDouble":12.5');
  const bad = spawnSync(process.execPath, [SCRIPT, '--input', '-'], { encoding: 'utf8', input: poisoned });
  assert.equal(bad.status, 2);
  assert.equal(bad.stdout, '');
  assert.equal(bad.stderr, 'otlp-error-rate-adapter: duplicate_json_key\n');
  assert.equal(bad.stderr.includes('devobs'), false);
  assert.throws(() => convertText('x'.repeat(MAX_INPUT_BYTES + 1)));
});

test('CLI accepts a regular file only where secure reads are supported', async t => {
  if (!requireNoFollowCapability(t)) return;
  const folder = await mkdtemp(path.join(tmpdir(), 'devobs-otlp-'));
  t.after(() => rm(folder, { recursive: true, force: true }));
  const file = path.join(folder, 'snapshot.json');
  await writeFile(file, JSON.stringify(request()));
  const good = spawnSync(process.execPath, [SCRIPT, '--input', file], { encoding: 'utf8' });
  assert.equal(good.status, 0, good.stderr);
  assert.equal(parseEventLines(good.stdout).events.length, 1);
  assert.equal(good.stderr, '');
});
