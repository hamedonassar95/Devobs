#!/usr/bin/env node
/** Offline, advisory-only pre-step CI classifier; never contacts GitHub. */
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { parseJsonLine } from '../ai_intelligence/event_schema.mjs';

// Only allow established public project aliases and job kinds. Never
// accept arbitrary private repository names or job labels in diagnostics.
const ALLOWED_JOBS_BY_SOURCE = Object.freeze({
  'cineforge-ai': new Set(['android', 'devobs-policy']),
  'phone-repair-assistant-v2': new Set(['repair-monitor', 'scorecard']),
});
const STATES = new Set(['queued', 'in_progress', 'completed']);
const RESULTS = new Set(['success', 'failure', 'cancelled']);
const RUN_FIELDS = new Set(['schema_version', 'source', 'run_status', 'run_conclusion', 'jobs']);
const JOB_FIELDS = new Set(['kind', 'status', 'conclusion', 'runner_id', 'executed_steps']);

export class CiRunnerTriageError extends Error {
  constructor(code) { super(code); this.code = code; }
}
function invalid(code) { throw new CiRunnerTriageError(code); }
function plainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}
function exactKeys(value, keys) {
  return plainObject(value) && Object.keys(value).length === keys.size
    && Object.keys(value).every(key => keys.has(key));
}
function validState(status, conclusion) {
  return STATES.has(status) && (status === 'completed'
    ? RESULTS.has(conclusion) : conclusion === null);
}

/** Classify ONLY supplied, bounded observations, never the root cause. */
export function triageProjectCi(input) {
  const permittedKinds = exactKeys(input, RUN_FIELDS) && typeof input.source === 'string'
    && Object.hasOwn(ALLOWED_JOBS_BY_SOURCE, input.source)
    ? ALLOWED_JOBS_BY_SOURCE[input.source] : null;
  if (!permittedKinds || input.schema_version !== 1
    || !validState(input.run_status, input.run_conclusion)
    || !Array.isArray(input.jobs) || input.jobs.length < 1 || input.jobs.length > 2) {
    invalid('invalid_run');
  }
  const seen = new Set();
  for (const job of input.jobs) {
    if (!exactKeys(job, JOB_FIELDS) || !permittedKinds.has(job.kind)
      || seen.has(job.kind) || !validState(job.status, job.conclusion)
      || !(job.runner_id === null || (Number.isSafeInteger(job.runner_id) && job.runner_id >= 0))
      || !(job.executed_steps === null || (Number.isSafeInteger(job.executed_steps)
        && job.executed_steps >= 0 && job.executed_steps <= 100))
      || (job.runner_id === 0 && job.executed_steps !== null && job.executed_steps > 0)
      || (job.status !== 'completed' && input.run_status === 'completed')
      || (job.status === 'completed' && input.run_status === 'queued')
      || (job.conclusion === 'success' && job.executed_steps === 0)) {
      invalid('invalid_job');
    }
    seen.add(job.kind);
  }
  if (input.run_status === 'completed'
    && (input.run_conclusion === 'success') !== input.jobs.every(j => j.conclusion === 'success')) {
    invalid('inconsistent_conclusion');
  }
  const total = input.jobs.length;
  // Null means the upstream read-only tool omitted this field, NOT numerical zero.
  const incomplete = input.jobs.filter(j => j.runner_id === null || j.executed_steps === null).length;
  const failedNoRunner = input.jobs.filter(j => j.status === 'completed'
    && j.conclusion === 'failure' && j.runner_id === 0 && j.executed_steps === 0).length;
  const assigned = input.jobs.filter(j => j.runner_id > 0).length;
  const executed = input.jobs.filter(j => j.executed_steps > 0).length;

  let code, nextCheck;
  if (input.run_status !== 'completed') {
    code = 'RUN_NOT_COMPLETE';
    nextCheck = 'Read the GitHub run status before drawing a conclusion; do not rerun automatically.';
  } else if (input.run_conclusion === 'cancelled') {
    code = 'RUN_CANCELLED';
    nextCheck = 'Confirm whether the run was intentionally cancelled; do not classify cancellation as a workflow failure or retry automatically.';
  } else if (input.run_conclusion === 'success') {
    code = 'SUCCESS_CLAIM_UNVERIFIED';
    nextCheck = 'Independently verify successful jobs and exact commit in GitHub.';
  } else if (incomplete > 0) {
    code = 'INSUFFICIENT_RUNNER_EVIDENCE';
    nextCheck = 'Runner ID or executed-step count is missing from the evidence source. Inspect the GitHub run-level banner and authenticated job details; never substitute zero, infer an application defect, or retry automatically.';
  } else if (failedNoRunner === total) {
    code = 'FAILURE_BEFORE_RUNNER';
    nextCheck = 'Inspect the GitHub run-level error banner and repository Actions/billing/runner restrictions; do not change application code or retry without new evidence.';
  } else if (executed > 0) {
    code = 'WORKFLOW_EXECUTED_WITH_FAILURE';
    nextCheck = 'Review the first failed step and permitted logs on the exact run; do not infer an application defect without its output.';
  } else {
    code = 'MIXED_OR_PRESTEP_FAILURE';
    nextCheck = 'Inspect job-level status and run-level errors; do not infer a code defect or allocate new runners automatically.';
  }
  return {
    schema_version: 1, source: input.source, mode: 'advisory_only',
    observed_classification: code, underlying_root_cause: 'UNKNOWN',
    provenance_verified: false, jobs_considered: total,
    jobs_failed_before_runner: failedNoRunner, jobs_assigned_runner: assigned,
    jobs_with_executed_steps: executed, jobs_with_incomplete_runner_evidence: incomplete,
    next_read_only_check: nextCheck,
    recommends_code_change: false, requires_human_review: true,
    automatic_execution: false,
  };
}
// Keep the original export for existing CineForge consumers.
export const triageCineForgeCi = triageProjectCi;

export async function main(args = process.argv.slice(2)) {
  try {
    if (args.length !== 2 || args[0] !== '--input' || !args[1] || args[1].startsWith('-')) invalid('invalid_arguments');
    const raw = await readFile(args[1]);
    if (raw.length > 4096) invalid('input_too_large');
    let parsed;
    try { parsed = parseJsonLine(new TextDecoder('utf-8', { fatal: true }).decode(raw)); }
    catch { invalid('invalid_json'); }
    process.stdout.write(JSON.stringify(triageProjectCi(parsed)) + '\n');
    return 0;
  } catch (error) {
    const code = error instanceof CiRunnerTriageError ? error.code : 'input_unavailable';
    process.stderr.write('cineforge-ci-triage: ' + code + '\n');
    return 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
