import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { ingestText, normalizeEvent, readEventStore } from '../scripts/ai_intelligence/event_ingest.mjs';
import { analyzeIncidentEvents } from '../scripts/ai_intelligence/incident_analysis.mjs';
import { createDashboardServer, buildDashboardSnapshot } from '../scripts/ai_intelligence/dashboard_server.mjs';
import { recordRecommendationFeedback } from '../scripts/ai_intelligence/feedback_learning.mjs';

const DASHBOARD_ASSETS = fileURLToPath(new URL('../scripts/ai_intelligence/dashboard_assets/', import.meta.url));
const RAW_MARKER = 'SYNTHETIC_DASHBOARD_RAW_LOG_MUST_NOT_LEAK';
const CASES = [
  ['timeout', `${RAW_MARKER} ETIMEDOUT request timed out`],
  ['connection', `${RAW_MARKER} ECONNRESET connection closed`],
  ['dns', `${RAW_MARKER} ENOTFOUND host lookup`],
  ['permission', `${RAW_MARKER} EACCES permission denied`],
  ['dependency', `${RAW_MARKER} module not found while loading`],
  ['memory', `${RAW_MARKER} heap out of memory`],
];

async function tempDir(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'devobs-ai7-dashboard-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  return directory;
}

function inputLine(event) {
  return JSON.stringify({
    schema_version: event.schema_version,
    occurred_at: event.occurred_at,
    source: event.source,
    kind: event.kind,
    severity: event.severity,
    data: event.data,
  }) + '\n';
}

async function makeStore(t) {
  const directory = await tempDir(t);
  const storePath = path.join(directory, 'events.jsonl');
  const events = CASES.map(([cause, message], index) => normalizeEvent({
    schema_version: 1,
    occurred_at: new Date(Date.UTC(2026, 9, 28, 8, index)).toISOString(),
    source: 'application',
    kind: 'log',
    severity: index === 0 ? 'error' : 'warning',
    data: { stream: 'stderr', message: `${message} case-${index}` },
  }));
  await ingestText(events.map(inputLine).join(''), storePath);
  return { directory, storePath, events };
}

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return server.address().port;
}

function request(port, route, { method = 'GET', host, origin } = {}) {
  return new Promise((resolve, reject) => {
    const headers = { host: host ?? `127.0.0.1:${port}` };
    if (origin !== undefined) headers.origin = origin;
    const req = http.request({ host: '127.0.0.1', port, path: route, method, headers }, response => {
      const chunks = [];
      response.on('data', chunk => chunks.push(chunk));
      response.on('end', () => resolve({
        status: response.statusCode,
        headers: response.headers,
        body: Buffer.concat(chunks).toString('utf8'),
      }));
    });
    req.on('error', reject);
    req.end();
  });
}

test('six-case synthetic rule-coverage set yields the expected cause category only', () => {
  let matched = 0;
  for (const [expectedCause, message] of CASES) {
    const event = normalizeEvent({
      schema_version: 1,
      occurred_at: '2026-10-28T08:00:00Z',
      source: 'application',
      kind: 'log',
      severity: 'error',
      data: { stream: 'stderr', message },
    });
    const report = analyzeIncidentEvents([event]);
    const predicted = report.clusters.flatMap(cluster => cluster.hypotheses).map(item => item.id);
    assert.deepEqual(predicted, [expectedCause]);
    matched++;
  }
  assert.equal(matched, 6);
});

test('read-only local API returns bounded aggregates and hides raw log/path/hash identifiers', async t => {
  const { directory, storePath, events } = await makeStore(t);
  const ledgerPath = path.join(directory, 'feedback.jsonl');
  for (const [index, decision] of ['accepted', 'accepted', 'rejected'].entries()) {
    await recordRecommendationFeedback({
      ledgerPath,
      recommendationKey: `sha256:${String(index + 1).repeat(64)}`,
      causeId: 'timeout',
      decision,
      recordedAt: `2026-10-28T08:0${index}:00.000Z`,
    });
  }
  const beforeStore = await readFile(storePath, 'utf8');
  const beforeLedger = await readFile(ledgerPath, 'utf8');
  const server = await createDashboardServer({ storePath, feedbackLedgerPath: ledgerPath });
  const port = await listen(server);
  t.after(() => new Promise(resolve => server.close(resolve)));

  const [summaryResponse, incidentsResponse, recommendationsResponse] = await Promise.all([
    request(port, '/api/v1/summary'),
    request(port, '/api/v1/incidents'),
    request(port, '/api/v1/recommendations'),
  ]);
  assert.equal(summaryResponse.status, 200);
  assert.equal(incidentsResponse.status, 200);
  assert.equal(recommendationsResponse.status, 200);
  const summary = JSON.parse(summaryResponse.body);
  const incidents = JSON.parse(incidentsResponse.body);
  const recommendations = JSON.parse(recommendationsResponse.body);
  assert.equal(summary.event_count, events.length);
  assert.equal(summary.kind_counts.log, events.length);
  assert.ok(incidents.incidents.length > 0);
  assert.ok(recommendations.recommendations.some(item => item.cause_id === 'timeout'));
  const timeout = recommendations.recommendations.find(item => item.cause_id === 'timeout');
  assert.equal(timeout.feedback_review_signal.status, 'ranking_eligible');
  assert.equal(timeout.requires_human_approval, true);
  assert.equal(timeout.automatic_execution, false);

  const combined = `${summaryResponse.body}\n${incidentsResponse.body}\n${recommendationsResponse.body}`;
  for (const forbidden of [RAW_MARKER, storePath, 'cluster_fingerprint', 'feedback_key', 'commit_sha', 'occurred_at']) {
    assert.equal(combined.includes(forbidden), false, `leaked ${forbidden}`);
  }
  assert.equal(await readFile(storePath, 'utf8'), beforeStore);
  assert.equal(await readFile(ledgerPath, 'utf8'), beforeLedger);
  assert.equal((await stat(ledgerPath)).mode & 0o077, 0);
});

test('server is loopback-only, same-origin, read-only, and emits browser hardening headers', async t => {
  const { storePath } = await makeStore(t);
  const server = await createDashboardServer({ storePath });
  const port = await listen(server);
  t.after(() => new Promise(resolve => server.close(resolve)));
  const origin = `http://127.0.0.1:${port}`;

  const page = await request(port, '/', { origin });
  assert.equal(page.status, 200);
  assert.match(page.headers['content-security-policy'], /default-src 'none'/);
  assert.equal(page.headers['access-control-allow-origin'], undefined);
  assert.match(page.body, /lang="ar" dir="rtl"/);
  assert.match(page.body, /dashboard\.js/);

  const script = await request(port, '/dashboard.js', { origin });
  assert.equal(script.status, 200);
  assert.match(script.body, /textContent/);
  assert.doesNotMatch(script.body, /innerHTML/);
  assert.doesNotMatch(script.body, /https?:\/\//);

  assert.equal((await request(port, '/api/v1/summary', { host: `localhost:${port}` })).status, 421);
  assert.equal((await request(port, '/api/v1/summary', { origin: 'https://untrusted.example' })).status, 403);
  assert.equal((await request(port, '/api/v1/summary?extra=1', { origin })).status, 404);
  assert.equal((await request(port, '/api/v1/summary', { method: 'POST', origin })).status, 405);
  assert.equal((await request(port, '/unknown', { origin })).status, 404);
});

test('dashboard snapshot never embeds event messages or source identifiers', () => {
  const snapshot = buildDashboardSnapshot([normalizeEvent({
    schema_version: 1,
    occurred_at: '2026-10-28T08:00:00Z',
    source: 'application',
    kind: 'log',
    severity: 'error',
    data: { stream: 'stderr', message: `${RAW_MARKER} ETIMEDOUT` },
  })]);
  const output = JSON.stringify(snapshot);
  assert.equal(output.includes(RAW_MARKER), false);
  assert.equal(output.includes('event_id'), false);
  assert.equal(output.includes('fingerprint'), false);
  assert.equal(output.includes('feedback_key'), false);
  assert.match(output, /heuristic/);
});
