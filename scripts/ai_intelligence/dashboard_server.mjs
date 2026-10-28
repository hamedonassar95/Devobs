#!/usr/bin/env node
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readEventStore } from './event_ingest.mjs';
import { IncidentAnalysisError, analyzeIncidentEvents } from './incident_analysis.mjs';
import { FeedbackLearningError, applyFeedbackLearning, readFeedbackLedger } from './feedback_learning.mjs';
import { RecommendationError, recommendFromIncidentAnalysis } from './recommendations.mjs';

const HOST = '127.0.0.1';
const DEFAULT_PORT = 8765;
const MAX_URL_LENGTH = 2_048;
const ASSET_ROOT = new URL('./dashboard_assets/', import.meta.url);
const CONTENT_TYPES = new Map([
  ['/', 'text/html; charset=utf-8'],
  ['/dashboard.js', 'text/javascript; charset=utf-8'],
  ['/dashboard.css', 'text/css; charset=utf-8'],
]);
const ASSET_FILES = new Map([
  ['/', 'index.html'],
  ['/dashboard.js', 'dashboard.js'],
  ['/dashboard.css', 'dashboard.css'],
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

export function buildDashboardSnapshot(events, feedbackRecords = []) {
  if (!Array.isArray(events)) reject('invalid_snapshot_input');
  const analysis = analyzeIncidentEvents(events);
  const recommendationReport = recommendFromIncidentAnalysis(analysis);
  const learnedReport = applyFeedbackLearning(recommendationReport, feedbackRecords);
  const recommendations = learnedReport.recommendations.map(safeRecommendation);
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
      heuristic_signal_counts: heuristicCounts,
      feedback_ranked_recommendation_count: recommendations.filter(
        item => item.feedback_review_signal.status === 'ranking_eligible',
      ).length,
    },
    incidents,
    recommendations,
    limitations: [
      'الفرضيات احتمالية وإشارات الثقة heuristic وليست احتمالات معايرة.',
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
    'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'",
  });
  response.end(method === 'HEAD' ? undefined : body);
}

function sendError(response, status, code, method) {
  send(response, status, 'application/json; charset=utf-8', JSON.stringify({ error: code }), method);
}

export async function createDashboardServer({ storePath, feedbackLedgerPath = null }) {
  const snapshot = await loadSnapshot({ storePath, feedbackLedgerPath });
  const jsonBodies = new Map([
    ['/api/v1/summary', JSON.stringify({ schema_version: 1, ...snapshot.summary })],
    ['/api/v1/incidents', JSON.stringify({ schema_version: 1, incidents: snapshot.incidents })],
    ['/api/v1/recommendations', JSON.stringify({
      schema_version: 1,
      mode: 'suggestion_only',
      feedback_learning: { automatic_execution: false },
      recommendations: snapshot.recommendations,
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
  const options = { storePath: null, feedbackLedgerPath: null, port: DEFAULT_PORT };
  const seen = new Set();
  for (let index = 0; index < args.length; index++) {
    const flag = args[index];
    const value = args[index + 1];
    if (!value || value.startsWith('--') || seen.has(flag)) reject('invalid_arguments');
    seen.add(flag);
    if (flag === '--store' && options.storePath === null) options.storePath = value;
    else if (flag === '--feedback-ledger' && options.feedbackLedgerPath === null) options.feedbackLedgerPath = value;
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
  return 'Usage: node scripts/ai_intelligence/dashboard_server.mjs --store <local-jsonl-file> [--feedback-ledger <private-jsonl-file>] [--port <0-65535>]';
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
      || error instanceof RecommendationError;
    const code = known ? error.code : 'dashboard_unavailable';
    process.stderr.write(`ai-dashboard: ${code}\n${usage()}\n`);
    if (server?.listening) server.close(() => {});
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
