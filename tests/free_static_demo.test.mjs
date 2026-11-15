import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { buildFreeDemoSnapshot } from '../scripts/free_demo_snapshot.mjs';
import { dashboardRequestUrl } from '../scripts/ai_intelligence/dashboard_assets/static_demo.mjs';

const ROOT = new URL('../', import.meta.url);
test('published synthetic snapshot equals current local engine output', async () => {
  const expected = await buildFreeDemoSnapshot();
  const raw = await readFile(new URL('assets/free-devobs/snapshot.json', ROOT), 'utf8');
  assert.deepEqual(JSON.parse(raw), expected);
  assert.equal(expected.pipeline.mode, 'local_advisory_only');
  assert.deepEqual(expected.pipeline.stages.map(item => item.id), ['AI-1','AI-2','AI-3','AI-4','AI-5','AI-6','AI-7']);
  assert.ok(expected.summary.event_count > 0);
  assert.ok(expected.summary.anomaly_candidate_count > 0);
  assert.doesNotMatch(raw, /LOCAL_ADVISORY_RAW_LOG_SENTINEL|Bearer |PRIVATE KEY/);
});

test('free profile resolves the one snapshot relative to its deployment path', () => {
  for (const base of ['https://example.org/Devobs/assets/free-devobs/', 'https://example.org/assets/free-devobs/']) {
    assert.equal(dashboardRequestUrl('/api/v1/intelligence', { staticDemo: true, moduleUrl: base + 'dashboard.js' }), base + 'snapshot.json');
    for (const denied of ['/api/v1/google-docs-config', '/api/v1/summary', 'https://other.example/api', '../secret']) {
      assert.throws(() => dashboardRequestUrl(denied, { staticDemo: true, moduleUrl: base }), /static_demo_api_disabled/);
    }
  }
  assert.equal(dashboardRequestUrl('/api/v1/intelligence'), '/api/v1/intelligence');
});

test('free HTML advertises synthetic data and has no credential or cloud controls', async () => {
  const html = await readFile(new URL('assets/free-devobs/index.html', ROOT), 'utf8');
  assert.match(html, /data-mode="free-demo"/);
  assert.match(html, /connect-src 'self'/);
  assert.match(html, /script-src 'self'/);
  assert.match(html, /بيانات اصطناعية/);
  assert.doesNotMatch(html, /https?:\/\/|type="password"|id="google-|src="\//);
  assert.match(html, /href="\.\/snapshot.json" download=/);
});
