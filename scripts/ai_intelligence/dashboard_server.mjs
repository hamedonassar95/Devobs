#!/usr/bin/env node
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readEventStore } from './event_ingest.mjs';
import { IncidentAnalysisError, analyzeIncidentEvents } from './incident_analysis.mjs';
import { FeedbackLearningError, applyFeedbackLearning, readFeedbackLedger } from './feedback_learning.mjs';
import { RecommendationError, recommendFromIncidentAnalysis } from './recommendations.mjs';
import { AnomalyAnalysisError, analyzeMetricEvents } from './anomaly_detector.mjs';
import { TrendAnalysisError } from './trend_forecast.mjs';
import { buildOperationalTrendReport } from './trend_report.mjs';

const HOST = '127.0.0.1';
const DEFAULT_PORT = 8765;
const MAX_URL_LENGTH = 2_048;
const ASSET_ROOT = new URL('./dashboard_assets/', import.meta.url);
const CONTENT_TYPES = new Map([
  ['/', 'text/html; charset=utf-8'],
  ['/dashboard.js', 'text/javascript; charset=utf-8'],
  ['/dashboard.css', 'text/css; charset=utf-8'],
  ['/runbook_notes.mjs', 'text/javascript; charset=utf-8'],
  ['/google_docs_export.mjs', 'text/javascript; charset=utf-8'],
  ['/google_calendar_followup.mjs', 'text/javascript; charset=utf-8'],
  ['/google_sheets_export.mjs', 'text/javascript; charset=utf-8'],
  ['/google_slides_export.mjs', 'text/javascript; charset=utf-8'],
  ['/google_chat_export.mjs', 'text/javascript; charset=utf-8'],
]);
const ASSET_FILES = new Map([
  ['/', 'index.html'],
  ['/dashboard.js', 'dashboard.js'],
  ['/dashboard.css', 'dashboard.css'],
  ['/runbook_notes.mjs', 'runbook_notes.mjs'],
  ['/google_docs_export.mjs', 'google_docs_export.mjs'],
  ['/google_calendar_followup.mjs', 'google_calendar_followup.mjs'],
  ['/google_sheets_export.mjs', 'google_sheets_export.mjs'],
  ['/google_slides_export.mjs', 'google_slides_export.mjs'],
  ['/google_chat_export.mjs', 'google_chat_export.mjs'],
]);

export class DashboardError extends Error {
  constructor(code) {
    super(code);
    this.name = 'DashboardError';
    this.code = code;
  }
}

function reject(code) {
  throw new DashboardError(code);
}

function countBy(values, allowed) {
  const counts = Object.fromEntries(allowed.map(value => [value, 0]));
  for (const value of values) if (Object.hasOwn(counts, value)) counts[value]++;
  return counts;
}

function safeRecommendation(item) {
  return {
    review_order: item.review_order,
    cause_id: item.cause_id,
    classification: 'POSSIBLE',
    heuristic_signal: item.heuristic_signal,
    event_count: item.event_count,
    evidence_markers: item.evidence_markers,
    runbook_title: item.runbook_title,
    read_only_checks: item.read_only_checks,
    possible_change_after_confirmation: item.possible_change_after_confirmation,
    feedback_review_signal: item.feedback_review_signal,
    requires_human_approval: true,
    automatic_execution: false,
  };
}

function safeAnomalyMetric(item) {
  const detectors = item.detectors
    ? Object.fromEntries(Object.entries(item.detectors).map(([name, result]) => [name, {
      value: result.value ?? result.delta ?? null,
      baseline: result.baseline ?? null,
      threshold: result.threshold ?? null,
      flagged: result.flagged === true,
    }]))
    : {};
  return {
    metric: item.metric,
    unit: item.unit,
    status: item.status,
    observations: item.observations,
    baseline_observations: item.baseline_observations ?? 0,
    latest_value: item.latest.value,
    signals: [...item.signals],
    detectors,
  };
}

function safeTrendWindow(window) {
  if (!window) return null;
  return {
    event_count: window.event_count,
    kind_counts: window.kind_counts,
    severity_counts: window.severity_counts,
    metrics: window.metrics.map(item => ({
      metric: item.metric,
      unit: item.unit,
      observations: item.observations,
      minimum: item.minimum,
      mean: item.mean,
      maximum: item.maximum,
      latest_value: item.latest.value,
    })),
  };
}

function safeForecast(item) {
  return {
    metric: item.metric,
    unit: item.unit,
    status: item.status,
    daily_observations: item.daily_observations,
    consecutive_observations: item.consecutive_observations,
    minimum_consecutive_observations: item.minimum_consecutive_observations,
    horizon_days: item.horizon_days,
    latest_value: item.latest_observation?.value ?? null,
    linear_regression: item.linear_regression ? {
      next_day_candidate: item.linear_regression.next_day_candidate,
      slope_per_day: item.linear_regression.slope_per_day,
    } : null,
    simple_exponential_smoothing: item.simple_exponential_smoothing ? {
      next_day_candidate: item.simple_exponential_smoothing.next_day_candidate,
    } : null,
    range_warning: item.range_warning === true,
  };
}

export function buildDashboardSnapshot(events, feedbackRecords = []) {
  if (!Array.isArray(events)) reject('invalid_snapshot_input');
  const analysis = analyzeIncidentEvents(events);
  const anomalyMetrics = analyzeMetricEvents(events);
  const trendReport = buildOperationalTrendReport(events);
  const recommendationReport = recommendFromIncidentAnalysis(analysis);
  const learnedReport = applyFeedbackLearning(recommendationReport, feedbackRecords);
  const recommendations = learnedReport.recommendations.map(safeRecommendation);
  const anomalyAnalysis = {
    status: anomalyMetrics.length ? 'analysis_available' : 'no_metrics',
    metric_count: anomalyMetrics.length,
    candidate_count: anomalyMetrics.filter(item => item.status === 'anomaly_candidate').length,
    metrics: anomalyMetrics.map(safeAnomalyMetric),
  };
  const forecasts = trendReport.metric_forecasts.map(safeForecast);
  const trendAnalysis = {
    status: trendReport.status,
    daily: safeTrendWindow(trendReport.daily),
    weekly: safeTrendWindow(trendReport.weekly),
    forecast_count: forecasts.filter(item => item.status === 'forecast_candidate').length,
    range_warning_count: forecasts.filter(item => item.status === 'range_warning').length,
    metric_forecasts: forecasts,
  };
  const heuristicCounts = countBy(recommendations.map(item => item.heuristic_signal), ['low', 'medium']);
  const kindCounts = countBy(events.map(event => event.kind), ['log', 'incident', 'ci_result', 'server_metric']);
  const severityCounts = countBy(events.map(event => event.severity), ['debug', 'info', 'warning', 'error', 'critical', 'unknown']);
  const incidents = analysis.clusters.map((cluster, index) => ({
    label: `مجموعة ${index + 1}`,
    event_count: cluster.count,
    severity_counts: cluster.severity_counts,
    hypotheses: cluster.hypotheses.map(item => ({
      cause_id: item.id,
      classification: 'POSSIBLE',
      heuristic_signal: item.heuristic_confidence,
      evidence_markers: item.evidence_markers,
    })),
  }));

  return {
    schema_version: 1,
    status: 'local_snapshot',
    summary: {
      event_count: events.length,
      kind_counts: kindCounts,
      severity_counts: severityCounts,
      log_event_count: analysis.log_events,
      ci_event_count: analysis.ci_events_considered,
      log_cluster_count: incidents.length,
      unknown_group_count: incidents.filter(item => item.hypotheses.length === 0).length,
      recommendation_count: recommendations.length,
      metric_series_count: anomalyAnalysis.metric_count,
      anomaly_candidate_count: anomalyAnalysis.candidate_count,
      forecast_count: trendAnalysis.forecast_count,
      trend_range_warning_count: trendAnalysis.range_warning_count,
      heuristic_signal_counts: heuristicCounts,
      feedback_ranked_recommendation_count: recommendations.filter(
        item => item.feedback_review_signal.status === 'ranking_eligible',
      ).length,
    },
    pipeline: {
      id: 'devobs-ai-local-1-7',
      mode: 'local_advisory_only',
      stages: [
        { id: 'AI-1', name: 'استقبال وتطبيع الأحداث', status: events.length ? 'ready' : 'no_data', count: events.length },
        { id: 'AI-2', name: 'كشف الشذوذ الإحصائي', status: anomalyAnalysis.metric_count ? 'ready' : 'no_metrics', count: anomalyAnalysis.metric_count, candidate_count: anomalyAnalysis.candidate_count },
        { id: 'AI-3', name: 'تحليل السجلات والفرضيات', status: analysis.log_events ? 'ready' : 'no_logs', count: incidents.length },
        { id: 'AI-4', name: 'مطابقة إرشادات التشغيل', status: recommendations.length ? 'ready' : 'no_matches', count: recommendations.length },
        { id: 'AI-5', name: 'ملخص الاتجاهات والاستقراء', status: trendReport.status, count: forecasts.length },
        { id: 'AI-6', name: 'ترتيب بملاحظات المشغّل', status: feedbackRecords.length ? 'applied' : 'no_feedback', count: feedbackRecords.length },
        { id: 'AI-7', name: 'لوحة الذكاء التشغيلي الموحدة', status: 'ready', count: 1 },
      ],
    },
    incidents,
    recommendations,
    anomaly_analysis: anomalyAnalysis,
    trend_analysis: trendAnalysis,
    limitations: [
      'المراحل AI-1 إلى AI-7 مسار محلي واحد من خوارزميات وقواعد حتمية؛ لا يوجد استدلال LLM أو اتصال بخدمة خارجية.',
      'الفرضيات احتمالية وإشارات الثقة heuristic وليست احتمالات معايرة.',
      'كشف الشذوذ والاستقراء اتجاهات أولية غير معايرة، ولا يثبتان سببًا أو يتنبآن بحادث موثوق.',
      'كل التوصيات للعرض فقط؛ يلزم اعتماد بشري ولا يوجد تنفيذ تلقائي.',
      'المعروض لقطة عند بدء الخادم؛ أعد تشغيله لتحديث الملفات المحلية.',
    ],
  };
}

async function loadSnapshot({ storePath, feedbackLedgerPath }) {
  if (typeof storePath !== 'string' || storePath.length === 0) reject('invalid_arguments');
  const events = await readEventStore(storePath);
  const feedback = feedbackLedgerPath ? await readFeedbackLedger(feedbackLedgerPath) : [];
  return buildDashboardSnapshot(events, feedback);
}

function send(response, status, contentType, body, method) {
  response.writeHead(status, {
    'Content-Type': contentType,
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Content-Security-Policy': "default-src 'none'; script-src 'self' https://accounts.google.com; style-src 'self'; connect-src 'self' https://docs.googleapis.com https://sheets.googleapis.com https://slides.googleapis.com https://chat.googleapis.com https://www.googleapis.com; frame-src https://accounts.google.com/gsi/; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'",
  });
  response.end(method === 'HEAD' ? undefined : body);
}

function sendError(response, status, code, method) {
  send(response, status, 'application/json; charset=utf-8', JSON.stringify({ error: code }), method);
}

export async function createDashboardServer({
  storePath,
  feedbackLedgerPath = null,
  googleDocsClientId = '',
  googleCalendarClientId = '',
  googleSheetsClientId = '',
  googleSlidesClientId = '',
  googleChatClientId = '',
}) {
  const snapshot = await loadSnapshot({ storePath, feedbackLedgerPath });
  if (typeof googleDocsClientId !== 'string' || googleDocsClientId.length > 256
    || (googleDocsClientId !== '' && !/^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$/.test(googleDocsClientId))) {
    reject('invalid_google_docs_client_id');
  }
  if (typeof googleCalendarClientId !== 'string' || googleCalendarClientId.length > 256
    || (googleCalendarClientId !== '' && !/^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$/.test(googleCalendarClientId))) {
    reject('invalid_google_calendar_client_id');
  }
  if (typeof googleSheetsClientId !== 'string' || googleSheetsClientId.length > 256
    || (googleSheetsClientId !== '' && !/^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$/.test(googleSheetsClientId))) {
    reject('invalid_google_sheets_client_id');
  }
  if (typeof googleSlidesClientId !== 'string' || googleSlidesClientId.length > 256
    || (googleSlidesClientId !== '' && !/^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$/.test(googleSlidesClientId))) {
    reject('invalid_google_slides_client_id');
  }
  if (typeof googleChatClientId !== 'string' || googleChatClientId.length > 256
    || (googleChatClientId !== '' && !/^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$/.test(googleChatClientId))) {
    reject('invalid_google_chat_client_id');
  }
  const jsonBodies = new Map([
    ['/api/v1/intelligence', JSON.stringify(snapshot)],
    ['/api/v1/summary', JSON.stringify({ schema_version: 1, ...snapshot.summary })],
    ['/api/v1/incidents', JSON.stringify({ schema_version: 1, incidents: snapshot.incidents })],
    ['/api/v1/recommendations', JSON.stringify({
      schema_version: 1,
      mode: 'suggestion_only',
      feedback_learning: { automatic_execution: false },
      recommendations: snapshot.recommendations,
    })],
    ['/api/v1/google-docs-config', JSON.stringify({
      enabled: googleDocsClientId !== '',
      client_id: googleDocsClientId,
      scope: 'https://www.googleapis.com/auth/drive.file',
    })],
    ['/api/v1/google-calendar-config', JSON.stringify({
      enabled: googleCalendarClientId !== '',
      client_id: googleCalendarClientId,
      scope: 'https://www.googleapis.com/auth/calendar.app.created',
    })],
    ['/api/v1/google-sheets-config', JSON.stringify({
      enabled: googleSheetsClientId !== '',
      client_id: googleSheetsClientId,
      scope: 'https://www.googleapis.com/auth/drive.file',
    })],
    ['/api/v1/google-slides-config', JSON.stringify({
      enabled: googleSlidesClientId !== '',
      client_id: googleSlidesClientId,
      scope: 'https://www.googleapis.com/auth/drive.file',
    })],
    ['/api/v1/google-chat-config', JSON.stringify({
      enabled: googleChatClientId !== '',
      client_id: googleChatClientId,
      scope: 'https://www.googleapis.com/auth/chat.messages.create',
    })],
  ]);
  const assets = new Map();
  for (const [route, file] of ASSET_FILES) {
    try {
      assets.set(route, await readFile(new URL(file, ASSET_ROOT)));
    } catch {
      reject('dashboard_asset_unavailable');
    }
  }

  let server;
  server = createServer((request, response) => {
    const address = request.socket.remoteAddress;
    const boundAddress = server.address();
    const port = boundAddress && typeof boundAddress === 'object' ? boundAddress.port : null;
    const expectedHost = port === null ? null : `${HOST}:${port}`;
    if (address !== HOST || !expectedHost || request.headers.host !== expectedHost) {
      sendError(response, 421, 'local_origin_required', request.method);
      return;
    }
    const expectedOrigin = `http://${expectedHost}`;
    if (request.headers.origin !== undefined && request.headers.origin !== expectedOrigin) {
      sendError(response, 403, 'same_origin_required', request.method);
      return;
    }
    if (!['GET', 'HEAD'].includes(request.method ?? '')) {
      request.resume();
      sendError(response, 405, 'method_not_allowed', request.method);
      return;
    }
    if (typeof request.url !== 'string' || request.url.length > MAX_URL_LENGTH) {
      sendError(response, 400, 'invalid_request', request.method);
      return;
    }
    let parsed;
    try {
      parsed = new URL(request.url, expectedOrigin);
    } catch {
      sendError(response, 400, 'invalid_request', request.method);
      return;
    }
    if (parsed.origin !== expectedOrigin || parsed.search || parsed.hash) {
      sendError(response, 404, 'not_found', request.method);
      return;
    }
    const json = jsonBodies.get(parsed.pathname);
    if (json !== undefined) {
      send(response, 200, 'application/json; charset=utf-8', json, request.method);
      return;
    }
    const asset = assets.get(parsed.pathname);
    if (asset !== undefined) {
      send(response, 200, CONTENT_TYPES.get(parsed.pathname), asset, request.method);
      return;
    }
    sendError(response, 404, 'not_found', request.method);
  });
  return server;
}

function parseArgs(args) {
  const options = {
    storePath: null,
    feedbackLedgerPath: null,
    googleDocsClientId: '',
    googleCalendarClientId: '',
    googleSheetsClientId: '',
    googleSlidesClientId: '',
    googleChatClientId: '',
    port: DEFAULT_PORT,
  };
  const seen = new Set();
  for (let index = 0; index < args.length; index++) {
    const flag = args[index];
    const value = args[index + 1];
    if (!value || value.startsWith('--') || seen.has(flag)) reject('invalid_arguments');
    seen.add(flag);
    if (flag === '--store' && options.storePath === null) options.storePath = value;
    else if (flag === '--feedback-ledger' && options.feedbackLedgerPath === null) options.feedbackLedgerPath = value;
    else if (flag === '--google-docs-client-id' && options.googleDocsClientId === '') options.googleDocsClientId = value;
    else if (flag === '--google-calendar-client-id' && options.googleCalendarClientId === '') options.googleCalendarClientId = value;
    else if (flag === '--google-sheets-client-id' && options.googleSheetsClientId === '') options.googleSheetsClientId = value;
    else if (flag === '--google-slides-client-id' && options.googleSlidesClientId === '') options.googleSlidesClientId = value;
    else if (flag === '--google-chat-client-id' && options.googleChatClientId === '') options.googleChatClientId = value;
    else if (flag === '--port' && options.port === DEFAULT_PORT) {
      if (!/^(?:0|[1-9]\d{0,4})$/.test(value) || Number(value) > 65_535) reject('invalid_arguments');
      options.port = Number(value);
    } else reject('invalid_arguments');
    index++;
  }
  if (!options.storePath) reject('invalid_arguments');
  return options;
}

function usage() {
  return 'Usage: node scripts/ai_intelligence/dashboard_server.mjs --store <local-jsonl-file> [--feedback-ledger <private-jsonl-file>] [--google-docs-client-id <public-oauth-client-id>] [--google-calendar-client-id <public-oauth-client-id>] [--google-sheets-client-id <public-oauth-client-id>] [--google-slides-client-id <public-oauth-client-id>] [--google-chat-client-id <public-oauth-client-id>] [--port <0-65535>]';
}

export async function main(args = process.argv.slice(2)) {
  let server;
  try {
    if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    const options = parseArgs(args);
    server = await createDashboardServer(options);
    await new Promise((resolve, rejectListen) => {
      server.once('error', rejectListen);
      server.listen(options.port, HOST, resolve);
    });
    const address = server.address();
    process.stdout.write(`ai-dashboard: http://${HOST}:${address.port}\n`);
    await new Promise(resolve => {
      const close = () => server.close(resolve);
      process.once('SIGINT', close);
      process.once('SIGTERM', close);
    });
    return 0;
  } catch (error) {
    const known = error instanceof DashboardError || error instanceof EventIngestError
      || error instanceof IncidentAnalysisError || error instanceof FeedbackLearningError
      || error instanceof RecommendationError || error instanceof AnomalyAnalysisError
      || error instanceof TrendAnalysisError;
    const code = known ? error.code : 'dashboard_unavailable';
    process.stderr.write(`ai-dashboard: ${code}\n${usage()}\n`);
    if (server?.listening) server.close(() => {});
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
