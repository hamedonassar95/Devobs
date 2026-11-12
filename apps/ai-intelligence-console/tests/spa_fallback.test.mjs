import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { once } from 'node:events';
import express from 'express';
import rateLimit from 'express-rate-limit';
import { test } from 'node:test';
import { createSpaFallbackHandler } from '../spaFallback.ts';

test('production SPA fallback serves the root and nested routes through the rate limit middleware', async (t) => {
  const distDirectory = await mkdtemp(path.join(os.tmpdir(), 'devobs-spa-'));
  await writeFile(path.join(distDirectory, 'index.html'), '<main>Devobs app</main>');
  const app = express();
  const routeRateLimit = rateLimit({
    windowMs: 60_000,
    limit: 2,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
  });
  // Express 5 requires named wildcards. The braces also include the root URL.
  app.get('/{*splat}', routeRateLimit, createSpaFallbackHandler(distDirectory));

  const server = app.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(async () => {
    server.closeAllConnections();
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    await rm(distDirectory, { recursive: true, force: true });
  });

  const address = server.address();
  assert.ok(address && typeof address === 'object');
  for (const route of ['/', '/dashboard/servers']) {
    const response = await fetch(`http://127.0.0.1:${address.port}${route}`);
    assert.equal(response.status, 200, `${route} should resolve to the SPA`);
    assert.equal(await response.text(), '<main>Devobs app</main>');
  }
  const limitedResponse = await fetch(`http://127.0.0.1:${address.port}/another-route`);
  assert.equal(limitedResponse.status, 429, 'the route limiter should block requests beyond its configured limit');
});
