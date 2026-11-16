#!/usr/bin/env node
/** Manual, anonymous, read-only CI visibility for four reviewed public repositories.
 * Docs: https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow
 *       https://docs.github.com/en/rest/branches/branches#get-a-branch
 */
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

export const PUBLIC_TARGETS = Object.freeze([
  Object.freeze({ repo: 'hamedonassar95/Devobs', branch: 'main' }),
  Object.freeze({ repo: 'hamedonassar95/devobs-saas', branch: 'main' }),
  Object.freeze({ repo: 'hamedonassar95/LiveOps-Integration', branch: 'main' }),
  Object.freeze({ repo: 'hamedonassar95/ops', branch: 'main' }),
]);
const SHA = /^[0-9a-f]{40}$/;
const CONCLUSIONS = new Set(['success', 'failure', 'cancelled', 'timed_out', 'neutral',
  'skipped', 'action_required', 'stale', 'startup_failure']);
const MAX_BYTES = 65_536;
const API = 'https://api.github.com/repos/';
export class PublicPortfolioError extends Error {
  constructor(code) { super(code); this.code = code; }
}
function ensure(condition) {
  if (!condition) throw new PublicPortfolioError('invalid_response');
}
function record(v) { return v !== null && typeof v === 'object' && !Array.isArray(v); }
function safeInt(v) { return Number.isSafeInteger(v) && v > 0; }

export function normalizePublicRun(target, branch, list) {
  ensure(record(target) && PUBLIC_TARGETS.some(x => x.repo === target.repo && x.branch === target.branch));
  ensure(record(branch) && branch.name === target.branch && record(branch.commit)
    && typeof branch.commit.sha === 'string' && SHA.test(branch.commit.sha));
  ensure(record(list) && Number.isSafeInteger(list.total_count) && list.total_count >= 0
    && Array.isArray(list.workflow_runs) && list.workflow_runs.length <= 1);
  const main_sha = branch.commit.sha;
  const base = { repository: target.repo, branch: target.branch, main_sha, source: 'public_github_read_only' };
  if (list.total_count === 0) {
    ensure(list.workflow_runs.length === 0);
    return { ...base, status: 'missing', run_sha: null, run_id: null };
  }
  ensure(list.workflow_runs.length === 1);
  const run = list.workflow_runs[0];
  ensure(record(run) && safeInt(run.id) && run.path === '.github/workflows/ci.yml'
    && run.head_branch === target.branch && run.event === 'push'
    && typeof run.head_sha === 'string' && SHA.test(run.head_sha)
    && record(run.repository) && run.repository.full_name === target.repo
    && run.repository.private === false
    && record(run.head_repository) && run.head_repository.full_name === target.repo
    && run.head_repository.private === false);
  ensure(typeof run.status === 'string'
    && ['completed', 'in_progress', 'queued', 'waiting', 'pending', 'requested'].includes(run.status));
  if (run.status === 'completed') ensure(CONCLUSIONS.has(run.conclusion));
  else ensure(run.conclusion === null);
  const status = run.head_sha !== main_sha ? 'stale'
    : run.status === 'completed' ? run.conclusion
      : run.status === 'in_progress' ? 'running' : 'pending';
  return { ...base, status, run_sha: run.head_sha, run_id: run.id };
}

async function boundedJson(response) {
  ensure(response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() === 'application/json');
  const length = response.headers.get('content-length');
  ensure(length === null || (/^\d+$/.test(length) && Number(length) <= MAX_BYTES));
  ensure(response.body && typeof response.body.getReader === 'function');
  const reader = response.body.getReader();
  const chunks = [];
  let bytes = 0;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      ensure(value instanceof Uint8Array);
      bytes += value.byteLength;
      ensure(bytes <= MAX_BYTES);
      chunks.push(value);
    }
  } finally {
    if (bytes > MAX_BYTES) await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
  const combined = new Uint8Array(bytes);
  let offset = 0;
  for (const chunk of chunks) { combined.set(chunk, offset); offset += chunk.length; }
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(combined)); }
  catch { throw new PublicPortfolioError('invalid_response'); }
}

export async function inspectPublicPortfolio(fetcher = globalThis.fetch) {
  const results = [];
  for (const target of PUBLIC_TARGETS) {
    const base = API + target.repo + '/';
    const urls = [base + 'branches/' + target.branch,
      base + 'actions/workflows/ci.yml/runs?branch=' + target.branch + '&event=push&per_page=1'];
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5_000);
    try {
      const payloads = [];
      for (const url of urls) {
        const response = await fetcher(url, {
          method: 'GET', credentials: 'omit', redirect: 'error',
          referrerPolicy: 'no-referrer', cache: 'no-store',
          headers: { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
          signal: controller.signal,
        });
        if (response?.status === 403 && response.headers.get('x-ratelimit-remaining') === '0')
          throw new PublicPortfolioError('rate_limited');
        if (response?.status === 429) throw new PublicPortfolioError('rate_limited');
        if (response?.status === 404) throw new PublicPortfolioError('not_available');
        ensure(response?.status === 200 && response.redirected === false && response.url === url);
        payloads.push(await boundedJson(response));
      }
      results.push(normalizePublicRun(target, ...payloads));
    } catch (error) {
      // Do not echo input, provider error bodies, URLs, tokens or response text.
      const code = error instanceof PublicPortfolioError ? error.code : 'unavailable';
      results.push({ repository: target.repo, branch: target.branch, status: 'unverified', error: code });
    } finally {
      clearTimeout(timer);
    }
  }
  return {
    schema_version: 1, scope: 'public_ci_only', read_only: true,
    private_repositories_queried: false, production_ready: false,
    checked_count: results.length, results,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv.length !== 2) {
    process.stderr.write('usage: node scripts/portfolio_public_ci.mjs\n');
    process.exitCode = 2;
  } else {
    const report = await inspectPublicPortfolio();
    process.stdout.write(JSON.stringify(report, null, 2) + '\n');
    process.exitCode = report.results.some(x => x.status === 'unverified') ? 1 : 0;
  }
}
