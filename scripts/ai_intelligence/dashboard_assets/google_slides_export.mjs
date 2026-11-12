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
const SLIDES_API = 'https://slides.googleapis.com/v1/presentations';
const SLIDE_TITLES = Object.freeze([
  'ملخص تنفيذي — Devobs AI-7',
  'فئات الأحداث والشدة',
]);
const SUMMARY_NOTE = 'مجاميع من لقطة محلية؛ الإشارات استرشادية ولا تثبت حالة إنتاجية.';

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

/** Build a fixed two-slide executive report from allowlisted AI-7 counts only. */
export function buildGoogleSlidesReport(snapshot, createdAt = new Date()) {
  if (!isRecord(snapshot) || !isRecord(snapshot.summary) || !(createdAt instanceof Date)
    || !Number.isFinite(createdAt.getTime())) {
    throw new TypeError('invalid_google_slides_report_input');
  }
  return {
    title: `Devobs - AI-7 executive summary ${createdAt.toISOString().slice(0, 10)}`,
    createdAt: createdAt.toISOString(),
    summaryRows: rowsFor(snapshot.summary, SUMMARY_FIELDS),
    eventRows: rowsFor(snapshot.summary.kind_counts, EVENT_KINDS),
    severityRows: rowsFor(snapshot.summary.severity_counts, SEVERITIES),
  };
}

function validRows(rows, fields) {
  return Array.isArray(rows) && rows.length === fields.length && rows.every((row, index) => (
    Array.isArray(row) && row.length === 2 && row[0] === fields[index][0]
    && Number.isSafeInteger(row[1]) && row[1] >= 0 && row[1] <= MAX_COUNT
  ));
}

function safeReport(report) {
  if (!isRecord(report) || typeof report.createdAt !== 'string'
    || !Array.isArray(report.summaryRows) || !Array.isArray(report.eventRows)
    || !Array.isArray(report.severityRows)) return false;
  const titleDate = /^Devobs - AI-7 executive summary (\d{4}-\d{2}-\d{2})$/.exec(report.title)?.[1];
  const date = new Date(report.createdAt);
  return Boolean(titleDate && report.createdAt.startsWith(`${titleDate}T`)
    && Number.isFinite(date.getTime()) && date.toISOString() === report.createdAt
    && validRows(report.summaryRows, SUMMARY_FIELDS)
    && validRows(report.eventRows, EVENT_KINDS)
    && validRows(report.severityRows, SEVERITIES));
}

function dimensionToPoints(dimension) {
  if (!isRecord(dimension) || !Number.isFinite(dimension.magnitude) || dimension.magnitude <= 0) return null;
  const points = dimension.unit === 'PT'
    ? dimension.magnitude
    : dimension.unit === 'EMU' ? dimension.magnitude / 12_700 : null;
  return Number.isFinite(points) && points >= 100 && points <= 10_000 ? points : null;
}

function bodyText(rows) {
  return rows.map(([label, value]) => `${label}: ${value}`).join('\n');
}

function createTextBoxRequest(objectId, slideId, text, pageSize, position, fontSize, bold = false) {
  const x = pageSize.width * 0.06;
  const width = pageSize.width * 0.88;
  const y = pageSize.height * position.y;
  const height = pageSize.height * position.height;
  return [
    {
      createShape: {
        objectId,
        shapeType: 'TEXT_BOX',
        elementProperties: {
          pageObjectId: slideId,
          size: {
            width: { magnitude: width, unit: 'PT' },
            height: { magnitude: height, unit: 'PT' },
          },
          transform: { scaleX: 1, scaleY: 1, translateX: x, translateY: y, unit: 'PT' },
        },
      },
    },
    { insertText: { objectId, insertionIndex: 0, text } },
    {
      updateTextStyle: {
        objectId,
        textRange: { type: 'ALL' },
        style: { fontSize: { magnitude: fontSize, unit: 'PT' }, bold },
        fields: 'fontSize,bold',
      },
    },
  ];
}

function buildRequests(report, pageSize) {
  const summarySlideId = 'devobs_ai7_summary_slide';
  const secondSlideId = 'devobs_ai7_categories_slide';
  const summaryBody = [
    `تاريخ الإنشاء UTC: ${report.createdAt}`,
    '',
    ...bodyText(report.summaryRows).split('\n'),
    '',
    SUMMARY_NOTE,
  ].join('\n');
  const categoryBody = [
    'نوع الحدث',
    ...bodyText(report.eventRows).split('\n'),
    '',
    'شدة الحدث',
    ...bodyText(report.severityRows).split('\n'),
  ].join('\n');
  return [
    { createSlide: { objectId: summarySlideId, slideLayoutReference: { predefinedLayout: 'BLANK' } } },
    { createSlide: { objectId: secondSlideId, slideLayoutReference: { predefinedLayout: 'BLANK' } } },
    ...createTextBoxRequest('devobs_ai7_summary_title', summarySlideId, SLIDE_TITLES[0], pageSize, { y: 0.06, height: 0.12 }, 24, true),
    ...createTextBoxRequest('devobs_ai7_summary_body', summarySlideId, summaryBody, pageSize, { y: 0.22, height: 0.70 }, 14),
    ...createTextBoxRequest('devobs_ai7_categories_title', secondSlideId, SLIDE_TITLES[1], pageSize, { y: 0.06, height: 0.12 }, 24, true),
    ...createTextBoxRequest('devobs_ai7_categories_body', secondSlideId, categoryBody, pageSize, { y: 0.22, height: 0.70 }, 15),
  ];
}

function validAccessToken(value) {
  return typeof value === 'string' && value.length >= 16 && value.length <= 4096
    && !/[\s\x00-\x1f\x7f]/.test(value);
}

/** Create a new presentation and populate it with only fixed, validated aggregates. */
export async function createGoogleSlidesPresentation({ accessToken, report, fetchImpl = fetch }) {
  if (!validAccessToken(accessToken) || !safeReport(report) || typeof fetchImpl !== 'function') {
    throw new TypeError('invalid_google_slides_request');
  }
  const requestOptions = {
    redirect: 'error',
    credentials: 'omit',
    cache: 'no-store',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
  };

  let response;
  try {
    response = await fetchImpl(`${SLIDES_API}?fields=presentationId,pageSize(width,height)`, {
      ...requestOptions,
      method: 'POST',
      body: JSON.stringify({ title: report.title }),
    });
  } catch {
    throw new Error('google_slides_create_failed');
  }
  if (!response.ok) throw new Error('google_slides_create_failed');

  let created;
  try {
    created = await response.json();
  } catch {
    throw new Error('google_slides_invalid_response');
  }
  if (!isRecord(created) || typeof created.presentationId !== 'string'
    || !/^[A-Za-z0-9_-]{5,256}$/.test(created.presentationId)
    || !isRecord(created.pageSize)) {
    throw new Error('google_slides_invalid_response');
  }

  const pageWidth = dimensionToPoints(created.pageSize.width);
  const pageHeight = dimensionToPoints(created.pageSize.height);
  if (pageWidth === null || pageHeight === null) throw new Error('google_slides_invalid_response');
  const requests = buildRequests(report, { width: pageWidth, height: pageHeight });
  const presentationUrl = new URL(`${SLIDES_API}/${encodeURIComponent(created.presentationId)}:batchUpdate`);
  try {
    response = await fetchImpl(presentationUrl, {
      ...requestOptions,
      method: 'POST',
      body: JSON.stringify({ requests }),
    });
  } catch {
    throw new Error('google_slides_update_failed');
  }
  if (!response.ok) throw new Error('google_slides_update_failed');

  let updated;
  try {
    updated = await response.json();
  } catch {
    throw new Error('google_slides_invalid_response');
  }
  if (!isRecord(updated) || !Array.isArray(updated.replies) || updated.replies.length !== requests.length
    || !isRecord(updated.replies[0]) || !isRecord(updated.replies[0].createSlide)
    || updated.replies[0].createSlide.objectId !== 'devobs_ai7_summary_slide'
    || !isRecord(updated.replies[1]) || !isRecord(updated.replies[1].createSlide)
    || updated.replies[1].createSlide.objectId !== 'devobs_ai7_categories_slide') {
    throw new Error('google_slides_invalid_response');
  }
  for (let index = 1; index < requests.length; index++) {
    if (requests[index].createShape
      && updated.replies[index]?.createShape?.objectId !== requests[index].createShape.objectId) {
      throw new Error('google_slides_invalid_response');
    }
  }
  return { presentationId: created.presentationId };
}
