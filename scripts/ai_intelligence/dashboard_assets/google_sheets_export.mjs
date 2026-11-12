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
const CAUSES = Object.freeze([
  ['مهلة', 'timeout'],
  ['اتصال', 'connection'],
  ['DNS', 'dns'],
  ['صلاحية', 'permission'],
  ['اعتماد', 'dependency'],
  ['ذاكرة', 'memory'],
]);
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
const SHEET_TITLE = 'AI-7 Summary';
const REPORT_TITLE = 'Devobs AI-7 ملخص إجمالي منقّح';
const REPORT_NOTICE = 'أعداد وفئات عامة فقط؛ لا تتضمن نصوص سجلات أو أسماء عملاء أو معرّفات مشاريع أو خوادم.';
const MAX_COUNT = 1_000_000;

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function count(value) {
  return Number.isSafeInteger(value) && value >= 0 && value <= MAX_COUNT ? value : 0;
}

function countsFor(source, fields) {
  const safeSource = isRecord(source) ? source : {};
  return fields.map(([label, key]) => [label, count(safeSource[key])]);
}

function causeCountsFor(incidents) {
  const counts = Object.fromEntries(CAUSES.map(([, id]) => [id, 0]));
  if (!Array.isArray(incidents)) return CAUSES.map(([label, id]) => [label, counts[id]]);
  for (const incident of incidents.slice(0, 100)) {
    if (!isRecord(incident) || !Array.isArray(incident.hypotheses)) continue;
    for (const hypothesis of incident.hypotheses) {
      if (!isRecord(hypothesis) || !Object.hasOwn(counts, hypothesis.cause_id)) continue;
      counts[hypothesis.cause_id] = Math.min(MAX_COUNT, counts[hypothesis.cause_id] + 1);
    }
  }
  return CAUSES.map(([label, id]) => [label, counts[id]]);
}

/** Build a fixed two-column aggregate report. No free text or identifiers are copied. */
export function buildGoogleSheetsReport(snapshot, createdAt = new Date()) {
  if (!isRecord(snapshot) || !isRecord(snapshot.summary) || !(createdAt instanceof Date)
    || !Number.isFinite(createdAt.getTime())) {
    throw new TypeError('invalid_google_sheets_report_input');
  }
  const summary = snapshot.summary;
  const rows = [
    [REPORT_TITLE],
    ['تاريخ الإنشاء UTC', createdAt.toISOString()],
    [REPORT_NOTICE],
    ['المؤشر', 'العدد'],
    ...countsFor(summary, SUMMARY_FIELDS),
    ['نوع الحدث', 'العدد'],
    ...countsFor(summary.kind_counts, EVENT_KINDS),
    ['شدة الحدث', 'العدد'],
    ...countsFor(summary.severity_counts, SEVERITIES),
    ['الفئة الاسترشادية', 'عدد الإشارات'],
    ...causeCountsFor(snapshot.incidents),
  ];
  return {
    title: `Devobs - AI-7 aggregate summary ${createdAt.toISOString().slice(0, 10)}`,
    rows,
  };
}

function validAccessToken(value) {
  return typeof value === 'string' && value.length >= 16 && value.length <= 4096
    && !/[\s\x00-\x1f\x7f]/.test(value);
}

function safeReport(report) {
  if (!isRecord(report) || typeof report.title !== 'string' || !Array.isArray(report.rows)) return false;
  const titleDate = /^Devobs - AI-7 aggregate summary (\d{4}-\d{2}-\d{2})$/.exec(report.title)?.[1];
  if (!titleDate || !Array.isArray(report.rows) || report.rows.length !== 34) return false;
  const rows = report.rows;
  if (JSON.stringify(rows[0]) !== JSON.stringify([REPORT_TITLE])
    || JSON.stringify(rows[2]) !== JSON.stringify([REPORT_NOTICE])) return false;
  const timestamp = rows[1];
  if (!Array.isArray(timestamp) || timestamp.length !== 2 || timestamp[0] !== 'تاريخ الإنشاء UTC'
    || typeof timestamp[1] !== 'string' || !timestamp[1].startsWith(`${titleDate}T`)) return false;
  const parsedDate = new Date(timestamp[1]);
  if (!Number.isFinite(parsedDate.getTime()) || parsedDate.toISOString() !== timestamp[1]) return false;
  let offset = 3;
  const sections = [
    ['المؤشر', SUMMARY_FIELDS],
    ['نوع الحدث', EVENT_KINDS],
    ['شدة الحدث', SEVERITIES],
    ['الفئة الاسترشادية', CAUSES],
  ];
  for (const [heading, fields] of sections) {
    if (JSON.stringify(rows[offset]) !== JSON.stringify([heading, heading === 'الفئة الاسترشادية' ? 'عدد الإشارات' : 'العدد'])) return false;
    offset++;
    for (const [label] of fields) {
      const row = rows[offset++];
      if (!Array.isArray(row) || row.length !== 2 || row[0] !== label
        || !Number.isSafeInteger(row[1]) || row[1] < 0 || row[1] > MAX_COUNT) return false;
    }
  }
  return offset === rows.length;
}

/** Create a new spreadsheet and write only a validated allowlisted aggregate report. */
export async function createGoogleSheet({ accessToken, report, fetchImpl = fetch }) {
  if (!validAccessToken(accessToken) || !safeReport(report) || typeof fetchImpl !== 'function') {
    throw new TypeError('invalid_google_sheets_request');
  }

  const requestOptions = {
    redirect: 'error',
    credentials: 'omit',
    cache: 'no-store',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
  };
  let response;
  try {
    response = await fetchImpl('https://sheets.googleapis.com/v4/spreadsheets', {
      ...requestOptions,
      method: 'POST',
      body: JSON.stringify({
        properties: { title: report.title },
        sheets: [{ properties: { title: SHEET_TITLE, gridProperties: { rowCount: report.rows.length, columnCount: 2 } } }],
      }),
    });
  } catch {
    throw new Error('google_sheets_create_failed');
  }
  if (!response.ok) throw new Error('google_sheets_create_failed');

  let created;
  try {
    created = await response.json();
  } catch {
    throw new Error('google_sheets_invalid_response');
  }
  if (!isRecord(created) || typeof created.spreadsheetId !== 'string'
    || !/^[A-Za-z0-9_-]{5,256}$/.test(created.spreadsheetId)
    || !Array.isArray(created.sheets) || created.sheets.length !== 1
    || !isRecord(created.sheets[0]) || !isRecord(created.sheets[0].properties)
    || created.sheets[0].properties.title !== SHEET_TITLE) {
    throw new Error('google_sheets_invalid_response');
  }

  const range = `'${SHEET_TITLE}'!A1:B${report.rows.length}`;
  const valuesUrl = new URL(
    `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(created.spreadsheetId)}/values/${encodeURIComponent(range)}:update`,
  );
  valuesUrl.searchParams.set('valueInputOption', 'RAW');
  try {
    response = await fetchImpl(valuesUrl, {
      ...requestOptions,
      method: 'PUT',
      body: JSON.stringify({ range, majorDimension: 'ROWS', values: report.rows }),
    });
  } catch {
    throw new Error('google_sheets_write_failed');
  }
  if (!response.ok) throw new Error('google_sheets_write_failed');

  let updated;
  try {
    updated = await response.json();
  } catch {
    throw new Error('google_sheets_invalid_response');
  }
  const expectedCells = report.rows.reduce((total, row) => total + row.length, 0);
  if (!isRecord(updated) || !Number.isSafeInteger(updated.updatedCells) || updated.updatedCells !== expectedCells) {
    throw new Error('google_sheets_invalid_response');
  }
  return { spreadsheetId: created.spreadsheetId };
}
