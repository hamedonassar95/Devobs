import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { ingestText, normalizeEvent } from '../scripts/ai_intelligence/event_ingest.mjs';
import { analyzeMetricEvents, AnomalyAnalysisError, MIN_HISTORY_POINTS } from '../scripts/ai_intelligence/anomaly_detector.mjs';

const REPORT_PATH = fileURLToPath(new URL('../scripts/ai_intelligence/anomaly_report.mjs', import.meta.url));

function metric(name, value, minute, unit = 'percent') {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: new Date(Date.UTC(2026, 9, 28, 8, minute)).toISOString(),
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: { name, value, unit },
  });
}

function series(name, values, unit = 'percent') {
  return values.map((value, index) => metric(name, value, index, unit));
}

test('flags a synthetic CPU step change with transparent statistical signals', () => {
  const result = analyzeMetricEvents(series('cpu_percent', [20, 20.2, 19.9, 20.1, 19.8, 30]))[0];
  assert.equal(result.status, 'anomaly_candidate');
  assert.ok(result.signals.includes('z_score'));
  assert.ok(result.signals.includes('moving_average'));
  assert.ok(result.signals.includes('ewma'));
  assert.equal(result.detectors.z_score.threshold, 3);
  assert.equal(result.latest.value, 30);
});

test('detects a sudden synthetic error-rate increase in percentage points', () => {
  const result = analyzeMetricEvents(series('error_rate', [1, 1.1, 0.9, 1, 1.05, 3]))[0];
  assert.equal(result.detectors.error_rate_spike.applicable, true);
  assert.equal(result.detectors.error_rate_spike.flagged, true);
  assert.ok(result.signals.includes('error_rate_spike'));
});

test('labels short history insufficient and does not emit an anomaly', () => {
  const result = analyzeMetricEvents(series('memory_percent', [5, 5, 5, 5, 90]).slice(0, MIN_HISTORY_POINTS - 1))[0];
  assert.equal(result.status, 'insufficient_data');
  assert.equal(result.minimum_observations, MIN_HISTORY_POINTS);
  assert.deepEqual(result.signals, []);
  assert.equal(Object.hasOwn(result, 'detectors'), false);
});

test('constant baseline does not create a zero-variance z-score alert', () => {
  const result = analyzeMetricEvents(series('disk_percent', [20, 20, 20, 20, 20, 20]))[0];
  assert.equal(result.status, 'no_signal');
  assert.equal(result.detectors.z_score.value, null);
  assert.deepEqual(result.signals, []);
});

test('sorts out-of-order records, isolates metric series, and ignores non-metric events', () => {
  const cpu = series('cpu_percent', [20, 20, 20, 20, 20, 35]);
  const requestRate = [10, 11, 10, 9, 10, 10].map((value, index) => metric('request_rate', value, index, 'per_second'));
  const incident = normalizeEvent({
    schema_version: 1,
    occurred_at: '2026-10-28T08:20:00Z',
    source: 'operator',
    kind: 'incident',
    severity: 'warning',
    data: { summary: 'Synthetic incident', status: 'open', impact: 'minor' },
  });
  const input = [incident, ...cpu.slice().reverse(), ...requestRate];
  const before = structuredClone(input);
  const result = analyzeMetricEvents(input);

  assert.deepEqual(result.map(item => item.metric), ['cpu_percent', 'request_rate']);
  assert.equal(result[0].status, 'anomaly_candidate');
  assert.equal(result[1].status, 'no_signal');
  assert.deepEqual(input, before);
});

test('rejects malformed records and unbounded input with fixed error codes', () => {
  assert.throws(() => analyzeMetricEvents([{ private: 'synthetic' }]), error => {
    assert.ok(error instanceof AnomalyAnalysisError);
    assert.equal(error.code, 'invalid_event');
    assert.equal(error.message.includes('synthetic'), false);
    return true;
  });
  assert.throws(() => analyzeMetricEvents(new Array(100_001)), { code: 'invalid_event_batch' });
});

test('offline CLI reads the local event store and prints no path or event payload', async t => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-anomaly-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const storePath = path.join(directory, 'events.jsonl');
  const values = series('error_rate', [1, 1, 1, 1, 1, 5]);
  await ingestText(`${values.map(event => JSON.stringify({
    schema_version: event.schema_version,
    occurred_at: event.occurred_at,
    source: event.source,
    kind: event.kind,
    severity: event.severity,
    data: event.data,
  })).join('\n')}\n`, storePath);

  const result = spawnSync(process.execPath, [REPORT_PATH, '--store', storePath], {
    env: { PATH: process.env.PATH ?? '' },
    encoding: 'utf8',
    timeout: 10_000,
  });
  assert.equal(result.status, 0);
  assert.equal(result.stderr, '');
  const report = JSON.parse(result.stdout);
  assert.equal(report.evaluated_metrics, 1);
  assert.equal(report.anomaly_candidates, 1);
  assert.equal(report.metrics[0].status, 'anomaly_candidate');
  assert.equal(result.stdout.includes(storePath), false);
  assert.equal(result.stdout.includes('Synthetic incident'), false);
  assert.match(await readFile(storePath, 'utf8'), /error_rate/);
});
