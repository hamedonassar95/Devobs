/** Offline handoff from verified public portfolio CI to existing AI-1 CloudEvents adapter.
 * https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md
 */
import { PUBLIC_TARGETS, PublicPortfolioError } from './portfolio-api.mjs';
const SHA = /^[0-9a-f]{40}$/;
const OUTCOMES = new Set(['success', 'failure', 'cancelled', 'timed_out',
  'neutral', 'skipped', 'action_required']);
const NONTERMINAL = new Set(['running', 'pending', 'stale', 'missing', 'unverified', 'startup_failure']);
const validId = value => Number.isSafeInteger(value) && value > 0;
function reject() { throw new PublicPortfolioError('invalid_portfolio_handoff'); }

/** Never export an unverified/stale/nonterminal run or invent run_attempt/time. */
export function buildPortfolioCloudEvents(report) {
  if (!report || report.schema_version !== 1 || report.scope !== 'public_ci_only'
      || report.read_only !== true || report.production_ready !== false
      || report.private_repositories_queried !== false
      || report.checked_count !== PUBLIC_TARGETS.length
      || !Array.isArray(report.results) || report.results.length !== PUBLIC_TARGETS.length) reject();
  const lines = [];
  let ineligible = 0;
  for (let i = 0; i < PUBLIC_TARGETS.length; i++) {
    const target = PUBLIC_TARGETS[i];
    const row = report.results[i];
    if (!row || row.repository !== target.repo || row.branch !== target.branch) reject();
    if (NONTERMINAL.has(row.status)) { ineligible++; continue; }
    if (!OUTCOMES.has(row.status) || row.source !== 'public_github_read_only'
        || !SHA.test(row.main_sha) || row.main_sha !== row.run_sha
        || !validId(row.run_id)) reject();
    // Missing optional GitHub fields may still be displayed but never exported.
    if (row.run_attempt === null || row.created_at === null) { ineligible++; continue; }
    if (!validId(row.run_attempt) || typeof row.created_at !== 'string'
        || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(row.created_at)
        || !Number.isFinite(Date.parse(row.created_at))
        || new Date(row.created_at).toISOString() !== row.created_at) reject();
    const slug = target.repo.slice('hamedonassar95/'.length);
    const attempt = `run-${row.run_id}-attempt-${row.run_attempt}`;
    const event = {
      specversion: '1.0',
      id: `github-ci-${slug}-${attempt}`,
      source: `https://github.com/${target.repo}`,
      type: 'devobs.ci.result.v1',
      time: row.created_at,
      datacontenttype: 'application/json',
      data: {
        workflow: 'CI',
        job: `workflow-summary-${attempt}`,
        conclusion: row.status,
        commit_sha: row.run_sha,
      },
    };
    lines.push(JSON.stringify(event));
  }
  return { jsonl: lines.length ? lines.join('\n') + '\n' : null,
    included: lines.length, excluded: ineligible, total: PUBLIC_TARGETS.length };
}
