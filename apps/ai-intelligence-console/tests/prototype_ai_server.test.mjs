import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const routes = [
  '/api/ai/generate-audit-report', '/api/ai/chat', '/api/ai/autonomous-heal',
  '/api/ai/predictive-forecast', '/api/ai/generate-sre-briefing',
  '/api/ai/transcribe-audio', '/api/ai/generate-video', '/api/ai/generate-image',
  '/api/ai/generate-music', '/api/ai/voice-speak', '/api/ai/live-conversation',
  '/api/github/generate-release-notes', '/api/github/generate-pr-summary',
];
const denial = { code: 'prototype_ai_disabled', error: 'ميزات الذكاء الاصطناعي التجريبية غير مفعّلة.' };

async function fixture(t, key) {
  const reserve = createServer().listen(0, '127.0.0.1');
  await once(reserve, 'listening');
  const port = reserve.address().port;
  await new Promise(resolve => reserve.close(resolve));
  const child = spawn(process.execPath,
    ['--import', './tests/fixtures/no-provider-network.mjs', '--import', 'tsx', 'server.ts'], {
      cwd: fileURLToPath(new URL('..', import.meta.url)),
      env: { PATH: process.env.PATH, NODE_ENV: 'production', HOST: '127.0.0.1', PORT: String(port),
        GEMINI_API_KEY: key, DEVOBS_DIAGNOSTICS_ENABLED: 'false' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  let logs = '';
  child.stdout.on('data', data => { logs += data; });
  child.stderr.on('data', data => { logs += data; });
  t.after(async () => {
    if (child.exitCode === null) { child.kill('SIGTERM'); await once(child, 'exit'); }
  });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('server_start_timeout')), 10000);
    child.stdout.on('data', data => {
      if (data.toString().includes('Server listening')) { clearTimeout(timer); resolve(); }
    });
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('exit', () => { clearTimeout(timer); reject(new Error('server_exited')); });
  });
  return {
    send: (path, options = {}) => fetch(`http://127.0.0.1:${port}${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer synthetic-private-marker' },
      body: '{}', ...options,
    }),
    logs: () => logs,
  };
}

for (const key of ['', 'synthetic-no-live-key']) {
  test(`real server keeps all prototype AI closed ${key ? 'with a synthetic key' : 'without a key'}`, { timeout: 20000 }, async t => {
    const { send, logs } = await fixture(t, key);
    for (const path of [...routes, '/API/AI/Chat/', '/api/github/generate-pr-summary/', '/api/ai/unknown']) {
      const response = await send(path);
      assert.equal(response.status, 503, path);
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.deepEqual(await response.json(), denial);
    }
    for (const body of ['{"access_token":"synthetic-private-marker"', 'x'.repeat(65536)]) {
      const response = await send('/api/ai/chat', { body });
      assert.equal(response.status, 503);
      assert.deepEqual(await response.json(), denial);
    }
    const diagnostics = await send('/api/ai/analyze-incident');
    assert.equal(diagnostics.status, 503);
    assert.deepEqual(await diagnostics.json(), { error: 'diagnostics_not_configured' });
    const metadata = await send('/api/github/git-info', { method: 'GET', body: undefined });
    assert.equal(metadata.status, 200);
    assert.equal((await metadata.json()).status, 'demo');
    assert.equal(logs().includes('unexpected_provider_network'), false);
    assert.equal(logs().includes('synthetic-private-marker'), false);
    assert.equal(logs().includes('synthetic-no-live-key'), false);
  });
}
