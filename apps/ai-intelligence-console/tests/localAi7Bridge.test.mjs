import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import http from 'node:http';
import express from 'express';
import { createLocalAi7Handler } from '../localAi7Bridge.ts';
import { normalizeEvent } from '../../../scripts/ai_intelligence/event_ingest.mjs';
import { buildDashboardSnapshot } from '../../../scripts/ai_intelligence/dashboard_server.mjs';

const payload = () => ({
  schema_version: 1, status: 'local_snapshot',
  summary: {
    event_count: 24, log_cluster_count: 2, recommendation_count: 0,
    anomaly_candidate_count: 2,
  },
  pipeline: {
    id: 'devobs-ai-local-1-7', mode: 'local_advisory_only',
    stages: Array.from({ length: 7 }, (_, i) => ({
      id: `AI-${i + 1}`, name: 'private source', status: 'ready', count: 1,
    })),
  },
  incidents: [{ label: 'SENSITIVE_RAW_LOG_MUST_NOT_LEAK' }],
  recommendations: [],
});

async function fixture(t, opts = {}) {
  const app = express();
  const server = createServer(app);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const port = server.address().port;
  t.after(() => new Promise(resolve => server.close(resolve)));
  app.get('/api/local-ai7/summary', createLocalAi7Handler({
    enabled: opts.enabled ?? true,
    bindHost: opts.bindHost ?? '127.0.0.1',
    consolePort: port,
    fetchImpl: opts.fetchImpl ?? (async () => Response.json(payload())),
  }));
  async function request(headers = {}) {
    return new Promise((resolve, reject) => {
      http.get({ hostname: '127.0.0.1', port, path: '/api/local-ai7/summary', headers }, response => {
        const body = [];
        response.on('data', chunk => body.push(chunk));
        response.on('end', () => resolve({ status: response.statusCode, headers: response.headers,
          data: JSON.parse(Buffer.concat(body).toString('utf8')) }));
      }).on('error', reject);
    });
  }
  return { request };
}

test('disabled by default fails closed without making a fetch', async t => {
  let calls = 0;
  const { request } = await fixture(t, { enabled: false, fetchImpl: async () => { calls++; throw Error('must not call'); } });
  const response = await request();
  assert.equal(response.status, 503);
  assert.equal(calls, 0);
  assert.equal(response.headers['cache-control'], 'no-store');
});

test('valid local AI-7 snapshot returns only bounded aggregate fields', async t => {
  let requested;
  const { request } = await fixture(t, {
    fetchImpl: async (url, options) => {
      requested = { url, options };
      return Response.json(payload());
    },
  });
  const response = await request();
  assert.equal(response.status, 200);
  assert.equal(requested.url, 'http://127.0.0.1:8765/api/v1/intelligence');
  assert.equal(requested.options.redirect, 'error');
  assert.equal(response.data.read_only, true);
  assert.equal(response.data.mode, 'local_advisory_only');
  assert.equal(response.data.summary.event_count, 24);
  assert.equal(response.data.summary.anomaly_candidate_count, 2);
  assert.deepEqual(response.data.stages.map(x => x.id), ['AI-1','AI-2','AI-3','AI-4','AI-5','AI-6','AI-7']);
  assert.doesNotMatch(JSON.stringify(response.data), /SENSITIVE_RAW_LOG_MUST_NOT_LEAK|private source/);
});

test('non-loopback host rejects the bridge even when feature is enabled', async t => {
  let calls = 0;
  const { request } = await fixture(t, { bindHost: '0.0.0.0', fetchImpl: async () => { calls++; return Response.json(payload()); } });
  assert.equal((await request()).status, 503);
  assert.equal(calls, 0);
});

test('foreign origin and Host header cannot read a localhost snapshot', async t => {
  let calls = 0;
  const { request } = await fixture(t, { fetchImpl: async () => { calls++; return Response.json(payload()); } });
  assert.equal((await request({ origin: 'https://evil.invalid' })).status, 403);
  assert.equal((await request({ host: 'evil.invalid' })).status, 403);
  assert.equal(calls, 0);
});

test('malformed upstream data is never mistaken for analysis', async t => {
  const malformed = payload();
  malformed.pipeline.mode = 'live_recovery';
  const { request } = await fixture(t, { fetchImpl: async () => Response.json(malformed) });
  const res = await request();
  assert.equal(res.status, 503);
  assert.deepEqual(res.data, { error: 'local_ai7_unavailable' });
});

test('redirects and oversized bodies fail closed without exposing content', async t => {
  const redir = await fixture(t, { fetchImpl: async () => new Response(null, { status: 302, headers: { location: 'https://evil.invalid' } }) });
  assert.equal((await redir.request()).status, 503);
  const oversized = await fixture(t, { fetchImpl: async () => new Response('z'.repeat(70000), { headers: { 'content-type': 'application/json' } }) });
  assert.equal((await oversized.request()).status, 503);
});

test('the actual AI-7 engine aggregate contract is accepted without forwarding raw logs', async t => {
  const event = normalizeEvent({
    schema_version: 1,
    occurred_at: '2026-11-15T20:00:00.000Z',
    source: 'application', kind: 'log', severity: 'error',
    data: { stream: 'stderr', message: 'PRIVATE_EVENT_DIAGNOSTIC_MUST_NOT_APPEAR ETIMEDOUT request timed out' },
  });
  const realSnapshot = buildDashboardSnapshot([event]);
  const { request } = await fixture(t, { fetchImpl: async () => Response.json(realSnapshot) });
  const response = await request();
  assert.equal(response.status, 200);
  assert.equal(response.data.summary.event_count, 1);
  assert.equal(response.data.stages.length, 7);
  assert.equal(response.data.summary.recommendation_count, 1);
  assert.equal(response.data.recommendations.length, 1);
  assert.equal(response.data.recommendations[0].cause_id, 'timeout');
  assert.equal(response.data.recommendations[0].classification, 'POSSIBLE');
  assert.equal(response.data.recommendations[0].automatic_execution, false);
  assert.deepEqual(response.data.recommendations[0].evidence_markers, ['ETIMEDOUT', 'timed_out']);
  assert.doesNotMatch(JSON.stringify(response.data), /PRIVATE_EVENT_DIAGNOSTIC_MUST_NOT_APPEAR/);
});

function advisory(overrides = {}) {
  return {
    review_order: 1, cause_id: 'timeout', classification: 'POSSIBLE',
    heuristic_signal: 'medium', event_count: 3,
    evidence_markers: ['ETIMEDOUT'],
    runbook_title: 'UNTRUSTED_UPSTREAM_FREE_TEXT_DO_NOT_FORWARD',
    read_only_checks: ['UNTRUSTED_UPSTREAM_FREE_TEXT_DO_NOT_FORWARD'],
    requires_human_approval: true, automatic_execution: false,
    ...overrides,
  };
}

test('AI-4 shows real bounded cause, heuristic evidence and manual-review-only state', async t => {
  const raw = payload();
  raw.summary.recommendation_count = 1;
  raw.recommendations = [advisory()];
  const { request } = await fixture(t, { fetchImpl: async () => Response.json(raw) });
  const response = await request();
  assert.equal(response.status, 200);
  assert.equal(response.data.summary.recommendation_count, 1);
  assert.deepEqual(response.data.recommendations, [{
    review_order: 1, cause_id: 'timeout', classification: 'POSSIBLE',
    heuristic_signal: 'medium', event_count: 3,
    evidence_markers: ['ETIMEDOUT'],
    requires_human_approval: true, automatic_execution: false,
  }]);
  assert.doesNotMatch(JSON.stringify(response.data), /UNTRUSTED_UPSTREAM_FREE_TEXT_DO_NOT_FORWARD/);
});

test('unknown or unsafe recommendation evidence never passes the local bridge', async t => {
  const rejected = [
    advisory({ automatic_execution: true }),
    advisory({ requires_human_approval: false }),
    advisory({ classification: 'CONFIRMED' }),
    advisory({ cause_id: 'untrusted_hypothesis' }),
    advisory({ evidence_markers: ['SECRET_PATH_NOT_AN_EVIDENCE_MARKER'] }),
  ];
  for (const invalid of rejected) {
    const raw = payload();
    raw.summary.recommendation_count = 1;
    raw.recommendations = [invalid];
    const { request } = await fixture(t, { fetchImpl: async () => Response.json(raw) });
    const result = await request();
    assert.equal(result.status, 503);
    assert.deepEqual(result.data, { error: 'local_ai7_unavailable' });
  }
});

test('AI-4 fails closed on inconsistent totals and returns at most five suggestions', async t => {
  const mismatch = payload();
  mismatch.summary.recommendation_count = 2;
  mismatch.recommendations = [advisory()];
  const rejected = await fixture(t, { fetchImpl: async () => Response.json(mismatch) });
  assert.equal((await rejected.request()).status, 503);

  const many = payload();
  many.recommendations = Array.from({ length: 6 }, (_, index) =>
    advisory({ review_order: index + 1 }));
  many.summary.recommendation_count = 6;
  const result = await fixture(t, { fetchImpl: async () => Response.json(many) });
  const response = await result.request();
  assert.equal(response.status, 200);
  assert.equal(response.data.summary.recommendation_count, 6);
  assert.equal(response.data.recommendations.length, 5);
  assert.equal(response.data.recommendations[4].review_order, 5);
});
