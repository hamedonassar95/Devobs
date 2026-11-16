import test from 'node:test';
import assert from 'node:assert/strict';
import { PUBLIC_TARGETS, inspectPublicPortfolio } from '../assets/public-ci/portfolio-api.mjs';
import * as nodeModule from '../scripts/portfolio_public_ci.mjs';

const SHA = 'a'.repeat(40);
function element() {
  return {
    textContent: '', hidden: false, disabled: false, children: [], handlers: {},
    addEventListener(type, handler) { this.handlers[type] = handler; },
    append(...nodes) { this.children.push(...nodes); },
    replaceChildren() { this.children = []; },
  };
}
function fakeResponse(url, data, status = 200) {
  const r = Response.json(data, { status });
  Object.defineProperty(r, 'url', { value: url });
  return r;
}
function publicFixture(callLog, rejectOne = false, includeMetadata = false) {
  return async (url, options) => {
    callLog.push(url);
    assert.equal(options.method, 'GET');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    const target = PUBLIC_TARGETS.find(p => url.startsWith('https://api.github.com/repos/' + p.repo + '/'));
    assert.ok(target, 'must never request unknown or private repositories');
    if (rejectOne && target.repo.endsWith('/ops')) {
      return fakeResponse(url, { privatePayload: 'do-not-display' }, 500);
    }
    if (url.includes('/branches/')) return fakeResponse(url, { name: target.branch, commit: { sha: SHA } });
    return fakeResponse(url, { total_count: 1, workflow_runs: [{
      id: 55, path: '.github/workflows/ci.yml', head_branch: 'main',
      event: 'push', head_sha: SHA, status: 'completed', conclusion: 'success',
      repository: { full_name: target.repo, private: false },
      head_repository: { full_name: target.repo, private: false },
      privatePayload: 'do-not-display',
      ...(includeMetadata ? { run_attempt: 1, created_at: '2026-11-16T17:00:00Z' } : {}),
    }] });
  };
}

test('browser and manual CLI refer to the same source allowlist and normalizer', () => {
  assert.strictEqual(nodeModule.PUBLIC_TARGETS, PUBLIC_TARGETS);
  assert.strictEqual(nodeModule.inspectPublicPortfolio, inspectPublicPortfolio);
  assert.equal(PUBLIC_TARGETS.length, 4);
});

test('public browser view makes no network requests on import, only on click', async t => {
  const oldDocument = globalThis.document;
  const oldFetch = globalThis.fetch;
  const ui = Object.fromEntries(['check-portfolio-ci', 'download-portfolio-ci', 'portfolio-status', 'portfolio-results'].map(id => [id, element()]));
  // The real HTML includes the hidden attribute on the result container.
  ui['portfolio-results'].hidden = true;
  const clicks = [];
  globalThis.document = {
    getElementById: id => ui[id] ?? null,
    createElement: () => element(),
  };
  globalThis.fetch = publicFixture(clicks);
  t.after(() => {
    globalThis.document = oldDocument;
    globalThis.fetch = oldFetch;
  });
  await import('../assets/public-ci/portfolio-view.mjs');
  assert.equal(clicks.length, 0, 'no implicit calls before user interaction');
  assert.equal(ui['check-portfolio-ci'].disabled, false);
  assert.equal(ui['portfolio-results'].hidden, true);
  assert.equal(ui['download-portfolio-ci'].disabled, true);
  await ui['check-portfolio-ci'].handlers.click();
  assert.equal(clicks.length, 8);
  assert.equal(ui['portfolio-results'].hidden, false);
  assert.equal(ui['portfolio-results'].children.length, 4);
  assert.deepEqual(ui['portfolio-results'].children.map(node => node.children[0].textContent), PUBLIC_TARGETS.map(t => t.repo));
  assert.ok(ui['portfolio-results'].children.every(node => node.children[1].textContent.includes('ناجح')));
  assert.equal(ui['check-portfolio-ci'].disabled, false);
  assert.equal(ui['download-portfolio-ci'].disabled, true, 'missing attempt/time must block export');
  assert.doesNotMatch(JSON.stringify(ui), /do-not-display/);
  // A second explicit click can fail for one repository without inventing all-success.
  globalThis.fetch = publicFixture(clicks, true, true);
  await ui['check-portfolio-ci'].handlers.click();
  // An early error on the final repository short-circuits its second GET.
  assert.equal(clicks.length, 15);
  const rows = ui['portfolio-results'].children;
  assert.equal(rows.length, 4);
  assert.equal(ui['download-portfolio-ci'].disabled, false, 'three verified source runs allow partial export');
  assert.match(rows[3].children[1].textContent, /تعذر التحقق/);
  assert.doesNotMatch(JSON.stringify(ui), /do-not-display/);
});
