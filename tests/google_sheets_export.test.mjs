import assert from 'node:assert/strict';
import test from 'node:test';
import { buildGoogleSheetsReport, createGoogleSheet } from '../scripts/ai_intelligence/dashboard_assets/google_sheets_export.mjs';

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
  incidents: [{
    label: RAW_MARKER,
    hypotheses: [
      { cause_id: 'timeout', evidence_markers: [RAW_MARKER] },
      { cause_id: RAW_MARKER, evidence_markers: ['private'] },
    ],
  }],
  recommendations: [{ runbook_title: RAW_MARKER }],
};

test('Sheets report includes only fixed aggregate labels, counts, and creation date', () => {
  const report = buildGoogleSheetsReport(snapshot, createdAt);
  const serialized = JSON.stringify(report);

  assert.equal(report.title, 'Devobs - AI-7 aggregate summary 2026-11-12');
  assert.equal(report.rows[0][0], 'Devobs AI-7 ملخص إجمالي منقّح');
  assert.deepEqual(report.rows[1], ['تاريخ الإنشاء UTC', '2026-11-12T10:00:00.000Z']);
  assert.ok(report.rows.some(row => row[0] === 'الأحداث' && row[1] === 8));
  assert.ok(report.rows.some(row => row[0] === 'مهلة' && row[1] === 1));
  assert.equal(serialized.includes(RAW_MARKER), false);
  assert.equal(serialized.includes('private'), false);
  assert.equal(report.rows.length, 34);
});

test('Sheets report rejects invalid inputs and caps out-of-range counts', () => {
  const report = buildGoogleSheetsReport({ summary: { event_count: Number.MAX_SAFE_INTEGER } }, createdAt);
  assert.ok(report.rows.some(row => row[0] === 'الأحداث' && row[1] === 0));
  assert.throws(() => buildGoogleSheetsReport(null, createdAt), { message: 'invalid_google_sheets_report_input' });
  assert.throws(() => buildGoogleSheetsReport({ summary: {} }, 'not-a-date'), { message: 'invalid_google_sheets_report_input' });
});

test('Sheets client creates one new sheet and writes only its validated report using RAW values', async () => {
  const report = buildGoogleSheetsReport(snapshot, createdAt);
  const calls = [];
  const result = await createGoogleSheet({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async (url, options) => {
      calls.push({ url: String(url), options });
      return calls.length === 1
        ? { ok: true, json: async () => ({
          spreadsheetId: 'syntheticSheet_123',
          sheets: [{ properties: { title: 'AI-7 Summary' } }],
        }) }
        : { ok: true, json: async () => ({ updatedCells: report.rows.reduce((sum, row) => sum + row.length, 0) }) };
    },
  });

  assert.deepEqual(result, { spreadsheetId: 'syntheticSheet_123' });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, 'https://sheets.googleapis.com/v4/spreadsheets');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.credentials, 'omit');
  assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ya29.synthetic_access_token');
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    properties: { title: report.title },
    sheets: [{ properties: { title: 'AI-7 Summary', gridProperties: { rowCount: 34, columnCount: 2 } } }],
  });
  const writeUrl = new URL(calls[1].url);
  assert.equal(writeUrl.origin, 'https://sheets.googleapis.com');
  assert.equal(writeUrl.searchParams.get('valueInputOption'), 'RAW');
  assert.equal(calls[1].options.method, 'PUT');
  assert.equal(calls[1].options.headers.Authorization, 'Bearer ya29.synthetic_access_token');
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    range: "'AI-7 Summary'!A1:B34",
    majorDimension: 'ROWS',
    values: report.rows,
  });
  assert.equal(calls.some(call => call.url.includes('synthetic_access_token')), false);
  assert.equal(JSON.stringify(calls).includes(RAW_MARKER), false);
});

test('Sheets client rejects altered reports, failed writes, and unexpected provider responses', async () => {
  const report = buildGoogleSheetsReport(snapshot, createdAt);
  const altered = structuredClone(report);
  altered.rows[0][0] = RAW_MARKER;
  await assert.rejects(createGoogleSheet({ accessToken: 'ya29.synthetic_access_token', report: altered }), {
    message: 'invalid_google_sheets_request',
  });
  await assert.rejects(createGoogleSheet({ accessToken: '', report }), {
    message: 'invalid_google_sheets_request',
  });
  await assert.rejects(createGoogleSheet({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async () => ({ ok: false, status: 403, json: async () => ({ error: 'private provider detail' }) }),
  }), { message: 'google_sheets_create_failed' });
  await assert.rejects(createGoogleSheet({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async () => ({ ok: true, json: async () => ({ spreadsheetId: 'id' }) }),
  }), { message: 'google_sheets_invalid_response' });

  let calls = 0;
  await assert.rejects(createGoogleSheet({
    accessToken: 'ya29.synthetic_access_token',
    report,
    fetchImpl: async () => {
      calls++;
      return calls === 1
        ? { ok: true, json: async () => ({ spreadsheetId: 'syntheticSheet_123', sheets: [{ properties: { title: 'AI-7 Summary' } }] }) }
        : { ok: false, status: 403, json: async () => ({ error: 'private provider detail' }) };
    },
  }), { message: 'google_sheets_write_failed' });
});
