#!/usr/bin/env node
/** Analyze a manually downloaded public CI CloudEvents JSONL using existing AI-1 and AI-7.
 * No network calls, filesystem writes, deployments, model inference or remediation.
 */
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { readInputFile } from './ai_intelligence/event_ingest.mjs';
import { parseEventLines } from './ai_intelligence/event_schema.mjs';
import { convertText, CI_ALLOWED_SOURCES } from './integrations/cloudevents_ci_adapter.mjs';
import { PUBLIC_TARGETS } from '../assets/public-ci/portfolio-api.mjs';
import { buildDashboardSnapshot } from './ai_intelligence/dashboard_server.mjs';

const allowed = new Set(PUBLIC_TARGETS.map(target => CI_ALLOWED_SOURCES['https://github.com/' + target.repo] + ' - CI'));
const outcomes = new Set(['success', 'failure', 'cancelled', 'timed_out', 'neutral',
  'skipped', 'action_required']);
const jobPattern = /^workflow-summary-run-[1-9]\d*-attempt-[1-9]\d*$/;

export function analyzePortfolioCiJsonl(text) {
  // Existing converter validates CloudEvents fields, provenance labels, sensitive content,
  // then AI-1 validates immutable, content-derived event IDs and input limits.
  const converted = convertText(text);
  const { events, duplicatesInBatch } = parseEventLines(converted);
  if (duplicatesInBatch !== 0 || events.length === 0 || events.length > PUBLIC_TARGETS.length
      || events.some(event => event.kind !== 'ci_result'
        || event.source !== 'github_actions'
        || !allowed.has(event.data.workflow)
        || !jobPattern.test(event.data.job)
        || !outcomes.has(event.data.conclusion)
        || !/^[0-9a-f]{40}$/.test(event.data.commit_sha ?? ''))) {
    throw new Error('invalid_portfolio_input');
  }
  const projects = events.map(event => ({
    project: event.data.workflow.slice(0, -' - CI'.length),
    conclusion: event.data.conclusion,
  }));
  if (new Set(projects.map(row => row.project)).size !== projects.length)
    throw new Error('duplicate_project_ci');
  const snapshot = buildDashboardSnapshot(events);
  if (snapshot.status !== 'local_snapshot'
      || snapshot.pipeline.id !== 'devobs-ai-local-1-7'
      || snapshot.pipeline.mode !== 'local_advisory_only'
      || snapshot.summary.kind_counts.ci_result !== events.length
      || snapshot.summary.recommendation_count !== 0) {
    throw new Error('invalid_ai7_snapshot');
  }
  return {
    schema_version: 1, source: 'operator_supplied_public_ci_file',
    status: 'local_advisory_only', external_provenance_verified: false,
    read_only: true, production_ready: false,
    summary: {
      ci_event_count: snapshot.summary.kind_counts.ci_result,
      failed_ci_count: projects.filter(p => p.conclusion === 'failure' || p.conclusion === 'timed_out').length,
      recommendation_count: snapshot.summary.recommendation_count,
      missing_project_count: PUBLIC_TARGETS.length - projects.length,
    },
    projects,
    pipeline: snapshot.pipeline.stages.map(stage => ({
      id: stage.id, status: stage.status, count: stage.count,
    })),
    advisory: 'CI conclusions alone do not reveal root cause; inspect authorized logs manually before proposing a fix.',
    limitations: 'Imported public CI events do not prove identity, current CI status, live health, tenant isolation, production readiness or human approval.',
  };
}

function usage() { return 'usage: node scripts/portfolio_ci_ai7.mjs --input <downloaded-jsonl-file>'; }

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const args = process.argv.slice(2);
  if (args.length !== 2 || args[0] !== '--input' || typeof args[1] !== 'string'
      || !args[1] || args[1].startsWith('--')) {
    process.stderr.write(usage() + '\n');
    process.exitCode = 2;
  } else {
    try {
      const text = await readInputFile(args[1]);
      process.stdout.write(JSON.stringify(analyzePortfolioCiJsonl(text), null, 2) + '\n');
    } catch {
      // Never echo file contents, untrusted data, filesystem paths or provider errors.
      process.stderr.write('portfolio-ci-ai7: invalid_or_unavailable_input\n');
      process.exitCode = 2;
    }
  }
}
