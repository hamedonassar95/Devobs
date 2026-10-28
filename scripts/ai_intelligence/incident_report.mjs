#!/usr/bin/env node
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readEventStore } from './event_ingest.mjs';
import { IncidentAnalysisError, analyzeIncidentEvents } from './incident_analysis.mjs';

function usage() {
  return 'Usage: node scripts/ai_intelligence/incident_report.mjs --store <local-jsonl-file>';
}

export async function main(args = process.argv.slice(2)) {
  try {
    if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    if (args.length !== 2 || args[0] !== '--store' || !args[1] || args[1].startsWith('--')) {
      throw new IncidentAnalysisError('invalid_arguments');
    }
    const events = await readEventStore(args[1]);
    process.stdout.write(`${JSON.stringify({ schema_version: 1, ...analyzeIncidentEvents(events) })}\n`);
    return 0;
  } catch (error) {
    const code = error instanceof IncidentAnalysisError || error instanceof EventIngestError
      ? error.code : 'analysis_failed';
    process.stderr.write(`incident-report: ${code}\n${usage()}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
