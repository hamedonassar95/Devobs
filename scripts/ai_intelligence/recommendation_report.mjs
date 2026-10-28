#!/usr/bin/env node
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { EventIngestError, readEventStore } from './event_ingest.mjs';
import {
  applyFeedbackLearning,
  FeedbackLearningError,
  readFeedbackLedger,
  recordRecommendationFeedback,
} from './feedback_learning.mjs';
import { IncidentAnalysisError, analyzeIncidentEvents } from './incident_analysis.mjs';
import { RecommendationError, recommendFromIncidentAnalysis } from './recommendations.mjs';

function usage() {
  return 'Usage: node scripts/ai_intelligence/recommendation_report.mjs --store <local-jsonl-file> [--feedback-ledger <private-jsonl-file>] [--record-feedback <sha256-key> --decision accepted|rejected]';
}

function parseArguments(args) {
  const options = { storePath: null, feedbackLedgerPath: null, feedbackKey: null, decision: null };
  for (let index = 0; index < args.length; index++) {
    const flag = args[index];
    const value = args[index + 1];
    if (!value || value.startsWith('--')) throw new RecommendationError('invalid_arguments');
    if (flag === '--store' && options.storePath === null) options.storePath = value;
    else if (flag === '--feedback-ledger' && options.feedbackLedgerPath === null) options.feedbackLedgerPath = value;
    else if (flag === '--record-feedback' && options.feedbackKey === null) options.feedbackKey = value;
    else if (flag === '--decision' && options.decision === null) options.decision = value;
    else throw new RecommendationError('invalid_arguments');
    index++;
  }
  if (!options.storePath || (options.feedbackKey === null) !== (options.decision === null)
    || (options.feedbackKey !== null && !options.feedbackLedgerPath)
    || (options.decision !== null && !['accepted', 'rejected'].includes(options.decision))) {
    throw new RecommendationError('invalid_arguments');
  }
  return options;
}

export async function main(args = process.argv.slice(2)) {
  try {
    if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    const options = parseArguments(args);
    const events = await readEventStore(options.storePath);
    const analysis = analyzeIncidentEvents(events);
    let result = recommendFromIncidentAnalysis(analysis);
    if (options.feedbackKey !== null) {
      const recommendation = result.recommendations.find(item => item.feedback_key === options.feedbackKey);
      if (!recommendation) throw new FeedbackLearningError('unknown_feedback_key');
      await recordRecommendationFeedback({
        ledgerPath: options.feedbackLedgerPath,
        recommendationKey: recommendation.feedback_key,
        causeId: recommendation.cause_id,
        decision: options.decision,
      });
    }
    if (options.feedbackLedgerPath) {
      result = applyFeedbackLearning(result, await readFeedbackLedger(options.feedbackLedgerPath));
    }
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return 0;
  } catch (error) {
    const code = error instanceof EventIngestError
      || error instanceof FeedbackLearningError
      || error instanceof IncidentAnalysisError
      || error instanceof RecommendationError ? error.code : 'recommendation_failed';
    process.stderr.write(`recommendation-report: ${code}\n${usage()}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
