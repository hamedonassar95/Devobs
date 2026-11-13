#!/usr/bin/env node
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ingestText, readEventStore } from './ai_intelligence/event_ingest.mjs';
import { createDashboardServer } from './ai_intelligence/dashboard_server.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_FIXTURE = path.join(ROOT, 'tests/fixtures/intelligence_eval_cases.json');
const HOST = '127.0.0.1';
const RAW_LOG_SENTINEL = 'LOCAL_ADVISORY_RAW_LOG_SENTINEL';
const MAX_FIXTURE_BYTES = 65_536;
const MAX_FIXTURE_CASES = 32;
const MAX_EVENTS = 100;
const MAX_API_RESPONSE_BYTES = 131_072;
const REQUEST_TIMEOUT_MS = 5_000;
const SHUTDOWN_TIMEOUT_MS = 5_000;
const BASE_TIME = Date.parse('2026-10-28T08:00:00.000Z');
const EXPECTED_STAGES = ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7'];
const GOOGLE_CONFIG_ROUTES = [
  '/api/v1/google-docs-config',
  '/api/v1/google-calendar-config',
  '/api/v1/google-sheets-config',
  '/api/v1/google-slides-config',
  '/api/v1/google-chat-config',
  '/api/v1/google-tasks-config',
  '/api/v1/google-gmail-config',
];

export class LocalAdvisoryAcceptanceError extends Error {
  constructor(code) {
    super(code);
    this.name = 'LocalAdvisoryAcceptanceError';
    this.code = code;
  }
}

function reject(code) {
  throw new LocalAdvisoryAcceptanceError(code);
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function hasExactKeys(value, expected) {
  return isPlainObject(value) && Object.keys(value).length === expected.length
    && Object.keys(value).every(key => expected.includes(key));
}

export function parseSyntheticFixture(text) {
  if (typeof text !== 'string' || Buffer.byteLength(text, 'utf8') > MAX_FIXTURE_BYTES) reject('invalid_fixture');
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    reject('invalid_fixture');
  }
  if (!Array.isArray(parsed) || parsed.length === 0 || parsed.length > MAX_FIXTURE_CASES) reject('invalid_fixture');

  const categories = new Set(['ci_failure', 'high_error_rate', 'capacity_pressure', 'unknown']);
  return parsed.map(item => {
    if (!hasExactKeys(item, ['case_id', 'signals', 'expected_category'])
      || typeof item.case_id !== 'string' || !/^[a-z][a-z0-9_]{0,39}$/.test(item.case_id)
      || !categories.has(item.expected_category)
      || !hasExactKeys(item.signals, ['failed_checks', 'error_rate_pct', 'capacity_pct'])
      || !Number.isSafeInteger(item.signals.failed_checks) || item.signals.failed_checks < 0 || item.signals.failed_checks > 100
      || !Number.isFinite(item.signals.error_rate_pct) || item.signals.error_rate_pct < 0 || item.signals.error_rate_pct > 100
      || !Number.isFinite(item.signals.capacity_pct) || item.signals.capacity_pct < 0 || item.signals.capacity_pct > 100) {
      reject('invalid_fixture');
    }
    return {
      case_id: item.case_id,
      signals: {
        failed_checks: item.signals.failed_checks,
        error_rate_pct: item.signals.error_rate_pct,
        capacity_pct: item.signals.capacity_pct,
      },
      expected_category: item.expected_category,
    };
  });
}

function toRawEvent({ minute, source, kind, severity, data }) {
  return {
    schema_version: 1,
    occurred_at: new Date(BASE_TIME + minute * 60_000).toISOString(),
    source,
    kind,
    severity,
    data,
  };
}

function createSyntheticInput(cases) {
  const events = [];
  for (const [index, item] of cases.entries()) {
    events.push(toRawEvent({
      minute: index,
      source: 'operator',
      kind: 'incident',
      severity: 'warning',
      data: { summary: `Synthetic incident case ${item.case_id}.`, status: 'open', impact: 'minor' },
    }));
    events.push(toRawEvent({
      minute: index,
      source: 'application',
      kind: 'log',
      severity: item.signals.failed_checks ? 'error' : 'info',
      data: {
        stream: 'application',
        message: item.signals.failed_checks
          ? `${RAW_LOG_SENTINEL} case-${item.case_id} ETIMEDOUT synthetic test timeout`
          : `${RAW_LOG_SENTINEL} case-${item.case_id} synthetic observation`,
      },
    }));
    if (item.signals.failed_checks > 0) {
      events.push(toRawEvent({
        minute: index,
        source: 'github_actions',
        kind: 'ci_result',
        severity: 'error',
        data: { workflow: 'synthetic-ci', job: 'synthetic-check', conclusion: 'failure', commit_sha: null },
      }));
    }
  }

  const errorRate = Math.max(...cases.map(item => item.signals.error_rate_pct));
  const capacity = Math.max(...cases.map(item => item.signals.capacity_pct));
  const metricSeries = [
    { name: 'error_rate', unit: 'percent', values: [1, 1.1, 0.9, 1, 1.05, Math.max(3, errorRate)] },
    { name: 'memory_percent', unit: 'percent', values: [10, 10.2, 9.8, 10.1, 9.9, Math.max(30, capacity)] },
  ];
  for (const series of metricSeries) {
    for (const [minute, value] of series.values.entries()) {
      events.push(toRawEvent({
        minute: cases.length + minute,
        source: 'server',
        kind: 'server_metric',
        severity: 'info',
        data: { name: series.name, value, unit: series.unit },
      }));
    }
  }
  if (events.length > MAX_EVENTS) reject('fixture_exceeds_event_bound');
  return `${events.map(event => JSON.stringify(event)).join('\n')}\n`;
}

async function listenOnLoopback(server) {
  await new Promise((resolve, rejectPromise) => {
    const onError = () => {
      server.removeListener('error', onError);
      rejectPromise(new LocalAdvisoryAcceptanceError('dashboard_start_failed'));
    };
    server.once('error', onError);
    server.listen(0, HOST, () => {
      server.removeListener('error', onError);
      resolve();
    });
  });
  const address = server.address();
  if (!address || typeof address === 'string' || address.address !== HOST
    || !Number.isInteger(address.port) || address.port < 1 || address.port > 65_535) {
    reject('dashboard_invalid_address');
  }
  return address.port;
}

function getLocalJson(port, route) {
  return new Promise((resolve, rejectPromise) => {
    const request = http.request({
      hostname: HOST,
      port,
      path: route,
      method: 'GET',
      agent: false,
      headers: { host: `${HOST}:${port}`, accept: 'application/json' },
    }, response => {
      const chunks = [];
      let bytes = 0;
      const declaredLength = Number(response.headers['content-length']);
      if (Number.isFinite(declaredLength) && declaredLength > MAX_API_RESPONSE_BYTES) {
        response.destroy();
        rejectPromise(new LocalAdvisoryAcceptanceError('api_response_exceeds_bound'));
        return;
      }
      response.on('data', chunk => {
        bytes += chunk.length;
        if (bytes > MAX_API_RESPONSE_BYTES) {
          response.destroy(new LocalAdvisoryAcceptanceError('api_response_exceeds_bound'));
          return;
        }
        chunks.push(chunk);
      });
      response.once('error', error => rejectPromise(error instanceof LocalAdvisoryAcceptanceError
        ? error : new LocalAdvisoryAcceptanceError('api_request_failed')));
      response.once('end', () => {
        const body = Buffer.concat(chunks).toString('utf8');
        if (response.statusCode !== 200 || response.headers['content-type']?.startsWith('application/json') !== true) {
          rejectPromise(new LocalAdvisoryAcceptanceError('unexpected_api_response'));
          return;
        }
        try {
          resolve({ body: JSON.parse(body), bytes });
        } catch {
          rejectPromise(new LocalAdvisoryAcceptanceError('malformed_api_response'));
        }
      });
    });
    request.setTimeout(REQUEST_TIMEOUT_MS, () => request.destroy(new LocalAdvisoryAcceptanceError('api_request_timeout')));
    request.once('error', error => rejectPromise(error instanceof LocalAdvisoryAcceptanceError
      ? error : new LocalAdvisoryAcceptanceError('api_request_failed')));
    request.end();
  });
}

function assertSafeSnapshot(snapshot, apiBytes, tempDirectory) {
  if (!isPlainObject(snapshot) || snapshot.schema_version !== 1 || snapshot.status !== 'local_snapshot'
    || snapshot.pipeline?.mode !== 'local_advisory_only'
    || !Array.isArray(snapshot.pipeline?.stages)
    || !Array.isArray(snapshot.incidents) || !Array.isArray(snapshot.recommendations)
    || !isPlainObject(snapshot.summary)) reject('unexpected_snapshot_shape');
  const stageIds = snapshot.pipeline.stages.map(stage => stage?.id);
  if (JSON.stringify(stageIds) !== JSON.stringify(EXPECTED_STAGES)) reject('unexpected_pipeline_stages');
  for (const stage of snapshot.pipeline.stages) {
    if (!Number.isSafeInteger(stage.count) || stage.count < 0 || stage.count > MAX_EVENTS) reject('unbounded_pipeline_output');
  }
  if (!Number.isSafeInteger(snapshot.summary.event_count) || snapshot.summary.event_count < 1
    || snapshot.summary.event_count > MAX_EVENTS || snapshot.incidents.length > MAX_EVENTS
    || snapshot.recommendations.length > MAX_EVENTS || apiBytes > MAX_API_RESPONSE_BYTES) reject('unbounded_api_output');
  for (const recommendation of snapshot.recommendations) {
    if (recommendation.automatic_execution !== false || recommendation.requires_human_approval !== true) {
      reject('unsafe_recommendation_contract');
    }
  }
  const serialized = JSON.stringify(snapshot);
  for (const forbidden of [RAW_LOG_SENTINEL, tempDirectory, 'cluster_fingerprint', 'feedback_key', 'commit_sha', 'occurred_at']) {
    if (serialized.includes(forbidden)) reject('api_privacy_check_failed');
  }
  if (snapshot.summary.anomaly_candidate_count < 1 || snapshot.summary.recommendation_count < 1) {
    reject('expected_advisory_output_missing');
  }
}

function assertSuggestionResponse(response, responseBytes, tempDirectory) {
  if (!isPlainObject(response) || response.schema_version !== 1 || response.mode !== 'suggestion_only'
    || response.feedback_learning?.automatic_execution !== false || !Array.isArray(response.recommendations)
    || response.recommendations.length > MAX_EVENTS
    || responseBytes > MAX_API_RESPONSE_BYTES
    || response.recommendations.some(item => item.automatic_execution !== false || item.requires_human_approval !== true)) {
    reject('unsafe_recommendation_response');
  }
  const serialized = JSON.stringify(response);
  if (serialized.includes(RAW_LOG_SENTINEL) || serialized.includes(tempDirectory)
    || serialized.includes('cluster_fingerprint') || serialized.includes('feedback_key')) reject('api_privacy_check_failed');
}

function assertIntegrationsDisabled(responses) {
  if (responses.length !== GOOGLE_CONFIG_ROUTES.length || responses.some(response => !isPlainObject(response)
    || response.enabled !== false || response.client_id !== '')) reject('external_integration_not_disabled');
}

function closeDashboard(server) {
  if (!server?.listening) return Promise.resolve(true);
  return new Promise(resolve => {
    const timer = setTimeout(() => {
      server.closeAllConnections();
      resolve(false);
    }, SHUTDOWN_TIMEOUT_MS);
    server.close(error => {
      clearTimeout(timer);
      resolve(!error);
    });
  });
}

/** Run the already-implemented AI-1..AI-7 data path and dashboard using synthetic-only input. */
export async function runLocalAdvisoryAcceptance({ fixtureText, tempParent = os.tmpdir() } = {}) {
  const fixture = parseSyntheticFixture(fixtureText ?? await readFile(DEFAULT_FIXTURE, 'utf8'));
  const inputText = createSyntheticInput(fixture);
  const tempDirectory = await mkdtemp(path.join(tempParent, 'devobs-local-advisory-v01-'));
  const inputPath = path.join(tempDirectory, 'synthetic-events.jsonl');
  const storePath = path.join(tempDirectory, 'events.jsonl');
  let server;
  let result;
  let operationError;
  let stopped = true;
  let cleaned = false;

  try {
    await writeFile(inputPath, inputText, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
    const ingest = await ingestText(await readFile(inputPath, 'utf8'), storePath);
    const storedEvents = await readEventStore(storePath);
    if (ingest.accepted !== storedEvents.length || ingest.duplicateIgnored !== 0
      || storedEvents.length !== inputText.trimEnd().split('\n').length) reject('ingestion_contract_failed');

    server = await createDashboardServer({ storePath });
    const port = await listenOnLoopback(server);

    const [intelligence, recommendations, ...googleConfigs] = await Promise.all([
      getLocalJson(port, '/api/v1/intelligence'),
      getLocalJson(port, '/api/v1/recommendations'),
      ...GOOGLE_CONFIG_ROUTES.map(route => getLocalJson(port, route)),
    ]);
    assertSafeSnapshot(intelligence.body, intelligence.bytes, tempDirectory);
    assertSuggestionResponse(recommendations.body, recommendations.bytes, tempDirectory);
    assertIntegrationsDisabled(googleConfigs.map(item => item.body));

    const stages = intelligence.body.pipeline.stages.map(stage => ({
      id: stage.id,
      status: stage.status,
      count: stage.count,
    }));
    result = {
      schema_version: 1,
      status: 'LOCAL_ACCEPTANCE_PASSED',
      scope: 'offline_synthetic_only',
      pipeline_mode: 'local_advisory_only',
      event_count: intelligence.body.summary.event_count,
      anomaly_candidate_count: intelligence.body.summary.anomaly_candidate_count,
      recommendation_count: intelligence.body.summary.recommendation_count,
      stages,
      api: {
        route: '/api/v1/intelligence',
        method: 'GET',
        status: 200,
        response_bytes: intelligence.bytes,
        response_limit_bytes: MAX_API_RESPONSE_BYTES,
      },
      safeguards: {
        raw_log_exposed: false,
        automatic_execution: false,
        deployment_executed: false,
        remediation_executed: false,
        google_configs_enabled: false,
        firebase_or_model_runtime_started: false,
      },
      production_ready: false,
    };
  } catch (error) {
    operationError = error instanceof LocalAdvisoryAcceptanceError
      ? error : new LocalAdvisoryAcceptanceError('acceptance_failed');
  } finally {
    stopped = await closeDashboard(server);
    try {
      await rm(tempDirectory, { recursive: true, force: true });
      cleaned = true;
    } catch {
      cleaned = false;
    }
  }

  if (!stopped) operationError ??= new LocalAdvisoryAcceptanceError('dashboard_shutdown_failed');
  if (!cleaned) operationError ??= new LocalAdvisoryAcceptanceError('temporary_cleanup_failed');
  if (operationError) throw operationError;
  return { ...result, safeguards: { ...result.safeguards, dashboard_shutdown: 'graceful', temporary_artifacts_removed: true } };
}

function usage() {
  return 'Usage: node scripts/local_advisory_acceptance.mjs';
}

export async function main(args = process.argv.slice(2)) {
  if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
    process.stdout.write(`${usage()}\n`);
    return 0;
  }
  if (args.length !== 0) {
    process.stderr.write(`local-advisory-acceptance: invalid_arguments\n${usage()}\n`);
    return 2;
  }
  try {
    const result = await runLocalAdvisoryAcceptance();
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return 0;
  } catch (error) {
    const code = error instanceof LocalAdvisoryAcceptanceError ? error.code : 'acceptance_failed';
    process.stderr.write(`local-advisory-acceptance: ${code}\n${usage()}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
