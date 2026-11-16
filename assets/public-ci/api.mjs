// Public, read-only scope. No account, token, arbitrary URL or project input.
// https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow
// https://docs.github.com/en/rest/branches/branches#get-a-branch
const REPO = 'hamedonassar95/Devobs';
const ORIGIN = 'https://api.github.com/repos/' + REPO;
const URLS = [ORIGIN + '/branches/main', ORIGIN + '/actions/workflows/ci.yml/runs?branch=main&event=push&per_page=1'];
const PENDING = new Set(['queued', 'pending', 'waiting', 'requested']);
const CONCLUSIONS = new Set(['success', 'failure', 'cancelled', 'timed_out', 'neutral', 'skipped', 'action_required', 'stale', 'startup_failure']);
const EXPORT_CONCLUSIONS = new Set(['success', 'failure', 'cancelled', 'timed_out', 'neutral', 'skipped', 'action_required']);
const SHA = /^[a-f0-9]{40}$/;
const LIMIT = 65_536;
const DEADLINE_MS = 5_000;

export class PublicCiError extends Error {
  constructor(code) { super(code); this.name = 'PublicCiError'; this.code = code; }
}
function requireValue(condition) { if (!condition) throw new PublicCiError('invalid_response'); }
function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
const positiveInteger = value => Number.isSafeInteger(value) && value > 0;
function timestamp(value) {
  requireValue(typeof value === 'string');
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,3}))?Z$/.exec(value);
  requireValue(match !== null);
  const time = new Date(value);
  requireValue(Number.isFinite(time.getTime()) && time.toISOString() === `${match[1]}.${(match[2] ?? '').padEnd(3, '0')}Z`);
  return value;
}

export function normalizePublicCiEvidence(head, runs) {
  requireValue(object(head) && head.name === 'main' && object(head.commit)
    && typeof head.commit.sha === 'string' && SHA.test(head.commit.sha));
  requireValue(object(runs) && Number.isSafeInteger(runs.total_count) && runs.total_count >= 0
    && Array.isArray(runs.workflow_runs) && runs.workflow_runs.length <= 1);
  if (runs.total_count === 0) {
    requireValue(runs.workflow_runs.length === 0);
    return { state: 'missing', mainSha: head.commit.sha };
  }
  requireValue(runs.workflow_runs.length === 1);
  const run = runs.workflow_runs[0];
  requireValue(object(run) && positiveInteger(run.id) && positiveInteger(run.run_number)
    && run.workflow_id === 374991651 && run.path === '.github/workflows/ci.yml'
    && run.head_branch === 'main' && run.event === 'push'
    && typeof run.head_sha === 'string' && SHA.test(run.head_sha));
  for (const repo of [run.repository, run.head_repository]) {
    requireValue(object(repo) && repo.full_name === REPO && repo.private === false);
  }
  requireValue(typeof run.status === 'string' && (run.status === 'completed' || run.status === 'in_progress' || PENDING.has(run.status)));
  requireValue(run.status === 'completed' ? CONCLUSIONS.has(run.conclusion) : run.conclusion === null);
  const createdAt = timestamp(run.created_at);
  const updatedAt = timestamp(run.updated_at);
  requireValue(Date.parse(createdAt) <= Date.parse(updatedAt));
  // Optional in GitHub's schema: absence disables export, never implies attempt 1.
  const runAttempt = Object.hasOwn(run, 'run_attempt') ? run.run_attempt : null;
  requireValue((runAttempt === null && !Object.hasOwn(run, 'run_attempt')) || positiveInteger(runAttempt));
  const matchesHead = run.head_sha === head.commit.sha;
  const state = !matchesHead ? 'stale' : run.status === 'completed' ? run.conclusion
    : run.status === 'in_progress' ? 'running' : 'pending';
  return { state, mainSha: head.commit.sha, runSha: run.head_sha, runId: run.id, runNumber: run.run_number,
    runAttempt, createdAt, updatedAt, runUrl: `https://github.com/${REPO}/actions/runs/${run.id}`,
    status: run.status, conclusion: run.conclusion, matchesHead };
}

// Local file only. Creation time is a stable occurrence-time proxy, not completion
// time. The existing AI-1 converter drops CE id, so job also carries attempt identity.
export function buildPublicCiCloudEvent(evidence) {
  if (!object(evidence) || evidence.status !== 'completed' || evidence.matchesHead !== true
    || !EXPORT_CONCLUSIONS.has(evidence.conclusion) || evidence.state !== evidence.conclusion
    || evidence.runAttempt === null) return null;
  requireValue(positiveInteger(evidence.runId) && positiveInteger(evidence.runAttempt)
    && typeof evidence.runSha === 'string' && SHA.test(evidence.runSha)
    && evidence.mainSha === evidence.runSha);
  const time = new Date(timestamp(evidence.createdAt)).toISOString();
  return JSON.stringify({ specversion: '1.0', id: `github-ci-${evidence.runId}-attempt-${evidence.runAttempt}`,
    source: `https://github.com/${REPO}`, type: 'devobs.ci.result.v1', time,
    datacontenttype: 'application/json', data: { workflow: 'CI',
      job: `workflow-summary-run-${evidence.runId}-attempt-${evidence.runAttempt}`,
      conclusion: evidence.conclusion, commit_sha: evidence.runSha } }) + '\n';
}

async function boundedJson(response, signal) {
  requireValue(response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase() === 'application/json');
  const length = response.headers.get('Content-Length');
  requireValue(length === null || !/^\d+$/.test(length) || Number(length) <= LIMIT);
  requireValue(response.body && typeof response.body.getReader === 'function');
  const reader = response.body.getReader();
  let rejectAbort;
  const aborted = new Promise((_resolve, reject) => { rejectAbort = reject; });
  const onAbort = () => { void reader.cancel().catch(() => {}); rejectAbort(new PublicCiError('timeout')); };
  signal.addEventListener('abort', onAbort, { once: true });
  if (signal.aborted) onAbort();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await Promise.race([reader.read(), aborted]);
      if (done) break;
      requireValue(value instanceof Uint8Array); size += value.byteLength;
      if (size > LIMIT) { void reader.cancel().catch(() => {}); throw new PublicCiError('invalid_response'); }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
    catch { throw new PublicCiError('invalid_response'); }
  } finally {
    signal.removeEventListener('abort', onAbort);
    reader.releaseLock();
  }
}

export async function fetchPublicCi(fetcher = globalThis.fetch) {
  const controller = new AbortController();
  let deadlineExpired = false;
  const timer = setTimeout(() => { deadlineExpired = true; controller.abort(); }, DEADLINE_MS);
  try {
    const payloads = await Promise.all(URLS.map(async url => {
      const response = await fetcher(url, { method: 'GET', credentials: 'omit', redirect: 'error',
        referrerPolicy: 'no-referrer', cache: 'no-store', signal: controller.signal,
        headers: { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' } });
      requireValue(response && !response.redirected && response.url === url);
      if (response.status === 429 || (response.status === 403 && response.headers.get('X-RateLimit-Remaining') === '0')) throw new PublicCiError('rate_limited');
      if (response.status === 404) throw new PublicCiError('not_available');
      if (response.status !== 200) throw new PublicCiError('unavailable');
      return boundedJson(response, controller.signal);
    }));
    return normalizePublicCiEvidence(...payloads);
  } catch (error) {
    if (deadlineExpired) throw new PublicCiError('timeout');
    if (error instanceof PublicCiError) throw error;
    throw new PublicCiError('unavailable');
  } finally { clearTimeout(timer); controller.abort(); }
}
