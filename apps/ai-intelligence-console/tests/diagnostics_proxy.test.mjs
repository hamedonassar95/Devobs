import assert from 'node:assert/strict';
import { once } from 'node:events';
import express from 'express';
import { test } from 'node:test';
import { createDiagnosticsHandler } from '../diagnosticsProxy.ts';

const settings = {
  DEVOBS_DIAGNOSTICS_ENABLED: 'true', DEVOBS_API_BASE_URL: 'https://api.devobs.org',
  DEVOBS_SERVICE_BINDINGS_JSON: JSON.stringify({ 'srv-01': { tenantId: 'alpha', projectId: 'mobile', serviceId: 'api' } }),
};
const result = { diagnosis: 'Pool saturated.', recommendation: 'Inspect connection leaks.', severity: 'medium', confidence: 'low', model: 'reviewed-model', latency_ms: 10 };
const request = { serverId: 'srv-01', errorLog: 'HTTP 503 database pool exhausted', dataRedacted: true };
async function fixture(t, env = settings, upstream = async () => Response.json(result)) {
  const app = express();
  app.post('/api/ai/analyze-incident', express.json({ limit: '32kb' }), createDiagnosticsHandler(env, upstream));
  const server = app.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  return (body = request, token = 'synthetic-access') => fetch(`http://127.0.0.1:${server.address().port}/api/ai/analyze-incident`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: token ? `Bearer ${token}` : '' }, body: JSON.stringify(body),
  });
}

test('disabled and invalid configuration reject without any provider call', async t => {
  for (const env of [{}, { ...settings, DEVOBS_API_BASE_URL: 'http://api.devobs.org' }, { ...settings, DEVOBS_API_BASE_URL: 'https://user:secret@api.devobs.org' }, { ...settings, DEVOBS_API_BASE_URL: 'https://api.devobs.org/path' }, { ...settings, DEVOBS_SERVICE_BINDINGS_JSON: '{' }]) {
    const send = await fixture(t, env, () => { assert.fail('must not call provider'); });
    const response = await send();
    assert.equal(response.status, 503);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await response.json(), { error: 'diagnostics_not_configured' });
  }
});

test('requires explicit redaction, bounded input, bearer and registered server', async t => {
  const send = await fixture(t, settings, () => { assert.fail('must not call provider'); });
  for (const [body, token, status] of [[request, '', 401], [{ ...request, dataRedacted: false }, 'synthetic-access', 400], [{ ...request, serverId: 'unknown' }, 'synthetic-access', 403], [{ ...request, errorLog: 'x'.repeat(8193) }, 'synthetic-access', 400], [{ ...request, errorLog: 'Authorization: Bearer do-not-send' }, 'synthetic-access', 400], [{ ...request, extra: 'private' }, 'synthetic-access', 400]]) {
    assert.equal((await send(body, token)).status, status);
  }
});

test('forwards only reviewed log to mapped protected API with redirects disabled', async t => {
  const calls = [];
  const send = await fixture(t, settings, async (url, init) => { calls.push({ url, init }); return Response.json(result); });
  const response = await send();
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.match(body.analysis, /Pool saturated/);
  assert.doesNotMatch(JSON.stringify(body), /synthetic-access|HTTP 503/);
  assert.equal(calls[0].url, 'https://api.devobs.org/v1/tenants/alpha/projects/mobile/services/api/diagnostics');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer synthetic-access');
  assert.equal(calls[0].init.redirect, 'error');
  assert.ok(calls[0].init.signal instanceof AbortSignal);
  assert.deepEqual(JSON.parse(calls[0].init.body), { error_log: request.errorLog, data_redacted: true });
});

test('provider failures, redirects, invalid and oversized output fail without leaking content', async t => {
  for (const upstream of [async () => { throw new Error('synthetic-access private'); }, async () => new Response('private', { status: 302 }), async () => Response.json({ ...result, secret: 'private' }), async () => new Response('x'.repeat(32769))]) {
    const send = await fixture(t, settings, upstream);
    const response = await send();
    assert.equal(response.status, 502);
    assert.deepEqual(await response.json(), { error: 'diagnostics_unavailable' });
  }
});

test('bounded process request budget rejects a sixth call', async t => {
  let calls = 0;
  const send = await fixture(t, settings, async () => { calls++; return Response.json(result); });
  for (let i = 0; i < 5; i++) assert.equal((await send()).status, 200);
  assert.equal((await send()).status, 429);
  assert.equal(calls, 5);
});


test('properly redacted bearer markers may be reviewed and forwarded', async t => {
  const send = await fixture(t);
  for (const marker of ['<redacted>', 'redacted']) {
    assert.equal((await send({ ...request, errorLog: `HTTP 503\nAuthorization: Bearer ${marker}` })).status, 200);
  }
});

test('two active calls block a third and release slots after completion', async t => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  let calls = 0;
  let twoStarted;
  const started = new Promise(resolve => { twoStarted = resolve; });
  const send = await fixture(t, settings, async () => {
    if (++calls === 2) twoStarted();
    await pending;
    return Response.json(result);
  });
  const first = send(), second = send();
  await started;
  try { assert.equal((await send()).status, 429); }
  finally { release(); }
  assert.equal((await first).status, 200);
  assert.equal((await second).status, 200);
  assert.equal((await send()).status, 200);
});

test('oversized streamed reply is cancelled at the byte boundary', async t => {
  let cancelled = false;
  const send = await fixture(t, settings, async () => new Response(new ReadableStream({
    pull(controller) { controller.enqueue(new Uint8Array(16385)); },
    cancel() { cancelled = true; },
  })));
  assert.equal((await send()).status, 502);
  assert.equal(cancelled, true);
});

test('upstream access denials and unavailable state retain status without body leakage', async t => {
  for (const status of [401, 403, 429, 503]) {
    const send = await fixture(t, settings, async () => new Response('private provider details', { status }));
    const response = await send();
    assert.equal(response.status, status);
    assert.deepEqual(await response.json(), { error: 'diagnostics_unavailable' });
  }
});
