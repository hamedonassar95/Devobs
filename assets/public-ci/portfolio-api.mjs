/** Browser-compatible, explicit opt-in GitHub public CI portfolio client.
 * Never reads private repositories, credentials, or arbitrary origins.
 * https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow
 * https://docs.github.com/en/rest/branches/branches#get-a-branch
 */
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
// GitHub run creation time is a stable event-time proxy, never an observation timestamp.
function safeRunTime(value) {
  if (value === undefined) return null;
  ensure(typeof value === 'string'
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(value));
  const date = new Date(value);
  ensure(Number.isFinite(date.getTime()));
  const canonical = date.toISOString();
  const [second, fraction] = value.slice(0, -1).split('.');
  ensure(canonical === second + '.' + (fraction ?? '').padEnd(3, '0') + 'Z');
  return canonical;
}

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
  const run_attempt = Object.hasOwn(run, 'run_attempt') ? run.run_attempt : null;
  ensure(run_attempt === null && !Object.hasOwn(run, 'run_attempt') || safeInt(run_attempt));
  const created_at = safeRunTime(run.created_at);
  const status = run.head_sha !== main_sha ? 'stale'
    : run.status === 'completed' ? run.conclusion
      : run.status === 'in_progress' ? 'running' : 'pending';
  return { ...base, status, run_sha: run.head_sha, run_id: run.id,
    run_attempt, created_at };
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

export async function inspectPublicTarget(target, fetcher = globalThis.fetch) {
  ensure(record(target) && PUBLIC_TARGETS.some(x => x.repo === target.repo && x.branch === target.branch));
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
    return normalizePublicRun(target, ...payloads);
  } catch (error) {
    if (error instanceof PublicPortfolioError) throw error;
    throw new PublicPortfolioError(controller.signal.aborted ? 'timeout' : 'unavailable');
  } finally {
    clearTimeout(timer);
  }
}

export async function inspectPublicPortfolio(fetcher = globalThis.fetch) {
  const results = [];
  for (const target of PUBLIC_TARGETS) {
    try {
      results.push(await inspectPublicTarget(target, fetcher));
    } catch (error) {
      // Do not echo input, provider error bodies, URLs, tokens or response text.
      const code = error instanceof PublicPortfolioError ? error.code : 'unavailable';
      results.push({ repository: target.repo, branch: target.branch, status: 'unverified', error: code });
    }
  }
  return {
    schema_version: 1, scope: 'public_ci_only', read_only: true,
    private_repositories_queried: false, production_ready: false,
    checked_count: results.length, results,
  };
}

