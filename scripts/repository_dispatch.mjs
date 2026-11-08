#!/usr/bin/env node

import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const DISPATCH_EVENT_TYPE = 'devobs_ai_intelligence_ci_passed';
export const SOURCE_REPOSITORY = 'hamedonassar95/Devobs';
export const TARGET_REPOSITORY = 'hamedonassar95/Devobs';
export const SOURCE_WORKFLOW = 'Devobs AI Intelligence CI';

function isPositiveInteger(value) {
  return Number.isSafeInteger(value) && value > 0;
}

/** Return a bounded, metadata-only event for an approved successful main push. */
export function createDispatchBody(run) {
  if (!run || typeof run !== 'object' || Array.isArray(run)) return null;
  if (run.name !== SOURCE_WORKFLOW || run.event !== 'push' || run.head_branch !== 'main'
    || run.conclusion !== 'success' || run.head_repository?.full_name !== SOURCE_REPOSITORY
    || !isPositiveInteger(run.id) || !isPositiveInteger(run.run_attempt)
    || typeof run.head_sha !== 'string' || !/^[0-9a-f]{40}$/.test(run.head_sha)) {
    return null;
  }

  return {
    event_type: DISPATCH_EVENT_TYPE,
    client_payload: {
      source_repository: SOURCE_REPOSITORY,
      source_branch: 'main',
      source_sha: run.head_sha,
      source_run_id: run.id,
      source_run_attempt: run.run_attempt,
      source_workflow: SOURCE_WORKFLOW,
      source_conclusion: 'success',
      source_event: 'push',
    },
  };
}

export async function prepareDispatchPayload(eventPath, outputPath) {
  if (typeof eventPath !== 'string' || eventPath.length === 0
    || typeof outputPath !== 'string' || outputPath.length === 0) {
    throw new Error('invalid_dispatch_arguments');
  }
  const event = JSON.parse(await readFile(eventPath, 'utf8'));
  const body = createDispatchBody(event.workflow_run);
  if (!body) throw new Error('dispatch_out_of_scope');
  await writeFile(outputPath, JSON.stringify(body), { encoding: 'utf8', flag: 'wx', mode: 0o600 });
  return body;
}

export function classifyDispatchError(error) {
  if (error instanceof Error && /^[a-z0-9_]+$/.test(error.message)) return error.message;
  if (error?.name === 'AbortError' || error?.name === 'TimeoutError') return 'dispatch_timeout';
  if (error?.name === 'TypeError') return 'dispatch_transport_error';
  return 'dispatch_failed';
}

export async function main(args = process.argv.slice(2)) {
  try {
    if (args.length !== 3 || args[0] !== '--prepare') throw new Error('invalid_dispatch_arguments');
    await prepareDispatchPayload(args[1], args[2]);
    process.stdout.write('Metadata-only dispatch payload prepared.\n');
    return 0;
  } catch (error) {
    process.stderr.write(`repository-dispatch: ${classifyDispatchError(error)}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
