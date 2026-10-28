import { createHash } from 'node:crypto';
import { parseStoredEvent } from './event_schema.mjs';

export const MAX_ANALYSIS_EVENTS = 10_000;
export const MAX_LOG_EVENTS = 250;
export const MAX_TOKENS_PER_MESSAGE = 128;
export const MAX_CORRELATION_GAP_MS = 6 * 60 * 60 * 1_000;
export const TFIDF_SIMILARITY_THRESHOLD = 0.62;

const CAUSE_RULES = [
  { id: 'timeout', markers: [['ETIMEDOUT', /\betimedout\b/i], ['timeout', /\btimeout\b/i], ['timed_out', /\btimed out\b/i]], description: 'احتمال انتهاء مهلة عملية أو اعتماد.', next_check: 'راجع سجل المهلة وتوفر الاعتماد وحدود إعادة المحاولة.' },
  { id: 'connection', markers: [['ECONNREFUSED', /\beconnrefused\b/i], ['ECONNRESET', /\beconnreset\b/i]], description: 'احتمال رفض اتصال أو قطعه.', next_check: 'تحقق قراءةً من نقطة الاتصال وتوقيت الانقطاع.' },
  { id: 'dns', markers: [['ENOTFOUND', /\benotfound\b/i], ['EAI_AGAIN', /\beai_again\b/i]], description: 'احتمال تعذر حل اسم مضيف.', next_check: 'تحقق من سجل DNS والاسم المهيأ دون تغيير الإعدادات.' },
  { id: 'permission', markers: [['EACCES', /\beacces\b/i], ['permission_denied', /\bpermission denied\b/i]], description: 'احتمال نقص صلاحية على مورد.', next_check: 'راجع هوية العملية وصلاحية المورد بأقل امتياز.' },
  { id: 'dependency', markers: [['module_not_found', /\bmodule not found\b/i], ['cannot_find_module', /\bcannot find module\b/i]], description: 'احتمال تعذر حل وحدة أو اعتماد.', next_check: 'تحقق من قفل الاعتماديات واسم الوحدة ومسار الاستيراد.' },
  { id: 'memory', markers: [['out_of_memory', /\bout of memory\b/i], ['heap_limit', /\bheap out of memory\b/i]], description: 'احتمال بلوغ حد الذاكرة.', next_check: 'راجع استخدام الذاكرة وحدود التشغيل قبل أي تغيير.' },
];

export class IncidentAnalysisError extends Error {
  constructor(code) {
    super(code);
    this.name = 'IncidentAnalysisError';
    this.code = code;
  }
}

function reject(code) {
  throw new IncidentAnalysisError(code);
}

function compareText(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function normalizedTokens(message) {
  const normalized = message.toLowerCase().normalize('NFKC')
    .replace(/\b[0-9a-f]{8}-[0-9a-f-]{27,}\b/gi, ' uuid ')
    .replace(/\b0x[0-9a-f]+\b/gi, ' hexid ')
    .replace(/\b[0-9a-f]{8,64}\b/gi, ' hexid ')
    .replace(/\b\d+(?:\.\d+)?\b/g, ' number ');
  const tokens = normalized.match(/[\p{L}\p{N}_]+/gu) ?? ['empty'];
  if (tokens.length > MAX_TOKENS_PER_MESSAGE) reject('message_too_complex');
  return tokens;
}

function fingerprint(tokens) {
  return `sha256:${createHash('sha256').update(tokens.join(' '), 'utf8').digest('hex').slice(0, 24)}`;
}

function makeVectors(documents) {
  const documentFrequency = new Map();
  for (const tokens of documents) {
    for (const token of new Set(tokens)) documentFrequency.set(token, (documentFrequency.get(token) ?? 0) + 1);
  }
  return documents.map(tokens => {
    const counts = new Map();
    for (const token of tokens) counts.set(token, (counts.get(token) ?? 0) + 1);
    const weights = new Map([...counts].map(([token, count]) => [
      token,
      (count / tokens.length) * (Math.log((documents.length + 1) / (documentFrequency.get(token) + 1)) + 1),
    ]));
    const norm = Math.sqrt([...weights.values()].reduce((sum, weight) => sum + weight * weight, 0));
    return new Map([...weights].map(([token, weight]) => [token, weight / norm]));
  });
}

function cosine(left, right) {
  const [small, large] = left.size <= right.size ? [left, right] : [right, left];
  let score = 0;
  for (const [token, weight] of small) score += weight * (large.get(token) ?? 0);
  return Math.max(0, Math.min(1, score));
}

function rankHypotheses(events) {
  const text = events.map(event => event.data.message).join('\n');
  return CAUSE_RULES.map(rule => {
    const evidence = rule.markers.filter(([, pattern]) => pattern.test(text)).map(([label]) => label);
    return { rule, evidence };
  }).filter(item => item.evidence.length > 0)
    .sort((left, right) => right.evidence.length - left.evidence.length || compareText(left.rule.id, right.rule.id))
    .map(({ rule, evidence }) => ({
      classification: 'POSSIBLE',
      id: rule.id,
      description: rule.description,
      next_check: rule.next_check,
      evidence_markers: evidence,
      heuristic_confidence: evidence.length > 1 ? 'medium' : 'low',
    }));
}

function correlate(events, ciEvents) {
  const firstTime = Date.parse(events[0].occurred_at);
  const exactCommits = new Set();
  for (const event of events) {
    const matches = event.data.message.match(/\b[0-9a-f]{40}\b/gi) ?? [];
    for (const match of matches) exactCommits.add(match.toLowerCase());
  }
  const exact = ciEvents.filter(event => exactCommits.has(event.data.commit_sha)
    && Math.abs(firstTime - Date.parse(event.occurred_at)) <= MAX_CORRELATION_GAP_MS)
    .sort((left, right) => Math.abs(firstTime - Date.parse(left.occurred_at))
      - Math.abs(firstTime - Date.parse(right.occurred_at)))[0];
  if (exact) {
    return {
      classification: 'POSSIBLE',
      basis: 'full_commit_sha_text_match',
      heuristic_confidence: 'medium',
      commit_sha: exact.data.commit_sha,
      conclusion: exact.data.conclusion,
      seconds_from_log_start: Math.round(Math.abs(firstTime - Date.parse(exact.occurred_at)) / 1_000),
    };
  }
  const priorFailure = ciEvents.filter(event => ['failure', 'timed_out'].includes(event.data.conclusion)
    && event.data.commit_sha && Date.parse(event.occurred_at) <= firstTime
    && firstTime - Date.parse(event.occurred_at) <= MAX_CORRELATION_GAP_MS)
    .sort((left, right) => Date.parse(right.occurred_at) - Date.parse(left.occurred_at))[0];
  if (!priorFailure) return { classification: 'UNKNOWN', basis: 'no_bounded_ci_match' };
  return {
    classification: 'POSSIBLE',
    basis: 'nearest_prior_ci_failure_within_six_hours',
    heuristic_confidence: 'low',
    commit_sha: priorFailure.data.commit_sha,
    conclusion: priorFailure.data.conclusion,
    seconds_before_log_start: Math.round((firstTime - Date.parse(priorFailure.occurred_at)) / 1_000),
  };
}

function summarizeCluster(cluster, ciEvents) {
  const events = [...cluster.events].sort((left, right) => compareText(left.occurred_at, right.occurred_at)
    || compareText(left.event_id, right.event_id));
  const severityCounts = {};
  for (const event of events) severityCounts[event.severity] = (severityCounts[event.severity] ?? 0) + 1;
  return {
    fingerprint: cluster.fingerprint,
    count: events.length,
    first_occurred_at: events[0].occurred_at,
    last_occurred_at: events.at(-1).occurred_at,
    severity_counts: severityCounts,
    grouping_methods: [...cluster.groupingMethods].sort(compareText),
    max_similarity: Number(cluster.maxSimilarity.toPrecision(6)),
    hypotheses: rankHypotheses(events),
    correlation: correlate(events, ciEvents),
  };
}

export function analyzeIncidentEvents(records) {
  if (!Array.isArray(records) || records.length > MAX_ANALYSIS_EVENTS) reject('invalid_event_batch');
  const logs = [];
  const ciEvents = [];
  for (const record of records) {
    let event;
    try {
      event = parseStoredEvent(record);
    } catch {
      reject('invalid_event');
    }
    if (event.kind === 'log') logs.push(event);
    if (event.kind === 'ci_result') ciEvents.push(event);
  }
  if (logs.length > MAX_LOG_EVENTS) reject('too_many_log_events');
  if (logs.length === 0) return { log_events: 0, ci_events_considered: ciEvents.length, deployment_correlation: 'unsupported_by_event_schema', clusters: [] };

  logs.sort((left, right) => compareText(left.occurred_at, right.occurred_at) || compareText(left.event_id, right.event_id));
  const documents = logs.map(event => normalizedTokens(event.data.message));
  const vectors = makeVectors(documents);
  const clusters = [];
  const exactClusters = new Map();
  documents.forEach((tokens, index) => {
    const event = logs[index];
    const key = fingerprint(tokens);
    let cluster = exactClusters.get(key);
    let similarity = 1;
    let method = 'normalized_fingerprint';
    if (!cluster) {
      let best = null;
      for (const candidate of clusters) {
        const score = cosine(vectors[index], candidate.representativeVector);
        if (!best || score > best.score) best = { cluster: candidate, score };
      }
      if (best && best.score >= TFIDF_SIMILARITY_THRESHOLD) {
        cluster = best.cluster;
        similarity = best.score;
        method = 'tfidf_cosine';
      } else {
        cluster = { fingerprint: key, events: [], representativeVector: vectors[index], groupingMethods: new Set(), maxSimilarity: 1 };
        clusters.push(cluster);
      }
      exactClusters.set(key, cluster);
    }
    cluster.events.push(event);
    cluster.groupingMethods.add(method);
    cluster.maxSimilarity = Math.max(cluster.maxSimilarity, similarity);
  });
  return {
    log_events: logs.length,
    ci_events_considered: ciEvents.length,
    deployment_correlation: 'unsupported_by_event_schema',
    clusters: clusters.map(cluster => summarizeCluster(cluster, ciEvents))
      .sort((left, right) => compareText(left.first_occurred_at, right.first_occurred_at)
        || compareText(left.fingerprint, right.fingerprint)),
  };
}
