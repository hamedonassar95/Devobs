const EVENT_KINDS = ['log', 'incident', 'ci_result', 'server_metric'];
const SEVERITIES = ['debug', 'info', 'warning', 'error', 'critical', 'unknown'];
const CAUSE_LABELS = Object.freeze({
  timeout: 'مهلة',
  connection: 'اتصال',
  dns: 'DNS',
  permission: 'صلاحية',
  dependency: 'اعتماد',
  memory: 'ذاكرة',
});

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function count(value) {
  return Number.isSafeInteger(value) && value >= 0 && value <= 1_000_000 ? value : 0;
}

function countsFor(source, keys) {
  const safeSource = isRecord(source) ? source : {};
  return keys.map(key => `${key}: ${count(safeSource[key])}`);
}

function aggregateLines(snapshot) {
  const summary = snapshot.summary;
  const lines = [
    'الأعداد الإجمالية',
    `الأحداث: ${count(summary.event_count)}`,
    `السجلات: ${count(summary.log_event_count)}`,
    `مجموعات السجلات: ${count(summary.log_cluster_count)}`,
    `التوصيات: ${count(summary.recommendation_count)}`,
    `مرشحو الشذوذ: ${count(summary.anomaly_candidate_count)}`,
    `استقراءات الاتجاه: ${count(summary.forecast_count)}`,
    '',
    'الأحداث بحسب النوع',
    ...countsFor(summary.kind_counts, EVENT_KINDS),
    '',
    'الأحداث بحسب الشدة',
    ...countsFor(summary.severity_counts, SEVERITIES),
    '',
    'الفئات الاسترشادية',
  ];

  const causeCounts = Object.fromEntries(Object.keys(CAUSE_LABELS).map(key => [key, 0]));
  if (Array.isArray(snapshot.incidents)) {
    for (const incident of snapshot.incidents.slice(0, 100)) {
      if (!isRecord(incident) || !Array.isArray(incident.hypotheses)) continue;
      for (const hypothesis of incident.hypotheses) {
        if (isRecord(hypothesis) && Object.hasOwn(causeCounts, hypothesis.cause_id)) {
          causeCounts[hypothesis.cause_id]++;
        }
      }
    }
  }
  for (const [cause, label] of Object.entries(CAUSE_LABELS)) lines.push(`${label}: ${causeCounts[cause]}`);
  return lines;
}

/** Build a report from allowlisted aggregates only; never copy log text or identifiers. */
export function buildGoogleDocsReport(snapshot, createdAt = new Date()) {
  if (!isRecord(snapshot) || !isRecord(snapshot.summary) || !(createdAt instanceof Date)
    || !Number.isFinite(createdAt.getTime())) {
    throw new TypeError('invalid_google_docs_report_input');
  }
  return {
    title: `Devobs - ملخص تشغيلي ${createdAt.toISOString().slice(0, 10)}`,
    text: ['Devobs — ملخص تشغيلي منقّح', `أُنشئ: ${createdAt.toISOString()}`, '',
      'تنبيه: هذا ملخص محلي استرشادي؛ التصنيفات لا تثبت سبب الحادثة، ولا تنفذ أي إجراء.', '',
      ...aggregateLines(snapshot), '',
      'البيانات المرسلة لا تتضمن نصوص السجلات أو أسماء العملاء أو معرّفات المشاريع أو الخوادم.'].join('\n'),
  };
}

/** Strict, credential-free TXT export; provider exports retain their old contract. */
export function buildLocalTextReport(snapshot, { mode, createdAt = new Date() } = {}) {
  const modes = { synthetic_fixed: ['synthetic', 'عينة اصطناعية ثابتة'],
    local_snapshot: ['local', 'لقطة محلية عند بدء الخادم'] };
  const reject = () => { throw new TypeError('invalid_local_text_report_input'); };
  const validCount = value => Number.isSafeInteger(value) && value >= 0 && value <= 1_000_000;
  if (!isRecord(snapshot) || !isRecord(snapshot.summary) || typeof mode !== 'string' || !Object.hasOwn(modes, mode)
    || !(createdAt instanceof Date) || !Number.isFinite(createdAt.getTime())) reject();
  const summary = snapshot.summary;
  for (const key of ['event_count', 'log_event_count', 'log_cluster_count', 'recommendation_count',
    'anomaly_candidate_count', 'forecast_count']) if (!validCount(summary[key])) reject();
  for (const [key, names] of [['kind_counts', EVENT_KINDS], ['severity_counts', SEVERITIES]]) {
    if (!isRecord(summary[key]) || names.some(name => !Object.hasOwn(summary[key], name)
      || !validCount(summary[key][name]))
      || names.reduce((sum, name) => sum + summary[key][name], 0) !== summary.event_count) reject();
  }
  if (summary.log_event_count !== summary.kind_counts.log || !Array.isArray(snapshot.incidents)
    || snapshot.incidents.length > 100 || snapshot.incidents.length !== summary.log_cluster_count
    || summary.log_cluster_count > summary.log_event_count) reject();
  for (const incident of snapshot.incidents) {
    if (!isRecord(incident) || !Array.isArray(incident.hypotheses)
      || incident.hypotheses.length > Object.keys(CAUSE_LABELS).length) reject();
    const seen = new Set();
    for (const hypothesis of incident.hypotheses) {
      if (!isRecord(hypothesis) || typeof hypothesis.cause_id !== 'string'
        || !Object.hasOwn(CAUSE_LABELS, hypothesis.cause_id)
        || seen.has(hypothesis.cause_id)) reject();
      seen.add(hypothesis.cause_id);
    }
  }
  const [prefix, label] = modes[mode];
  return { filename: `devobs-${prefix}-report-${createdAt.toISOString().slice(0, 10)}.txt`,
    text: ['Devobs — تقرير محلي منقّح', label, `وقت إنشاء الملف: ${createdAt.toISOString()}`, '',
      'الأعداد تخص اللقطة المعروضة؛ وقت إنشاء الملف لا يثبت حداثة بياناتها.',
      'التصنيفات استرشادية وتحتاج مراجعة بشرية. لا تثبت سبب الحادثة أو جاهزية الإنتاج.', '',
      ...aggregateLines(snapshot), '',
      'بيانات التقرير أعداد وفئات عامة فقط. المذكرات والنصوص الخام والمعرّفات مستبعدة.'].join('\n') + '\n' };
}

function validAccessToken(value) {
  return typeof value === 'string' && value.length >= 16 && value.length <= 4096
    && !/[\s\x00-\x1f\x7f]/.test(value);
}

/** Create a new Google Doc only; token is used in-memory and never persisted by this module. */
export async function createGoogleDoc({ accessToken, title, text, fetchImpl = fetch }) {
  if (!validAccessToken(accessToken) || typeof title !== 'string' || title.length < 1 || title.length > 200
    || typeof text !== 'string' || text.length < 1 || text.length > 16_384
    || typeof fetchImpl !== 'function') {
    throw new TypeError('invalid_google_docs_request');
  }

  let response;
  try {
    response = await fetchImpl('https://docs.googleapis.com/v1/documents', {
      method: 'POST',
      redirect: 'error',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
  } catch {
    throw new Error('google_docs_create_failed');
  }
  if (!response.ok) throw new Error('google_docs_create_failed');

  let created;
  try {
    created = await response.json();
  } catch {
    throw new Error('google_docs_invalid_response');
  }
  if (!isRecord(created) || typeof created.documentId !== 'string'
    || !/^[A-Za-z0-9_-]{5,256}$/.test(created.documentId)) {
    throw new Error('google_docs_invalid_response');
  }

  let updated;
  try {
    updated = await fetchImpl(`https://docs.googleapis.com/v1/documents/${created.documentId}:batchUpdate`, {
      method: 'POST',
      redirect: 'error',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ requests: [{ insertText: { location: { index: 1 }, text } }] }),
    });
  } catch {
    throw new Error('google_docs_write_failed');
  }
  if (!updated.ok) throw new Error('google_docs_write_failed');
  return { documentId: created.documentId };
}
