import { createHash, randomUUID } from 'node:crypto';
import { constants } from 'node:fs';
import { open, realpath, rename, unlink } from 'node:fs/promises';
import path from 'node:path';

export const MIN_FEEDBACK_DECISIONS_FOR_RANKING = 3;
export const MAX_FEEDBACK_RECORDS = 10_000;
export const MAX_FEEDBACK_BYTES = 1_048_576;

const KEY_PATTERN = /^sha256:[0-9a-f]{64}$/;
const CAUSE_IDS = new Set(['timeout', 'connection', 'dns', 'permission', 'dependency', 'memory']);
const DECISIONS = new Set(['accepted', 'rejected']);
const FIELDS = new Set(['schema_version', 'recommendation_key', 'cause_id', 'decision', 'recorded_at']);

export class FeedbackLearningError extends Error {
  constructor(code) {
    super(code);
    this.name = 'FeedbackLearningError';
    this.code = code;
  }
}

function reject(code) {
  throw new FeedbackLearningError(code);
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function validateTimestamp(value) {
  if (typeof value !== 'string' || value.length > 24) reject('invalid_feedback');
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp) || new Date(timestamp).toISOString() !== value) reject('invalid_feedback');
}

function validateFeedback(record) {
  if (!isPlainObject(record) || Object.keys(record).length !== FIELDS.size
    || Object.keys(record).some(key => !FIELDS.has(key))
    || record.schema_version !== 1
    || typeof record.recommendation_key !== 'string' || !KEY_PATTERN.test(record.recommendation_key)
    || typeof record.cause_id !== 'string' || !CAUSE_IDS.has(record.cause_id)
    || typeof record.decision !== 'string' || !DECISIONS.has(record.decision)) {
    reject('invalid_feedback');
  }
  validateTimestamp(record.recorded_at);
  return record;
}

function makeRecord(recommendationKey, causeId, decision, recordedAt = new Date().toISOString()) {
  return validateFeedback({
    schema_version: 1,
    recommendation_key: recommendationKey,
    cause_id: causeId,
    decision,
    recorded_at: recordedAt,
  });
}

export function createRecommendationFeedbackKey(clusterFingerprint, causeId) {
  if (typeof clusterFingerprint !== 'string' || !/^sha256:[0-9a-f]{24}$/.test(clusterFingerprint)
    || typeof causeId !== 'string' || !CAUSE_IDS.has(causeId)) reject('invalid_feedback_target');
  const digest = createHash('sha256').update(`${clusterFingerprint}\0${causeId}`, 'utf8').digest('hex');
  return `sha256:${digest}`;
}

function parseLedger(text) {
  if (typeof text !== 'string' || Buffer.byteLength(text, 'utf8') > MAX_FEEDBACK_BYTES) reject('ledger_too_large');
  if (text === '') return [];
  const lines = text.split('\n');
  if (lines.at(-1) === '') lines.pop();
  if (lines.length > MAX_FEEDBACK_RECORDS || lines.some(line => line.length === 0)) reject('invalid_ledger');
  return lines.map(line => {
    let record;
    try {
      record = JSON.parse(line);
    } catch {
      reject('invalid_ledger');
    }
    try {
      return validateFeedback(record);
    } catch {
      reject('invalid_ledger');
    }
  });
}

async function resolveLedgerPath(ledgerPath) {
  if (typeof ledgerPath !== 'string' || ledgerPath.length === 0 || ledgerPath.length > 4_096) reject('invalid_ledger_path');
  const absolutePath = path.resolve(ledgerPath);
  const basename = path.basename(absolutePath);
  if (!basename || basename === '.' || basename === '..') reject('invalid_ledger_path');
  try {
    return path.join(await realpath(path.dirname(absolutePath)), basename);
  } catch {
    reject('ledger_unavailable');
  }
}

async function readResolvedLedger(ledgerPath, allowMissing) {
  let handle;
  try {
    if (typeof constants.O_NOFOLLOW !== 'number') reject('platform_no_follow_unsupported');
    handle = await open(ledgerPath, constants.O_RDONLY | constants.O_NOFOLLOW);
    const info = await handle.stat();
    if (!info.isFile()) reject('unsafe_ledger');
    if ((info.mode & 0o077) !== 0) reject('unsafe_ledger_permissions');
    if (info.size > MAX_FEEDBACK_BYTES) reject('ledger_too_large');
    const bytes = await handle.readFile();
    if (bytes.length > MAX_FEEDBACK_BYTES) reject('ledger_too_large');
    let text;
    try {
      text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    } catch {
      reject('invalid_ledger');
    }
    return parseLedger(text);
  } catch (error) {
    if (error instanceof FeedbackLearningError) throw error;
    if (error?.code === 'ENOENT' && allowMissing) return [];
    if (error?.code === 'ELOOP') reject('unsafe_ledger');
    reject(error?.code === 'ENOENT' ? 'ledger_missing' : 'ledger_unavailable');
  } finally {
    await handle?.close().catch(() => {});
  }
}

export async function readFeedbackLedger(ledgerPath) {
  const resolvedPath = await resolveLedgerPath(ledgerPath);
  return readResolvedLedger(resolvedPath, false);
}

export async function recordRecommendationFeedback({ ledgerPath, recommendationKey, causeId, decision, recordedAt }) {
  const record = makeRecord(recommendationKey, causeId, decision, recordedAt);
  const resolvedPath = await resolveLedgerPath(ledgerPath);
  const lockPath = `${resolvedPath}.lock`;
  let lockHandle;
  let tempHandle;
  let tempPath;
  let lockCreated = false;
  try {
    if (typeof constants.O_NOFOLLOW !== 'number') reject('platform_no_follow_unsupported');
    try {
      lockHandle = await open(lockPath, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
      lockCreated = true;
    } catch (error) {
      if (error?.code === 'EEXIST') reject('ledger_locked');
      if (error?.code === 'ELOOP') reject('unsafe_ledger');
      reject('ledger_unavailable');
    }

    const records = await readResolvedLedger(resolvedPath, true);
    if (records.length >= MAX_FEEDBACK_RECORDS) reject('ledger_record_limit');
    const nextText = `${[...records, record].map(item => JSON.stringify(item)).join('\n')}\n`;
    if (Buffer.byteLength(nextText, 'utf8') > MAX_FEEDBACK_BYTES) reject('ledger_too_large');

    tempPath = `${resolvedPath}.${randomUUID()}.tmp`;
    tempHandle = await open(tempPath, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
    await tempHandle.writeFile(nextText, 'utf8');
    await tempHandle.sync();
    await tempHandle.close();
    tempHandle = undefined;
    await rename(tempPath, resolvedPath);
    tempPath = undefined;
    return { recorded: true, decision: record.decision };
  } catch (error) {
    if (error instanceof FeedbackLearningError) throw error;
    reject('ledger_unavailable');
  } finally {
    await tempHandle?.close().catch(() => {});
    if (tempPath) await unlink(tempPath).catch(() => {});
    await lockHandle?.close().catch(() => {});
    if (lockCreated) await unlink(lockPath).catch(() => {});
  }
}

function latestDecisionByRecommendation(records) {
  const latest = new Map();
  for (const record of records) {
    validateFeedback(record);
    const previous = latest.get(record.recommendation_key);
    if (!previous || Date.parse(record.recorded_at) >= Date.parse(previous.recorded_at)) {
      latest.set(record.recommendation_key, record);
    }
  }
  return [...latest.values()];
}

export function applyFeedbackLearning(recommendationReport, feedbackRecords) {
  if (!isPlainObject(recommendationReport) || !Array.isArray(recommendationReport.recommendations)
    || !Array.isArray(feedbackRecords)) reject('invalid_learning_input');
  const aggregate = new Map();
  for (const record of latestDecisionByRecommendation(feedbackRecords)) {
    const current = aggregate.get(record.cause_id) ?? { accepted: 0, rejected: 0 };
    current[record.decision]++;
    aggregate.set(record.cause_id, current);
  }

  const ranked = recommendationReport.recommendations.map((recommendation, index) => {
    if (!isPlainObject(recommendation) || typeof recommendation.feedback_key !== 'string'
      || !KEY_PATTERN.test(recommendation.feedback_key) || typeof recommendation.cause_id !== 'string'
      || !CAUSE_IDS.has(recommendation.cause_id)) reject('invalid_learning_input');
    const counts = aggregate.get(recommendation.cause_id) ?? { accepted: 0, rejected: 0 };
    const sampleCount = counts.accepted + counts.rejected;
    return {
      index,
      counts,
      recommendation: {
        ...recommendation,
        feedback_review_signal: {
          accepted_count: counts.accepted,
          rejected_count: counts.rejected,
          sample_count: sampleCount,
          smoothed_acceptance_rate: sampleCount === 0 ? null : Number(((counts.accepted + 1) / (sampleCount + 2)).toFixed(4)),
          status: sampleCount >= MIN_FEEDBACK_DECISIONS_FOR_RANKING ? 'ranking_eligible' : 'insufficient_history',
        },
      },
    };
  });

  const hasEligibleSignal = ranked.some(item => item.recommendation.feedback_review_signal.status === 'ranking_eligible');
  if (hasEligibleSignal) {
    ranked.sort((left, right) => {
      const leftSignal = left.recommendation.feedback_review_signal;
      const rightSignal = right.recommendation.feedback_review_signal;
      if (leftSignal.status !== rightSignal.status) return leftSignal.status === 'ranking_eligible' ? -1 : 1;
      if (leftSignal.status === 'ranking_eligible'
        && leftSignal.smoothed_acceptance_rate !== rightSignal.smoothed_acceptance_rate) {
        return rightSignal.smoothed_acceptance_rate - leftSignal.smoothed_acceptance_rate;
      }
      return left.index - right.index;
    });
  }

  return {
    ...recommendationReport,
    mode: 'suggestion_only',
    review_order_note: hasEligibleSignal
      ? 'Eligible groups are ordered by a smoothed local operator-acceptance signal, not by probability or verified correctness.'
      : recommendationReport.review_order_note,
    feedback_learning: {
      source: 'explicit_local_operator_feedback',
      minimum_distinct_recommendations: MIN_FEEDBACK_DECISIONS_FOR_RANKING,
      ranking_adjusted: hasEligibleSignal,
      automatic_execution: false,
    },
    recommendations: ranked.map((item, index) => ({ ...item.recommendation, review_order: index + 1 })),
  };
}
