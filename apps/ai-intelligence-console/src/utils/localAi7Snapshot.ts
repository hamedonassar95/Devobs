export type LocalAi7Stage = {
  id: `AI-${1 | 2 | 3 | 4 | 5 | 6 | 7}`;
  status: string;
  count: number;
};

export type LocalAi7Recommendation = {
  review_order: number;
  cause_id: 'timeout' | 'connection' | 'dns' | 'permission' | 'dependency' | 'memory';
  classification: 'POSSIBLE';
  heuristic_signal: 'low' | 'medium';
  event_count: number;
  evidence_markers: string[];
  requires_human_approval: true;
  automatic_execution: false;
};

export type LocalAi7Snapshot = {
  source: 'local_ai7_snapshot';
  status: 'local_snapshot';
  mode: 'local_advisory_only';
  read_only: true;
  summary: {
    event_count: number;
    log_cluster_count: number;
    recommendation_count: number;
    anomaly_candidate_count: number;
  };
  stages: LocalAi7Stage[];
  recommendations: LocalAi7Recommendation[];
};

const SUMMARY_KEYS = [
  'event_count',
  'log_cluster_count',
  'recommendation_count',
  'anomaly_candidate_count',
] as const;
const STAGE_IDS = ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7'] as const;
const RECOMMENDATION_KEYS = [
  'review_order',
  'cause_id',
  'classification',
  'heuristic_signal',
  'event_count',
  'evidence_markers',
  'requires_human_approval',
  'automatic_execution',
] as const;
const EVIDENCE_BY_CAUSE: Readonly<Record<LocalAi7Recommendation['cause_id'], readonly string[]>> = {
  timeout: ['ETIMEDOUT', 'timeout', 'timed_out'],
  connection: ['ECONNREFUSED', 'ECONNRESET'],
  dns: ['ENOTFOUND', 'EAI_AGAIN'],
  permission: ['EACCES', 'permission_denied'],
  dependency: ['module_not_found', 'cannot_find_module'],
  memory: ['out_of_memory', 'heap_limit'],
};
const MAX_COUNT = 10_000_000;
const MAX_VISIBLE_RECOMMENDATIONS = 5;
const MAX_EVIDENCE_MARKERS = 8;

type RecordValue = Record<string, unknown>;

function isRecord(value: unknown): value is RecordValue {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function hasExactKeys(value: RecordValue, keys: readonly string[]): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every(key => Object.hasOwn(value, key));
}

function isCount(value: unknown): value is number {
  return typeof value === 'number'
    && Number.isSafeInteger(value)
    && value >= 0
    && value <= MAX_COUNT;
}

function parseSummary(value: unknown): LocalAi7Snapshot['summary'] | null {
  if (!isRecord(value) || !hasExactKeys(value, SUMMARY_KEYS)
      || SUMMARY_KEYS.some(key => !isCount(value[key]))) {
    return null;
  }
  return {
    event_count: value.event_count as number,
    log_cluster_count: value.log_cluster_count as number,
    recommendation_count: value.recommendation_count as number,
    anomaly_candidate_count: value.anomaly_candidate_count as number,
  };
}

function parseStages(value: unknown): LocalAi7Stage[] | null {
  if (!Array.isArray(value) || value.length !== STAGE_IDS.length) return null;
  const stages: LocalAi7Stage[] = [];
  for (const [index, item] of value.entries()) {
    if (!isRecord(item) || !hasExactKeys(item, ['id', 'status', 'count'])
        || item.id !== STAGE_IDS[index]
        || typeof item.status !== 'string'
        || !/^[a-z_]{1,32}$/.test(item.status)
        || !isCount(item.count)) {
      return null;
    }
    stages.push({ id: STAGE_IDS[index], status: item.status, count: item.count });
  }
  return stages;
}

function parseRecommendations(value: unknown, total: number): LocalAi7Recommendation[] | null {
  const expectedLength = Math.min(total, MAX_VISIBLE_RECOMMENDATIONS);
  if (!Array.isArray(value) || value.length !== expectedLength) return null;
  const recommendations: LocalAi7Recommendation[] = [];
  for (const [index, item] of value.entries()) {
    if (!isRecord(item) || !hasExactKeys(item, RECOMMENDATION_KEYS)
        || item.review_order !== index + 1
        || typeof item.cause_id !== 'string'
        || !Object.hasOwn(EVIDENCE_BY_CAUSE, item.cause_id)
        || item.classification !== 'POSSIBLE'
        || (item.heuristic_signal !== 'low' && item.heuristic_signal !== 'medium')
        || !isCount(item.event_count) || item.event_count === 0
        || item.requires_human_approval !== true
        || item.automatic_execution !== false
        || !Array.isArray(item.evidence_markers)
        || item.evidence_markers.length < 1
        || item.evidence_markers.length > MAX_EVIDENCE_MARKERS
        || item.evidence_markers.some(marker =>
          typeof marker !== 'string'
          || !EVIDENCE_BY_CAUSE[item.cause_id as LocalAi7Recommendation['cause_id']].includes(marker))) {
      return null;
    }
    recommendations.push({
      review_order: index + 1,
      cause_id: item.cause_id as LocalAi7Recommendation['cause_id'],
      classification: 'POSSIBLE',
      heuristic_signal: item.heuristic_signal,
      event_count: item.event_count,
      evidence_markers: [...item.evidence_markers] as string[],
      requires_human_approval: true,
      automatic_execution: false,
    });
  }
  return recommendations;
}

/** Validate the local AI-7 response before rendering any advisory content. */
export function parseLocalAi7Snapshot(value: unknown): LocalAi7Snapshot | null {
  if (!isRecord(value)
      || !hasExactKeys(value, ['source', 'status', 'mode', 'read_only', 'summary', 'stages', 'recommendations'])
      || value.source !== 'local_ai7_snapshot'
      || value.status !== 'local_snapshot'
      || value.mode !== 'local_advisory_only'
      || value.read_only !== true) {
    return null;
  }

  const summary = parseSummary(value.summary);
  if (!summary) return null;
  const stages = parseStages(value.stages);
  if (!stages) return null;
  const recommendations = parseRecommendations(value.recommendations, summary.recommendation_count);
  if (!recommendations) return null;

  return {
    source: 'local_ai7_snapshot',
    status: 'local_snapshot',
    mode: 'local_advisory_only',
    read_only: true,
    summary,
    stages,
    recommendations,
  };
}
