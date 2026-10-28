#!/usr/bin/env node
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readEventStore } from './event_ingest.mjs';
import { AnomalyAnalysisError, analyzeMetricEvents } from './anomaly_detector.mjs';

function reject(code) {
  throw new AnomalyAnalysisError(code);
}

function parseArgs(args) {
  if (args.length === 1 && ['--help', '-h'].includes(args[0])) return { help: true };
  if (args.length !== 2 || args[0] !== '--store' || !args[1] || args[1].startsWith('--')) reject('invalid_arguments');
  return { storePath: args[1] };
}

function usage() {
  return 'Usage: node scripts/ai_intelligence/anomaly_report.mjs --store <local-jsonl-file>';
}

export async function main(args = process.argv.slice(2)) {
  try {
    const options = parseArgs(args);
    if (options.help) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    const events = await readEventStore(options.storePath);
    const metrics = analyzeMetricEvents(events);
    process.stdout.write(`${JSON.stringify({
      schema_version: 1,
      evaluated_metrics: metrics.length,
      anomaly_candidates: metrics.filter(metric => metric.status === 'anomaly_candidate').length,
      metrics,
    })}\n`);
    return 0;
  } catch (error) {
    const code = error instanceof AnomalyAnalysisError || error instanceof EventIngestError
      ? error.code : 'analysis_failed';
    process.stderr.write(`anomaly-report: ${code}\n${usage()}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
