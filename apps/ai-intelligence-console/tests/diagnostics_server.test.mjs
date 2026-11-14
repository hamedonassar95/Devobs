import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

test('real server mounts disabled diagnostics before large JSON parser and suppresses parse errors', { timeout: 20000 }, async t => {
  const reserve = createServer().listen(0, '127.0.0.1');
  await once(reserve, 'listening');
  const port = reserve.address().port;
  await new Promise(resolve => reserve.close(resolve));
  const child = spawn(process.execPath, ['--import', 'tsx', 'server.ts'], {
    cwd: fileURLToPath(new URL('..', import.meta.url)),
    env: { PATH: process.env.PATH, NODE_ENV: 'production', HOST: '127.0.0.1', PORT: String(port),
      GEMINI_API_KEY: '', DEVOBS_DIAGNOSTICS_ENABLED: 'false' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
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
  const send = body => fetch(`http://127.0.0.1:${port}/api/ai/analyze-incident`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body,
  });
  let response = await send('{}');
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.deepEqual(await response.json(), { error: 'diagnostics_not_configured' });
  response = await send('{"access_token":"synthetic-private-marker"');
  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: 'invalid_diagnostics_request' });
  response = await send(JSON.stringify({ errorLog: 'x'.repeat(32769) }));
  assert.equal(response.status, 413);
  assert.deepEqual(await response.json(), { error: 'invalid_diagnostics_request' });
});
