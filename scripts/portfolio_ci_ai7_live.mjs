#!/usr/bin/env node
/** Manual, anonymous public GitHub CI → existing AI-1/AI-7 pipeline.
 * No token, private repository, storage, scheduler, deployment or automatic fix.
 */
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { PUBLIC_TARGETS, inspectPublicPortfolio } from '../assets/public-ci/portfolio-api.mjs';
import { buildPortfolioCloudEvents } from '../assets/public-ci/portfolio-export.mjs';
import { analyzePortfolioCiJsonl } from './portfolio_ci_ai7.mjs';

const ALLOWED_STATUSES = new Set([
  'success', 'failure', 'cancelled', 'timed_out', 'neutral', 'skipped',
  'action_required', 'stale', 'running', 'pending', 'missing', 'unverified',
  'startup_failure',
]);

/**
 * Explicitly invokes at most eight fixed, anonymous GitHub REST GETs, then
 * analyzes *eligible* public CI events using the existing local AI-7 engine.
 * The injected fetcher is used by offline tests; no network calls on import.
 */
export async function inspectAndAnalyzePublicCi(fetcher = globalThis.fetch) {
  const observed = await inspectPublicPortfolio(fetcher);
  const converted = buildPortfolioCloudEvents(observed);
  const observations = observed.results.map((row, index) => {
    if (row.repository !== PUBLIC_TARGETS[index].repo
        || row.branch !== PUBLIC_TARGETS[index].branch
        || !ALLOWED_STATUSES.has(row.status)) {
      throw new Error('invalid_public_ci_observation');
    }
    return {
      repository: PUBLIC_TARGETS[index].repo,
      status: row.status,
      analysis_eligible: converted.jsonl !== null
        && row.source === 'public_github_read_only'
        && row.run_attempt !== null && row.created_at !== null
        && row.run_sha === row.main_sha
        && ['success', 'failure', 'cancelled', 'timed_out',
          'neutral', 'skipped', 'action_required'].includes(row.status),
    };
  });
  const verified = observations.filter(entry => entry.analysis_eligible).length;
  if (verified !== converted.included || converted.total !== PUBLIC_TARGETS.length
      || converted.excluded !== PUBLIC_TARGETS.length - verified) {
    throw new Error('inconsistent_portfolio_evidence');
  }
  const analysis = converted.jsonl === null ? null : analyzePortfolioCiJsonl(converted.jsonl);
  if (analysis !== null
      && (analysis.summary.ci_event_count !== verified
        || analysis.summary.missing_project_count !== PUBLIC_TARGETS.length - verified
        || analysis.read_only !== true || analysis.production_ready !== false)) {
    throw new Error('inconsistent_ai7_analysis');
  }
  return {
    schema_version: 1,
    status: verified === 0 ? 'no_eligible_evidence'
      : verified === PUBLIC_TARGETS.length ? 'complete_observation'
        : 'partial_observation',
    source: 'manual_anonymous_github_public_ci',
    read_only: true,
    production_ready: false,
    external_provenance_verified: false,
    checked_count: PUBLIC_TARGETS.length,
    eligible_count: verified,
    excluded_count: converted.excluded,
    observations,
    analysis: analysis === null ? null : {
      summary: analysis.summary,
      projects: analysis.projects,
      pipeline: analysis.pipeline,
      advisory: analysis.advisory,
    },
    limitations: 'A public GitHub CI conclusion is not a root cause, authenticated provenance, runtime health or permission to deploy. No logs, private repos or automation are accessed.',
  };
}

/** 0: all four reports analyzable (even if a CI run failed); 1: partial/none; 2: invalid invocation/error. */
export async function main(args = process.argv.slice(2), fetcher = globalThis.fetch) {
  if (args.length === 1 && args[0] === '--help') {
    process.stdout.write('usage: node scripts/portfolio_ci_ai7_live.mjs\n');
    return 0;
  }
  if (args.length !== 0) {
    process.stderr.write('portfolio-ci-ai7-live: invalid_arguments\n');
    return 2;
  }
  try {
    const result = await inspectAndAnalyzePublicCi(fetcher);
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
    return result.status === 'complete_observation' ? 0 : 1;
  } catch {
    // Fail closed and never print raw GitHub payloads, response errors or secrets.
    process.stderr.write('portfolio-ci-ai7-live: unverified_or_invalid_response\n');
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
