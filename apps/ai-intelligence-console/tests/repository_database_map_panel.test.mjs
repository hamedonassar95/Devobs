import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const APP_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = resolve(APP_ROOT, '../..');
const map = JSON.parse(await readFile(resolve(ROOT, 'docs/architecture/repository_database_map.json'), 'utf8'));
let vite;
let Panel;
let GitHubTab;
let validate;

before(async () => {
  vite = await createServer({ configFile: false, root: APP_ROOT, envDir: false, server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });
  ({ RepositoryDatabaseMapPanel: Panel, validateRepositoryDatabaseInventory: validate } = await vite.ssrLoadModule('/src/components/github/RepositoryDatabaseMapPanel.tsx'));
  ({ GitHubTab } = await vite.ssrLoadModule('/src/components/github/GitHubTab.tsx'));
});
after(async () => vite?.close());

function renderPanel(inventory) {
  return renderToStaticMarkup(React.createElement(Panel, arguments.length ? { inventory } : {}));
}

test('four repositories render with validated direct links', () => {
  const html = renderPanel();
  for (const repo of map.repositories) {
    assert.ok(html.includes(repo.name));
    assert.ok(html.includes(`href="${repo.url}"`));
  }
  assert.equal((html.match(/rel="noopener noreferrer"/g) ?? []).length, 4);
  assert.ok(html.includes('aria-label="Inventory status: VERIFIED"'));
});

test('GitHub Hub exposes the map as an accessible subtab button', () => {
  const html = renderToStaticMarkup(React.createElement(GitHubTab, { servers: [], incidents: [], deployments: [] }));
  assert.match(html, /Repository &amp; Database Map/);
  assert.match(html, /aria-pressed="false"/);
  assert.match(html, /type="button"/);
});

test('source status values, relationships, and verification boundaries render verbatim', () => {
  const html = renderPanel();
  for (const status of map.status_values) assert.ok(html.includes(`Inventory status: ${status}`));
  for (const text of [
    'Verified source evidence', 'Verified live connectivity', 'VERIFIED SOURCE LINK',
    'Service-to-database attachment', 'Physical provider / live target', 'my-apps-hamedo',
    'ai-studio-promptpal-f1b3ebe9-9826-4fca-9a67-b5376e8669b3', 'devobs_ai_staging',
    'PostgreSQL 17', '2026-12-05',
  ]) assert.ok(html.includes(text), `missing ${text}`);
});

test('dated mobile-first rendering keeps narrow cards stacked and long IDs wrapped', () => {
  const html = renderPanel();
  assert.ok(html.includes(`Not real-time · ${map.generated_at}`));
  assert.match(html, /makes no database or provider requests/);
  assert.match(html, /grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4/);
  assert.match(html, /break-all/);
  assert.doesNotMatch(html, /<table\b/);
});

test('missing map fails closed without showing topology', () => {
  const html = renderPanel(null);
  assert.match(html, /role="alert"/);
  assert.match(html, /map is missing or invalid/);
  assert.doesNotMatch(html, /hamedonassar95\/Devobs|my-apps-hamedo/);
});

test('invalid schema, status, URL, or live-access claim fails closed', () => {
  const cases = [structuredClone(map), structuredClone(map), structuredClone(map), structuredClone(map)];
  delete cases[0].map_format;
  cases[1].repositories[0].identity_status = 'LIVE';
  cases[2].repositories[0].url = 'javascript:alert(1)';
  cases[3].baseline.live_database_access_performed = true;
  for (const input of cases) {
    assert.equal(validate(input), null);
    const html = renderPanel(input);
    assert.match(html, /role="alert"/);
    assert.doesNotMatch(html, /Open repository/);
  }
});

test('unlisted secrets stay hidden and unsafe display values fail closed', () => {
  const input = structuredClone(map);
  input.database_resources[0].notes = 'SYNTHETIC_SECRET_SENTINEL';
  assert.doesNotMatch(renderPanel(input), /SYNTHETIC_SECRET_SENTINEL/);
  const unsafe = structuredClone(map);
  unsafe.database_resources.find(({ id }) => id === 'render_ai_staging_service').resource_name = 'postgresql://demo:password@db.example/database';
  assert.equal(validate(unsafe), null);
  assert.match(renderPanel(unsafe), /role="alert"/);
});
