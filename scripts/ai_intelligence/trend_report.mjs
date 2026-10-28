#!/usr/bin/env node
import { lstat } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readEventStore } from './event_ingest.mjs';
import { forecastMetricEvents, TrendAnalysisError } from './trend_forecast.mjs';
import { parseStoredEvent } from './event_schema.mjs';

const KINDS = ['ci_result', 'incident', 'log', 'server_metric'];
const SEVERITIES = ['critical', 'debug', 'error', 'info', 'unknown', 'warning'];
const DAY_MS = 86_400_000;
const MAX_REPORT_EVENTS = 100_000;

function reject(code) {
  throw new TrendAnalysisError(code);
}

function utcDayOffset(day, offset) {
  const timestamp = Date.parse(`${day}T00:00:00Z`) + offset * DAY_MS;
  if (!Number.isFinite(timestamp)) reject('numeric_range');
  return new Date(timestamp).toISOString().slice(0, 10);
}

function summarizeWindow(events, start, end) {
  const selected = events.filter(event => {
    const day = event.occurred_at.slice(0, 10);
    return day >= start && day <= end;
  });
  const kindCounts = Object.fromEntries(KINDS.map(kind => [kind, 0]));
  const severityCounts = Object.fromEntries(SEVERITIES.map(severity => [severity, 0]));
  const metricGroups = new Map();

  for (const event of selected) {
    kindCounts[event.kind]++;
    severityCounts[event.severity]++;
    if (event.kind !== 'server_metric') continue;
    const { name, unit, value } = event.data;
    const key = `${name}\u0000${unit}`;
    const current = metricGroups.get(key) ?? {
      metric: name, unit, count: 0, min: value, max: value, mean: 0, latest: null,
    };
    current.count++;
    current.min = Math.min(current.min, value);
    current.max = Math.max(current.max, value);
    current.mean += (value - current.mean) / current.count;
    if (!current.latest || event.occurred_at > current.latest.occurred_at) {
      current.latest = { occurred_at: event.occurred_at, value };
    }
    metricGroups.set(key, current);
  }

  const metrics = [...metricGroups.values()]
    .sort((left, right) => left.metric.localeCompare(right.metric))
    .map(metric => ({
      metric: metric.metric,
      unit: metric.unit,
      observations: metric.count,
      minimum: metric.min,
      maximum: metric.max,
      mean: metric.mean,
      latest: metric.latest,
    }));

  return {
    window_start_utc: start,
    window_end_utc: end,
    event_count: selected.length,
    kind_counts: kindCounts,
    severity_counts: severityCounts,
    metrics,
  };
}

export function buildOperationalTrendReport(records) {
  if (!Array.isArray(records) || records.length > MAX_REPORT_EVENTS) reject('invalid_event_batch');
  let events;
  try {
    events = records.map(record => parseStoredEvent(record)).sort((left, right) => left.occurred_at.localeCompare(right.occurred_at)
      || left.event_id.localeCompare(right.event_id));
  } catch {
    reject('invalid_event');
  }

  if (events.length === 0) {
    return {
      schema_version: 1,
      mode: 'local_read_only_summary',
      status: 'no_events',
      daily: null,
      weekly: null,
      metric_forecasts: [],
    };
  }

  const latestDay = events.at(-1).occurred_at.slice(0, 10);
  return {
    schema_version: 1,
    mode: 'local_read_only_summary',
    status: 'report_available',
    latest_event_at_utc: events.at(-1).occurred_at,
    daily: summarizeWindow(events, latestDay, latestDay),
    weekly: summarizeWindow(events, utcDayOffset(latestDay, -6), latestDay),
    metric_forecasts: forecastMetricEvents(events),
  };
}

function markdownMetricTable(metrics) {
  if (metrics.length === 0) return 'لا توجد مقاييس في هذه النافذة.\n';
  return [
    '| المقياس | الوحدة | عدد العينات | الأدنى | المتوسط | الأعلى | آخر قيمة |',
    '|---|---:|---:|---:|---:|---:|---:|',
    ...metrics.map(metric => `| ${metric.metric} | ${metric.unit} | ${metric.observations} | ${metric.minimum} | ${Number(metric.mean.toPrecision(6))} | ${metric.maximum} | ${metric.latest.value} |`),
    '',
  ].join('\n');
}

function markdownSummary(title, summary) {
  return [
    `## ${title} (UTC)`,
    `الفترة: ${summary.window_start_utc} إلى ${summary.window_end_utc} — ${summary.event_count} حدث.`,
    `حسب النوع: ${KINDS.map(kind => `${kind}=${summary.kind_counts[kind]}`).join('، ')}.`,
    `حسب الشدة: ${SEVERITIES.map(severity => `${severity}=${summary.severity_counts[severity]}`).join('، ')}.`,
    '',
    '### المقاييس',
    markdownMetricTable(summary.metrics),
  ].join('\n');
}

function markdownForecastTable(forecasts) {
  if (forecasts.length === 0) return 'لا توجد سلاسل مقاييس لتقييمها.\n';
  return [
    '| المقياس | الأيام المتصلة | الاتجاه الخطي لليوم التالي | التمهيد الأسي α=0.3 | الحالة |',
    '|---|---:|---:|---:|---|',
    ...forecasts.map(item => {
      const regression = item.linear_regression?.next_day_candidate ?? '—';
      const smoothing = item.simple_exponential_smoothing?.next_day_candidate ?? '—';
      const status = item.status === 'forecast_candidate' ? 'مرشح استرشادي' : item.status === 'range_warning' ? 'تحذير نطاق' : 'بيانات غير كافية';
      return `| ${item.metric} | ${item.consecutive_observations}/${item.minimum_consecutive_observations}+ | ${regression} | ${smoothing} | ${status} |`;
    }),
    '',
  ].join('\n');
}

export function renderOperationalTrendMarkdown(report) {
  if (report.status === 'no_events') {
    return '# تقرير الاتجاهات المحلي\n\nلا توجد أحداث محلية في السجل. لم يُنتج تنبؤ.\n';
  }
  return [
    '# تقرير الاتجاهات التشغيلي (محلي)',
    '',
    '> ملخص قراءة فقط من ملف أحداث محلي. النماذج استقراءات أولية وليست تنبيهات أو توقعات موثوقة.',
    `آخر حدث ضمن السجل: ${report.latest_event_at_utc}. النوافذ تُحدد من تاريخ هذا الحدث لا من ساعة التشغيل.`,
    '',
    markdownSummary('الملخص اليومي', report.daily),
    markdownSummary('الملخص الأسبوعي — آخر 7 أيام', report.weekly),
    '## استقراء المقاييس ليوم واحد',
    'الانحدار الخطي يستخدم متوسط كل يوم UTC؛ والتمهيد الأسي الثابت α=0.3 يعامل الأيام المرصودة بالتساوي. تُعرض نتيجة فقط عند وجود 6 أيام متصلة على الأقل.',
    '',
    markdownForecastTable(report.metric_forecasts),
    'لا يثبت الاستقراء سببًا أو حادثًا مستقبليًا. لا توجد فواصل ثقة أو معايرة أو اختبار رجعي، ولا تُنفذ توصيات أو تغييرات.',
    '',
  ].join('\n');
}

function parseArgs(args) {
  if (args.length === 1 && ['--help', '-h'].includes(args[0])) return { help: true };
  if (args.length !== 2 || args[0] !== '--store' || !args[1] || args[1].startsWith('--')) reject('invalid_arguments');
  return { storePath: args[1] };
}

function usage() {
  return 'Usage: node scripts/ai_intelligence/trend_report.mjs --store <local-jsonl-file>';
}

export async function main(args = process.argv.slice(2)) {
  try {
    const options = parseArgs(args);
    if (options.help) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    try {
      const info = await lstat(options.storePath);
      if (!info.isFile()) reject('store_unavailable');
    } catch (error) {
      if (error instanceof TrendAnalysisError) throw error;
      reject('store_unavailable');
    }
    const events = await readEventStore(options.storePath);
    process.stdout.write(renderOperationalTrendMarkdown(buildOperationalTrendReport(events)));
    return 0;
  } catch (error) {
    const code = error instanceof EventIngestError || error instanceof TrendAnalysisError ? error.code : 'analysis_failed';
    process.stderr.write(`trend-report: ${code}\n${usage()}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
