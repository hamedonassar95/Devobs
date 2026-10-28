import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { ingestText, normalizeEvent } from '../scripts/ai_intelligence/event_ingest.mjs';
import { TrendAnalysisError, forecastMetricEvents, MIN_FORECAST_DAYS, SES_ALPHA } from '../scripts/ai_intelligence/trend_forecast.mjs';
import { buildOperationalTrendReport, renderOperationalTrendMarkdown } from '../scripts/ai_intelligence/trend_report.mjs';

const REPORT_PATH = fileURLToPath(new URL('../scripts/ai_intelligence/trend_report.mjs', import.meta.url));

function metric(day, value, name = 'cpu_percent', hour = 8) {
  const occurredAt = new Date(`${day}T${String(hour).padStart(2, '0')}:00:00Z`).toISOString();
  const unit = name === 'request_rate' ? 'per_second' : name === 'latency_ms' ? 'milliseconds' : name === 'uptime_seconds' ? 'seconds' : 'percent';
  return normalizeEvent({
    schema_version: 1,
    occurred_at: occurredAt,
    source: 'server',
    kind: 'server_metric',
    severity: 'info',
    data: { name, value, unit },
  });
}

function dailySeries(values, startDay = '2026-10-01', name = 'cpu_percent') {
  const start = Date.parse(`${startDay}T00:00:00Z`);
  return values.map((value, index) => metric(new Date(start + index * 86_400_000).toISOString().slice(0, 10), value, name));
}

function log(day, message) {
  return normalizeEvent({
    schema_version: 1,
    occurred_at: `${day}T10:00:00Z`,
    source: 'application',
    kind: 'log',
    severity: 'error',
    data: { stream: 'application', message },
  });
}

function jsonl(records) {
  return `${records.map(({ event_id: _id, ...event }) => JSON.stringify(event)).join('\n')}\n`;
}

test('emits one-day linear and fixed-alpha SES candidates from six contiguous synthetic daily averages', () => {
  const events = dailySeries([20, 22, 24, 26, 28, 30]);
  const [result] = forecastMetricEvents(events);

  assert.equal(result.status, 'forecast_candidate');
  assert.equal(result.consecutive_observations, MIN_FORECAST_DAYS);
  assert.equal(result.horizon_days, 1);
  assert.equal(result.linear_regression.next_day_candidate, 32);
  assert.equal(result.linear_regression.slope_per_day, 2);
  assert.equal(result.simple_exponential_smoothing.alpha, SES_ALPHA);
  assert.equal(result.simple_exponential_smoothing.next_day_candidate, 26.11766);
  assert.equal(result.range_warning, false);
});

test('does not forecast when the latest daily history has a gap', () => {
  const days = ['2026-10-01', '2026-10-02', '2026-10-03', '2026-10-04', '2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09'];
  const [result] = forecastMetricEvents(days.map((day, index) => metric(day, 20 + index)));
  assert.equal(result.status, 'insufficient_history');
  assert.equal(result.consecutive_observations, 4);
  assert.equal(Object.hasOwn(result, 'linear_regression'), false);
});

test('surfaces rather than clips a percentage forecast outside its defined range', () => {
  const [result] = forecastMetricEvents(dailySeries([90, 95, 99, 100, 100, 100]));
  assert.equal(result.status, 'range_warning');
  assert.equal(result.range_warning, true);
  assert.ok(result.linear_regression.next_day_candidate > 100);
});

test('rejects malformed or over-limit input with fixed error codes and no input mutation', () => {
  const valid = dailySeries([1, 2, 3, 4, 5, 6]);
  const before = structuredClone(valid);
  assert.throws(() => forecastMetricEvents([{ event_id: 'synthetic', private: 'not-an-event' }]), error => {
    assert.ok(error instanceof TrendAnalysisError);
    assert.equal(error.code, 'invalid_event');
    assert.equal(error.message.includes('synthetic'), false);
    return true;
  });
  assert.throws(() => forecastMetricEvents(new Array(100_001)), { code: 'invalid_event_batch' });
  forecastMetricEvents(valid);
  assert.deepEqual(valid, before);
});

test('builds UTC daily and seven-day summaries without exposing raw event text', () => {
  const events = [
    log('2026-09-20', 'SYNTHETIC_OLD_MESSAGE'),
    ...dailySeries([10, 20, 30, 40, 50, 60], '2026-10-01'),
    metric('2026-10-06', 80, 'cpu_percent', 9),
    log('2026-10-06', 'SYNTHETIC_PRIVATE_TEXT_MARKER'),
  ];
  const report = buildOperationalTrendReport(events);
  const markdown = renderOperationalTrendMarkdown(report);

  assert.equal(report.status, 'report_available');
  assert.equal(report.daily.window_start_utc, '2026-10-06');
  assert.equal(report.daily.event_count, 3);
  assert.equal(report.daily.kind_counts.server_metric, 2);
  assert.equal(report.weekly.window_start_utc, '2026-09-30');
  assert.equal(report.weekly.event_count, 8);
  assert.equal(report.weekly.kind_counts.log, 1);
  assert.equal(report.daily.metrics[0].observations, 2);
  assert.equal(report.daily.metrics[0].mean, 70);
  assert.equal(markdown.includes('SYNTHETIC_PRIVATE_TEXT_MARKER'), false);
  assert.equal(markdown.includes('SYNTHETIC_OLD_MESSAGE'), false);
  assert.match(markdown, /الملخص اليومي/);
  assert.match(markdown, /الملخص الأسبوعي/);
});

test('returns an explicit no-events report instead of a fabricated forecast', () => {
  const report = buildOperationalTrendReport([]);
  assert.equal(report.status, 'no_events');
  assert.equal(report.daily, null);
  assert.deepEqual(report.metric_forecasts, []);
  assert.match(renderOperationalTrendMarkdown(report), /لا توجد أحداث محلية/);
});

test('offline CLI reads a synthetic store without changing it or printing paths and event payloads', async t => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-trend-report-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const storePath = path.join(directory, 'events.jsonl');
  const marker = 'SYNTHETIC_RAW_EVENT_TEXT_MUST_NOT_APPEAR';
  const events = [...dailySeries([10, 12, 14, 16, 18, 20]), log('2026-10-06', marker)];
  await ingestText(jsonl(events), storePath);
  const before = await readFile(storePath, 'utf8');

  const result = spawnSync(process.execPath, [REPORT_PATH, '--store', storePath], {
    env: { PATH: process.env.PATH ?? '' },
    encoding: 'utf8',
    timeout: 10_000,
  });

  assert.equal(result.status, 0);
  assert.equal(result.stderr, '');
  assert.match(result.stdout, /# تقرير الاتجاهات التشغيلي/);
  assert.match(result.stdout, /22/);
  assert.equal(result.stdout.includes(marker), false);
  assert.equal(result.stdout.includes(storePath), false);
  assert.equal(await readFile(storePath, 'utf8'), before);
});

test('offline CLI fails closed for a missing store without echoing its path', async t => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-trend-missing-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const missingPath = path.join(directory, 'not-created.jsonl');
  const result = spawnSync(process.execPath, [REPORT_PATH, '--store', missingPath], {
    env: { PATH: process.env.PATH ?? '' },
    encoding: 'utf8',
    timeout: 10_000,
  });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /trend-report: store_unavailable/);
  assert.equal(result.stderr.includes(missingPath), false);
  assert.equal(result.stdout, '');
});
