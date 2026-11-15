#!/usr/bin/env node
/** Regenerate only the public, reviewed synthetic demonstration. No user input. */
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseSyntheticFixture, createSyntheticInput } from './local_advisory_acceptance.mjs';
import { parseEventLines } from './ai_intelligence/event_schema.mjs';
import { buildDashboardSnapshot } from './ai_intelligence/dashboard_server.mjs';

export async function buildFreeDemoSnapshot() {
  const cases = parseSyntheticFixture(await readFile(new URL('../tests/fixtures/intelligence_eval_cases.json', import.meta.url), 'utf8'));
  const { events } = parseEventLines(createSyntheticInput(cases));
  return buildDashboardSnapshot(events);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv.length !== 2) {
    process.stderr.write('free-demo-snapshot: invalid_arguments\n');
    process.exitCode = 2;
  } else {
    try { process.stdout.write(JSON.stringify(await buildFreeDemoSnapshot(), null, 2) + '\n'); }
    catch { process.stderr.write('free-demo-snapshot: generation_failed\n'); process.exitCode = 2; }
  }
}
