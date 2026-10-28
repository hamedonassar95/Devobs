#!/usr/bin/env node
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readEventStore } from './event_ingest.mjs';
import { IncidentAnalysisError, analyzeIncidentEvents } from './incident_analysis.mjs';
import { RecommendationError, recommendFromIncidentAnalysis } from './recommendations.mjs';

function usage() {
  return 'Usage: node scripts/ai_intelligence/recommendation_report.mjs --store <local-jsonl-file>';
}

export async function main(args = process.argv.slice(2)) {
  try {
    if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    if (args.length !== 2 || args[0] !== '--store' || !args[1] || args[1].startsWith('--')) {
      throw new RecommendationError('invalid_arguments');
    }
    const events = await readEventStore(args[1]);
    const analysis = analyzeIncidentEvents(events);
    const result = recommendFromIncidentAnalysis(analysis);
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return 0;
  } catch (error) {
    const code = error instanceof EventIngestError
      || error instanceof IncidentAnalysisError
      || error instanceof RecommendationError ? error.code : 'recommendation_failed';
    process.stderr.write(`recommendation-report: ${code}\n${usage()}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
