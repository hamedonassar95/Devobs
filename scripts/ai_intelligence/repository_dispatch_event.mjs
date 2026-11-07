#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { normalizeEvent, EventIngestError } from './event_ingest.mjs';

export const DISPATCH_ACTION = 'devobs_ai_intelligence_ci_passed';
export const SOURCE_REPOSITORY = 'hamedonassar95/DevObs-ai-Intelligence-';
export const SOURCE_WORKFLOW = 'Devobs AI Intelligence CI';

const EXPECTED_PAYLOAD_FIELDS = new Set([
  'source_repository',
  'source_branch',
  'source_sha',
  'source_run_id',
  'source_run_attempt',
  'source_workflow',
  'source_conclusion',
  'source_event',
]);

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}

function isPositiveInteger(value) {
  return Number.isSafeInteger(value) && value > 0;
}

/** Validate a GitHub dispatch and map only approved metadata into AI-1's event schema. */
export function dispatchToAiEvent(dispatch, occurredAt = new Date().toISOString()) {
  if (!isPlainObject(dispatch) || dispatch.action !== DISPATCH_ACTION
    || !isPlainObject(dispatch.client_payload)) {
    throw new EventIngestError('invalid_repository_dispatch');
  }

  const payload = dispatch.client_payload;
  const keys = Object.keys(payload);
  if (keys.length !== EXPECTED_PAYLOAD_FIELDS.size || keys.some(key => !EXPECTED_PAYLOAD_FIELDS.has(key))) {
    throw new EventIngestError('invalid_repository_dispatch_fields');
  }
  if (payload.source_repository !== SOURCE_REPOSITORY || payload.source_branch !== 'main'
    || payload.source_workflow !== SOURCE_WORKFLOW || payload.source_conclusion !== 'success'
    || payload.source_event !== 'push' || !isPositiveInteger(payload.source_run_id)
    || !isPositiveInteger(payload.source_run_attempt)
    || typeof payload.source_sha !== 'string' || !/^[0-9a-f]{40}$/.test(payload.source_sha)) {
    throw new EventIngestError('repository_dispatch_out_of_scope');
  }

  return normalizeEvent({
    schema_version: 1,
    occurred_at: occurredAt,
    source: 'github_actions',
    kind: 'ci_result',
    severity: 'info',
    data: {
      workflow: SOURCE_WORKFLOW,
      job: 'build-and-validate',
      conclusion: 'success',
      commit_sha: payload.source_sha,
    },
  });
}

/** Render only the validated, public CI provenance fields for a GitHub job summary. */
export function renderDispatchSummary(dispatch) {
  dispatchToAiEvent(dispatch);
  const payload = dispatch.client_payload;
  const sourceBaseUrl = `https://github.com/${SOURCE_REPOSITORY}`;
  return [
    '## Validated AI CI dispatch metadata',
    '',
    `- Source repository: [\`${payload.source_repository}\`](${sourceBaseUrl})`,
    `- Source workflow: \`${payload.source_workflow}\``,
    `- Source run: [${payload.source_run_id}](${sourceBaseUrl}/actions/runs/${payload.source_run_id}) (attempt ${payload.source_run_attempt})`,
    `- Source commit: [\`${payload.source_sha}\`](${sourceBaseUrl}/commit/${payload.source_sha})`,
    `- Source event/result: \`${payload.source_event}\` / \`${payload.source_conclusion}\``,
    '',
    'The receiver validated these payload claims before AI-1 ingestion; this summary is not independent cryptographic authentication of the sender.',
    '',
  ].join('\n');
}

export async function main(args = process.argv.slice(2)) {
  try {
    const summaryMode = args[0] === '--summary';
    const inputPath = summaryMode ? args[1] : args[0];
    if (args.length !== (summaryMode ? 2 : 1)
      || typeof inputPath !== 'string' || inputPath.length === 0) {
      throw new EventIngestError('invalid_arguments');
    }
    const raw = await readFile(inputPath, 'utf8');
    if (Buffer.byteLength(raw, 'utf8') > 65_535) throw new EventIngestError('input_too_large');
    let dispatch;
    try {
      dispatch = JSON.parse(raw);
    } catch {
      throw new EventIngestError('invalid_json');
    }
    if (summaryMode) {
      process.stdout.write(renderDispatchSummary(dispatch));
      return 0;
    }
    const event = dispatchToAiEvent(dispatch);
    process.stdout.write(`${JSON.stringify({
      schema_version: event.schema_version,
      occurred_at: event.occurred_at,
      source: event.source,
      kind: event.kind,
      severity: event.severity,
      data: event.data,
    })}\n`);
    return 0;
  } catch (error) {
    const code = error instanceof EventIngestError ? error.code : 'dispatch_unavailable';
    process.stderr.write(`repository-dispatch: ${code}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
