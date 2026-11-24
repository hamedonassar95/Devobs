import type { RequestHandler } from 'express';
import { inspectPublicTarget, PublicPortfolioError } from '../../assets/public-ci/portfolio-api.mjs';

/** Reuses the public CI reader's fixed URLs, anonymous fetch policy, timeout and schema checks. */
export const ALLOWED_GITHUB_REPOSITORIES = Object.freeze([
  'hamedonassar95/Devobs',
  'hamedonassar95/ops',
  'hamedonassar95/DevObs-ai-Intelligence-',
  'hamedonassar95/devobs-saas',
] as const);

const ALLOWED = new Set<string>(ALLOWED_GITHUB_REPOSITORIES);
// Visibility was verified on 2026-11-24. The other requested entry is never queried.
const VERIFIED_PUBLIC = new Set([
  'hamedonassar95/Devobs', 'hamedonassar95/ops', 'hamedonassar95/devobs-saas',
]);
const CONCLUSIONS = new Set(['success', 'failure', 'cancelled', 'timed_out', 'neutral',
  'skipped', 'action_required', 'stale', 'startup_failure']);
type StatusPayload = {
  repository: string | null; status: 'OBSERVED' | 'PENDING' | 'UNVERIFIED';
  branch: string | null; commitSha: string | null; ciConclusion: string | null;
  runStatus: string | null; observedAt: string | null; cached: boolean; reason: string | null;
};
const unverified = (repository: string | null, reason: string, branch: string | null = null,
  commitSha: string | null = null, observedAt: string | null = null): StatusPayload => ({
  repository, status: 'UNVERIFIED', branch, commitSha, ciConclusion: null,
  runStatus: null, observedAt, cached: false, reason,
});

export function createPublicGithubStatusHandler({
  enabled = false, bindHost = '127.0.0.1', consolePort = 3000,
  fetchImpl = fetch, clock = () => new Date(), cacheTtlMs = 30_000,
}: { enabled?: boolean; bindHost?: string; consolePort?: number;
  fetchImpl?: typeof fetch; clock?: () => Date; cacheTtlMs?: number; } = {}): RequestHandler {
  const cache = new Map<string, { expiresAt: number; value: StatusPayload }>();
  const observedAt = () => {
    const value = clock();
    return value instanceof Date && Number.isFinite(value.getTime()) ? value.toISOString() : null;
  };
  return async (req, res) => {
    res.set({ 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' });
    if (req.method !== 'GET') { res.set('Allow', 'GET').status(405).json(unverified(null, 'method_not_allowed')); return; }
    const query = req.query as Record<string, unknown>;
    const repository = query.repository;
    if (Object.keys(query).length !== 1 || typeof repository !== 'string' || !ALLOWED.has(repository)) {
      res.status(400).json(unverified(null, 'repository_not_allowed')); return;
    }
    if (!enabled || bindHost !== '127.0.0.1') {
      res.status(503).json(unverified(repository, enabled ? 'non_loopback_bind' : 'disabled')); return;
    }
    const hosts = [`127.0.0.1:${consolePort}`, `localhost:${consolePort}`];
    const host = req.get('host') ?? '';
    const origin = req.get('origin');
    const site = req.get('sec-fetch-site');
    if (!hosts.includes(host) || (origin && !hosts.some(value => origin === `http://${value}`))
        || (site && !['none', 'same-origin'].includes(site)) || req.socket.localAddress !== '127.0.0.1') {
      res.status(403).json(unverified(repository, 'request_denied')); return;
    }
    if (!VERIFIED_PUBLIC.has(repository)) {
      res.status(503).json(unverified(repository, 'public_visibility_unverified')); return;
    }
    const now = Date.now();
    const cached = cache.get(repository);
    if (cached && cached.expiresAt > now) { res.status(200).json({ ...cached.value, cached: true }); return; }
    if (cached) cache.delete(repository);
    let branch: string | null = null;
    let commitSha: string | null = null;
    try {
      const current = await inspectPublicTarget({ repo: repository, branch: 'main' }, fetchImpl);
      branch = current.branch;
      commitSha = current.main_sha;
      const timestamp = observedAt();
      if (!timestamp) throw new PublicPortfolioError('invalid_response');
      let value: StatusPayload;
      if (current.status === 'missing' || current.status === 'stale') {
        value = unverified(repository, current.status === 'missing' ? 'no_runs' : 'no_matching_ci_run', branch, commitSha, timestamp);
      } else if (current.status === 'running' || current.status === 'pending') {
        value = { repository, status: 'PENDING', branch, commitSha, ciConclusion: 'pending',
          runStatus: current.status === 'running' ? 'in_progress' : 'pending', observedAt: timestamp, cached: false, reason: null };
      } else if (CONCLUSIONS.has(current.status)) {
        value = { repository, status: 'OBSERVED', branch, commitSha, ciConclusion: current.status,
          runStatus: 'completed', observedAt: timestamp, cached: false, reason: null };
      } else throw new PublicPortfolioError('invalid_response');
      cache.set(repository, { expiresAt: now + cacheTtlMs, value });
      res.status(200).json(value);
    } catch (error) {
      const code = error instanceof PublicPortfolioError ? error.code : 'unavailable';
      const reason = code === 'rate_limited' ? 'rate_limited' : code === 'timeout' ? 'timeout'
        : code === 'invalid_response' ? 'invalid_response' : 'upstream_unavailable';
      const timestamp = branch ? observedAt() : null;
      const value = unverified(repository, reason, branch, commitSha, timestamp);
      const statusCode = reason === 'rate_limited' ? 429 : reason === 'timeout' ? 504
        : reason === 'invalid_response' ? 502 : 503;
      cache.set(repository, { expiresAt: now + Math.min(cacheTtlMs, 5_000), value });
      res.status(statusCode).json(value);
    }
  };
}
