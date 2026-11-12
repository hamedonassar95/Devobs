const SUMMARY_FIELDS = Object.freeze([
  ['الأحداث', 'event_count'],
  ['السجلات', 'log_event_count'],
  ['نتائج CI', 'ci_event_count'],
  ['مجموعات السجلات', 'log_cluster_count'],
  ['مجموعات بلا فرضية معروفة', 'unknown_group_count'],
  ['التوصيات', 'recommendation_count'],
  ['سلاسل المقاييس', 'metric_series_count'],
  ['مرشحو الشذوذ', 'anomaly_candidate_count'],
  ['استقراءات الاتجاه', 'forecast_count'],
  ['تحذيرات نطاق الاستقراء', 'trend_range_warning_count'],
  ['ترتيب مدعوم بملاحظات محلية', 'feedback_ranked_recommendation_count'],
]);
const EVENT_KINDS = Object.freeze([
  ['سجلات', 'log'],
  ['حوادث', 'incident'],
  ['نتائج CI', 'ci_result'],
  ['مقاييس الخادم', 'server_metric'],
]);
const SEVERITIES = Object.freeze([
  ['تصحيح', 'debug'],
  ['معلومات', 'info'],
  ['تحذير', 'warning'],
  ['خطأ', 'error'],
  ['حرج', 'critical'],
  ['غير معروف', 'unknown'],
]);
const MAX_COUNT = 1_000_000;
const MAX_MESSAGE_BYTES = 32_000;
const CHAT_API_BASE = 'https://chat.googleapis.com/v1';
export const GOOGLE_CHAT_SCOPE = 'https://www.googleapis.com/auth/chat.messages.create';

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function count(value) {
  return Number.isSafeInteger(value) && value >= 0 && value <= MAX_COUNT ? value : 0;
}

function rowsFor(source, fields) {
  const safeSource = isRecord(source) ? source : {};
  return fields.map(([label, key]) => [label, count(safeSource[key])]);
}

function validRows(rows, fields) {
  return Array.isArray(rows) && rows.length === fields.length && rows.every((row, index) => (
    Array.isArray(row) && row.length === 2 && row[0] === fields[index][0]
    && Number.isSafeInteger(row[1]) && row[1] >= 0 && row[1] <= MAX_COUNT
  ));
}

function renderMessage(report) {
  return [
    'Devobs AI-7 — موجز مجمّع',
    `تاريخ الإنشاء UTC: ${report.createdAt}`,
    ...report.summaryRows.map(([label, value]) => `${label}: ${value}`),
    '',
    'أنواع الأحداث',
    ...report.eventRows.map(([label, value]) => `${label}: ${value}`),
    '',
    'شدة الأحداث',
    ...report.severityRows.map(([label, value]) => `${label}: ${value}`),
    '',
    'ملاحظة: هذه مجاميع من لقطة محلية؛ المؤشرات استرشادية وليست مراقبة حية.',
  ].join('\n');
}

function validDate(value) {
  if (typeof value !== 'string') return false;
  const date = new Date(value);
  return Number.isFinite(date.getTime()) && date.toISOString() === value;
}

function safeReport(report) {
  if (!isRecord(report) || !validDate(report.createdAt)
    || !validRows(report.summaryRows, SUMMARY_FIELDS)
    || !validRows(report.eventRows, EVENT_KINDS)
    || !validRows(report.severityRows, SEVERITIES)
    || typeof report.message !== 'string' || report.message !== renderMessage(report)) return false;
  return new TextEncoder().encode(report.message).byteLength <= MAX_MESSAGE_BYTES;
}

export function isValidGoogleChatSpaceName(value) {
  return typeof value === 'string' && /^spaces\/[A-Za-z0-9_-]{1,128}$/.test(value);
}

/** Build a fixed, allowlisted aggregate message; incident text and identifiers are ignored. */
export function buildGoogleChatReport(snapshot, createdAt = new Date()) {
  if (!isRecord(snapshot) || !isRecord(snapshot.summary) || !(createdAt instanceof Date)
    || !Number.isFinite(createdAt.getTime())) {
    throw new TypeError('invalid_google_chat_report_input');
  }
  const report = {
    createdAt: createdAt.toISOString(),
    summaryRows: rowsFor(snapshot.summary, SUMMARY_FIELDS),
    eventRows: rowsFor(snapshot.summary.kind_counts, EVENT_KINDS),
    severityRows: rowsFor(snapshot.summary.severity_counts, SEVERITIES),
  };
  report.message = renderMessage(report);
  if (!safeReport(report)) throw new TypeError('invalid_google_chat_report_input');
  return report;
}

function validAccessToken(value) {
  return typeof value === 'string' && value.length >= 16 && value.length <= 4096
    && !/[\s\x00-\x1f\x7f]/.test(value);
}

function validMessageName(value, spaceName) {
  const prefix = `${spaceName}/messages/`;
  if (typeof value !== 'string' || !value.startsWith(prefix)) return false;
  const messageId = value.slice(prefix.length);
  return /^[A-Za-z0-9._:-]{1,256}$/.test(messageId);
}

/** Send one user-approved text message to the supplied Chat space; never list/read spaces or messages. */
export async function sendGoogleChatSummary({ accessToken, spaceName, report, fetchImpl = fetch }) {
  if (!validAccessToken(accessToken) || !isValidGoogleChatSpaceName(spaceName)
    || !safeReport(report) || typeof fetchImpl !== 'function') {
    throw new TypeError('invalid_google_chat_request');
  }

  let response;
  try {
    response = await fetchImpl(`${CHAT_API_BASE}/${spaceName}/messages`, {
      method: 'POST',
      redirect: 'error',
      cache: 'no-store',
      credentials: 'omit',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: report.message }),
    });
  } catch {
    throw new Error('google_chat_send_failed');
  }
  if (!response || response.ok !== true) throw new Error('google_chat_send_failed');

  let created;
  try {
    created = await response.json();
  } catch {
    throw new Error('google_chat_invalid_response');
  }
  if (!isRecord(created) || !validMessageName(created.name, spaceName) || created.text !== report.message) {
    throw new Error('google_chat_invalid_response');
  }
  return { sent: true };
}
