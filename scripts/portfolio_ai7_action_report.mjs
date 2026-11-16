#!/usr/bin/env node
/** Strict offline reporting boundary for manually requested public CI → AI-7. */
import { readFileSync, writeFileSync, appendFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { PUBLIC_TARGETS } from '../assets/public-ci/portfolio-api.mjs';

const STATES = new Set(['success', 'failure', 'cancelled', 'timed_out', 'neutral',
  'skipped', 'action_required', 'stale', 'running', 'pending', 'missing',
  'unverified', 'startup_failure']);
const TERMINAL = new Set(['success', 'failure', 'cancelled', 'timed_out',
  'neutral', 'skipped', 'action_required']);
const STATUS = new Set(['complete_observation', 'partial_observation', 'no_eligible_evidence']);
const STAGES = ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7'];
const INTS = ['ci_event_count', 'failed_ci_count', 'recommendation_count', 'missing_project_count'];
const bounded = n => Number.isSafeInteger(n) && n >= 0 && n <= PUBLIC_TARGETS.length;
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const keys = (v, allowed) => object(v) && Object.keys(v).every(k => allowed.includes(k));
function fail() { throw new Error('invalid_public_ci_action_report'); }

/** Only validated fixed-field values enter the published report or Markdown. */
export function buildActionArtifact(input) {
  if (!keys(input, ['schema_version', 'status', 'source', 'read_only', 'production_ready',
    'external_provenance_verified', 'checked_count', 'eligible_count', 'excluded_count',
    'observations', 'analysis', 'limitations'])
    || input.schema_version !== 1 || !STATUS.has(input.status)
    || input.source !== 'manual_anonymous_github_public_ci'
    || input.read_only !== true || input.production_ready !== false
    || input.external_provenance_verified !== false || input.checked_count !== 4
    || !bounded(input.eligible_count) || !bounded(input.excluded_count)
    || input.eligible_count + input.excluded_count !== 4
    || !Array.isArray(input.observations) || input.observations.length !== 4) fail();

  const observations = input.observations.map((row, index) => {
    if (!keys(row, ['repository', 'status', 'analysis_eligible'])
      || row.repository !== PUBLIC_TARGETS[index].repo
      || !STATES.has(row.status) || typeof row.analysis_eligible !== 'boolean'
      || (row.analysis_eligible && !TERMINAL.has(row.status))) fail();
    return { repository: PUBLIC_TARGETS[index].repo, status: row.status,
      analysis_eligible: row.analysis_eligible };
  });
  if (observations.filter(x => x.analysis_eligible).length !== input.eligible_count
    || (input.eligible_count === 4) !== (input.status === 'complete_observation')
    || (input.eligible_count === 0) !== (input.status === 'no_eligible_evidence')) fail();

  let analysis = null;
  if (input.eligible_count === 0) {
    if (input.analysis !== null) fail();
  } else {
    const a = input.analysis;
    if (!keys(a, ['summary', 'projects', 'pipeline', 'advisory'])
      || !keys(a.summary, INTS) || INTS.some(k => !bounded(a.summary[k]))
      || a.summary.ci_event_count !== input.eligible_count
      || a.summary.missing_project_count !== input.excluded_count
      || a.summary.recommendation_count !== 0
      || !Array.isArray(a.projects) || a.projects.length !== input.eligible_count
      || !Array.isArray(a.pipeline) || a.pipeline.length !== STAGES.length) fail();

    const expected = observations.filter(x => x.analysis_eligible);
    const projects = a.projects.map(row => {
      if (!keys(row, ['project', 'conclusion']) || !TERMINAL.has(row.conclusion)
        || typeof row.project !== 'string'
        || !expected.some(x => x.repository.endsWith('/' + row.project)
          && x.status === row.conclusion)) fail();
      return { project: row.project, conclusion: row.conclusion };
    });
    if (new Set(projects.map(x => x.project)).size !== projects.length
      || a.summary.failed_ci_count !== projects.filter(x =>
        x.conclusion === 'failure' || x.conclusion === 'timed_out').length) fail();

    const pipeline = a.pipeline.map((stage, index) => {
      if (!keys(stage, ['id', 'status', 'count']) || stage.id !== STAGES[index]
        || !bounded(stage.count) || typeof stage.status !== 'string'
        || !/^[a-z][a-z0-9_]{0,39}$/.test(stage.status)) fail();
      return { id: STAGES[index], status: stage.status, count: stage.count };
    });
    analysis = { summary: Object.fromEntries(INTS.map(k => [k, a.summary[k]])),
      projects, pipeline };
  }
  const artifact = {
    schema_version: 1, status: input.status,
    source: 'manual_anonymous_github_public_ci',
    read_only: true, production_ready: false, external_provenance_verified: false,
    checked_count: 4, eligible_count: input.eligible_count,
    excluded_count: input.excluded_count, observations, analysis,
  };
  const markdown = [
    '## Devobs AI-7 — manually requested public CI observations',
    '', '- Result: **' + artifact.status + '**',
    '- Eligible observations: **' + artifact.eligible_count + '/4**',
    '- Anonymous public metadata only; no private sources, writes or deployments',
    '- Complete observation does not mean passing CI or production readiness.',
    '', '| Public repository | CI state | AI-7 eligible |',
    '| --- | --- | --- |',
    ...observations.map(x => '| ' + x.repository + ' | ' + x.status + ' | '
      + (x.analysis_eligible ? 'yes' : 'no') + ' |'),
    '', 'Requires human review. CI alone cannot establish root cause.',
  ].join('\n') + '\n';
  return { artifact, markdown };
}

export function main(args = process.argv.slice(2), summaryPath = process.env.GITHUB_STEP_SUMMARY) {
  if (args.length !== 4 || args[0] !== '--input' || args[2] !== '--output'
    || !args[1] || !args[3] || args[1].startsWith('--') || args[3].startsWith('--')) {
    process.stderr.write('portfolio-ai7-action-report: invalid_arguments\n');
    return 2;
  }
  try {
    const raw = readFileSync(args[1], 'utf8');
    if (Buffer.byteLength(raw, 'utf8') > 16_384) fail();
    const { artifact, markdown } = buildActionArtifact(JSON.parse(raw));
    writeFileSync(args[3], JSON.stringify(artifact, null, 2) + '\n',
      { flag: 'wx', mode: 0o600 });
    if (summaryPath) appendFileSync(summaryPath, markdown, 'utf8');
    else process.stdout.write(markdown);
    return 0;
  } catch {
    process.stderr.write('portfolio-ai7-action-report: unverified_or_invalid_report\n');
    return 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = main();
}
