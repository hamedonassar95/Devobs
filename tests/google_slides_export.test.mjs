import assert from 'node:assert/strict';
import test from 'node:test';
import { buildGoogleSlidesReport, createGoogleSlidesPresentation } from '../scripts/ai_intelligence/dashboard_assets/google_slides_export.mjs';

const RAW_MARKER = 'CUSTOMER_RAW_LOG_MUST_NOT_LEAVE_LOCAL_DASHBOARD';
const createdAt = new Date('2026-11-12T10:00:00.000Z');
const snapshot = {
  summary: {
    event_count: 8,
    log_event_count: 5,
    ci_event_count: 1,
    log_cluster_count: 2,
    unknown_group_count: 1,
    recommendation_count: 1,
    metric_series_count: 2,
    anomaly_candidate_count: 1,
    forecast_count: 0,
    trend_range_warning_count: 0,
    feedback_ranked_recommendation_count: 1,
    kind_counts: { log: 5, incident: 1, ci_result: 1, server_metric: 1, [RAW_MARKER]: 77 },
    severity_counts: { error: 2, warning: 3, info: 3, [RAW_MARKER]: 91 },
    raw_log: RAW_MARKER,
    tenant_id: RAW_MARKER,
  },
  incidents: [{ message: RAW_MARKER, event_id: RAW_MARKER }],
  recommendations: [{ runbook_title: RAW_MARKER }],
};

function presentationResponse() {
  return {
    presentationId: 'syntheticPresentation_123',
    pageSize: {
      width: { magnitude: 9_144_000, unit: 'EMU' },
      height: { magnitude: 5_143_500, unit: 'EMU' },
    },
  };
}

test('Slides report contains only allowlisted aggregate counts, labels, and creation time', () => {
  const report = buildGoogleSlidesReport(snapshot, createdAt);
  const serialized = JSON.stringify(report);
  assert.equal(report.title, 'Devobs - AI-7 executive summary 2026-11-12');
  assert.equal(report.createdAt, '2026-11-12T10:00:00.000Z');
  assert.deepEqual(report.summaryRows.find(row => row[0] === 'الأحداث'), ['الأحداث', 8]);
  assert.deepEqual(report.eventRows.find(row => row[0] === 'سجلات'), ['سجلات', 5]);
  assert.deepEqual(report.severityRows.find(row => row[0] === 'خطأ'), ['خطأ', 2]);
  assert.equal(serialized.includes(RAW_MARKER), false);
  assert.equal(report.summaryRows.length, 11);
  assert.equal(report.eventRows.length, 4);
  assert.equal(report.severityRows.length, 6);
});

test('Slides report rejects invalid inputs and normalizes unsafe counters to zero', () => {
  const report = buildGoogleSlidesReport({ summary: { event_count: Number.MAX_SAFE_INTEGER } }, createdAt);
  assert.deepEqual(report.summaryRows[0], ['الأحداث', 0]);
  assert.throws(() => buildGoogleSlidesReport(null, createdAt), { message: 'invalid_google_slides_report_input' });
  assert.throws(() => buildGoogleSlidesReport({ summary: {} }, 'not-a-date'), { message: 'invalid_google_slides_report_input' });
});

test('Slides client creates a new two-slide aggregate deck without reading Drive', async () => {
  const report = buildGoogleSlidesReport(snapshot, createdAt);
  const calls = [];
  const result = await createGoogleSlidesPresentation({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async (url, options) => {
      calls.push({ url: String(url), options });
      if (calls.length === 1) return { ok: true, json: async () => presentationResponse() };
      const { requests } = JSON.parse(options.body);
      const replies = requests.map(request => request.createSlide
        ? { createSlide: { objectId: request.createSlide.objectId } }
        : request.createShape ? { createShape: { objectId: request.createShape.objectId } } : {});
      return { ok: true, json: async () => ({ replies }) };
    },
  });

  assert.deepEqual(result, { presentationId: 'syntheticPresentation_123' });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, 'https://slides.googleapis.com/v1/presentations?fields=presentationId,pageSize(width,height)');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.credentials, 'omit');
  assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ya29.synthetic_access_token');
  assert.deepEqual(JSON.parse(calls[0].options.body), { title: report.title });

  const updateUrl = new URL(calls[1].url);
  assert.equal(updateUrl.origin, 'https://slides.googleapis.com');
  assert.equal(updateUrl.pathname, '/v1/presentations/syntheticPresentation_123:batchUpdate');
  assert.equal(calls[1].options.method, 'POST');
  const updateBody = JSON.parse(calls[1].options.body);
  assert.equal(updateBody.requests[0].createSlide.objectId, 'devobs_ai7_summary_slide');
  assert.equal(updateBody.requests[1].createSlide.objectId, 'devobs_ai7_categories_slide');
  const summaryTitleShape = updateBody.requests.find(request => request.createShape?.objectId === 'devobs_ai7_summary_title').createShape;
  assert.equal(summaryTitleShape.elementProperties.pageObjectId, 'devobs_ai7_summary_slide');
  assert.ok(Math.abs(summaryTitleShape.elementProperties.size.width.magnitude - 633.6) < 0.001);
  assert.equal(summaryTitleShape.elementProperties.size.width.unit, 'PT');
  const insertedText = updateBody.requests.filter(request => request.insertText).map(request => request.insertText.text).join('\n');
  assert.match(insertedText, /تاريخ الإنشاء UTC: 2026-11-12T10:00:00.000Z/);
  assert.match(insertedText, /الأحداث: 8/);
  assert.match(insertedText, /نتائج CI: 1/);
  assert.match(insertedText, /نوع الحدث/);
  assert.match(insertedText, /شدة الحدث/);
  assert.equal(insertedText.includes(RAW_MARKER), false);
  assert.equal(JSON.stringify(calls.map(({ url, options }) => ({ url, body: options.body }))).includes('synthetic_access_token'), false);
});

test('Slides client rejects altered reports, provider failures, and incomplete replies', async () => {
  const report = buildGoogleSlidesReport(snapshot, createdAt);
  const altered = structuredClone(report);
  altered.eventRows[0][0] = RAW_MARKER;
  await assert.rejects(createGoogleSlidesPresentation({ accessToken: 'ya29.synthetic_access_token', report: altered }), {
    message: 'invalid_google_slides_request',
  });
  await assert.rejects(createGoogleSlidesPresentation({ accessToken: '', report }), {
    message: 'invalid_google_slides_request',
  });
  await assert.rejects(createGoogleSlidesPresentation({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async () => ({ ok: false, json: async () => ({ error: 'private provider detail' }) }),
  }), { message: 'google_slides_create_failed' });
  await assert.rejects(createGoogleSlidesPresentation({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async () => ({ ok: true, json: async () => ({ presentationId: 'id' }) }),
  }), { message: 'google_slides_invalid_response' });
  await assert.rejects(createGoogleSlidesPresentation({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async (url) => String(url).includes(':batchUpdate')
      ? { ok: true, json: async () => ({ replies: [] }) }
      : { ok: true, json: async () => presentationResponse() },
  }), { message: 'google_slides_invalid_response' });
});
