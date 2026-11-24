import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const APP_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
let vite;
let LocalAi7Panel;

before(async () => {
  vite = await createServer({
    configFile: false,
    root: APP_ROOT,
    envDir: false,
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });
  ({ LocalAi7Panel } = await vite.ssrLoadModule('/src/components/dashboard/LocalAi7Panel.tsx'));
});

after(async () => vite?.close());

test('initial panel render makes no request and offers no report before a valid snapshot', async () => {
  const originalFetch = globalThis.fetch;
  let requests = 0;
  globalThis.fetch = async () => {
    requests++;
    throw new Error('unexpected_initial_local_ai7_request');
  };

  try {
    const html = renderToStaticMarkup(React.createElement(LocalAi7Panel));

    assert.equal(requests, 0, 'loading the panel must not contact the local AI-7 endpoint');
    assert.match(html, /لم يُطلب اتصال بالمحرك المحلي بعد/);
    assert.match(html, /قراءة المحرك المحلي/);
    assert.doesNotMatch(html, /تنزيل تقرير المراجعة/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
