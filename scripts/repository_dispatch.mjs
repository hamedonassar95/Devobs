#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const DISPATCH_EVENT_TYPE = 'devobs_ai_intelligence_ci_passed';
export const SOURCE_REPOSITORY = 'hamedonassar95/DevObs-ai-Intelligence-';
export const TARGET_REPOSITORY = 'hamedonassar95/Devobs';
export const SOURCE_WORKFLOW = 'Devobs AI Intelligence CI';

const API_VERSION = '2022-11-28';
const API_URL = `https://api.github.com/repos/${TARGET_REPOSITORY}/dispatches`;

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

export async function sendDispatch(body, token, fetchImpl = fetch) {
  if (typeof token !== 'string' || token.length === 0) {
    throw new Error('missing_dispatch_credential');
  }

  const response = await fetchImpl(API_URL, {
    method: 'POST',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${token}`,
      'X-GitHub-Api-Version': API_VERSION,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(10_000),
  });

  if (response.status !== 204) {
    throw new Error(`dispatch_http_${response.status}`);
  }
}

export async function main({ eventPath = process.env.GITHUB_EVENT_PATH,
  token = process.env.DEVOBS_REPOSITORY_DISPATCH_TOKEN, fetchImpl = fetch } = {}) {
  try {
    if (!eventPath) throw new Error('missing_event_path');
    const event = JSON.parse(await readFile(eventPath, 'utf8'));
    const body = createDispatchBody(event.workflow_run);
    if (!body) {
      process.stdout.write('Dispatch skipped: workflow run is outside the approved scope.\n');
      return 0;
    }
    await sendDispatch(body, token, fetchImpl);
    process.stdout.write('GitHub accepted the repository_dispatch event.\n');
    return 0;
  } catch (error) {
    const code = error instanceof Error && /^[a-z0-9_]+$/.test(error.message)
      ? error.message
      : 'dispatch_failed';
    process.stderr.write(`repository-dispatch: ${code}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
