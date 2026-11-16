import assert from 'node:assert/strict';
import test from 'node:test';
import { buildGoogleDocsReport, createGoogleDoc } from '../scripts/ai_intelligence/dashboard_assets/google_docs_export.mjs';
import * as reports from '../scripts/ai_intelligence/dashboard_assets/google_docs_export.mjs';
import { buildDashboardSnapshot } from '../scripts/ai_intelligence/dashboard_server.mjs';
import { parseEventLines } from '../scripts/ai_intelligence/event_schema.mjs';

const RAW_MARKER = 'CUSTOMER_RAW_LOG_MUST_NOT_LEAVE_LOCAL_DASHBOARD';
const createdAt = new Date('2026-11-12T10:00:00.000Z');

function localSnapshot() {
  return buildDashboardSnapshot(parseEventLines(JSON.stringify({ schema_version: 1,
    occurred_at: '2026-11-12T09:00:00Z', source: 'application', kind: 'log', severity: 'error',
    data: { stream: 'application', message: 'request timed out' } })).events);
}
function localReport(snapshot = localSnapshot(), mode = 'synthetic_fixed', time = createdAt) {
  assert.equal(typeof reports.buildLocalTextReport, 'function', 'Local TXT report must be implemented');
  return reports.buildLocalTextReport(snapshot, { mode, createdAt: time });
}

test('offline report labels its sample or startup snapshot and generation time honestly', () => {
  const synthetic = localReport();
  assert.equal(synthetic.filename, 'devobs-synthetic-report-2026-11-12.txt');
  assert.match(synthetic.text, /عينة اصطناعية ثابتة/);
  assert.match(synthetic.text, /وقت إنشاء الملف: 2026-11-12T10:00:00.000Z/);
  assert.match(synthetic.text, /الأحداث: 1/);
  assert.match(synthetic.text, /مهلة: 1/);
  const local = localReport(localSnapshot(), 'local_snapshot');
  assert.equal(local.filename, 'devobs-local-report-2026-11-12.txt');
  assert.match(local.text, /لقطة محلية عند بدء الخادم/);
  assert.doesNotMatch(local.text, /عينة اصطناعية ثابتة|البيانات المرسلة/);
  assert.deepEqual(localReport(), synthetic);
});

test('offline report excludes notes, raw text and identifiers while retaining known aggregates', () => {
  const snapshot = localSnapshot();
  snapshot.summary.raw_log = RAW_MARKER;
  snapshot.incidents[0].label = RAW_MARKER;
  snapshot.incidents[0].hypotheses[0].evidence_markers = [RAW_MARKER];
  snapshot.recommendations = [{ runbook_title: RAW_MARKER }];
  snapshot.notes = [{ content: RAW_MARKER }];
  const report = localReport(snapshot);
  assert.doesNotMatch(report.text + report.filename, new RegExp(RAW_MARKER + '|tenant_id|server_id'));
  assert.match(report.text, /مهلة: 1/);
});

test('offline report rejects malformed printed counts rather than replacing them with zero', () => {
  for (const value of [undefined, null, '1', -1, 0.5, NaN, Infinity, 1_000_001]) {
    const snapshot = localSnapshot(); snapshot.summary.event_count = value;
    assert.throws(() => localReport(snapshot), { message: 'invalid_local_text_report_input' });
  }
  for (const key of ['log_event_count', 'log_cluster_count', 'recommendation_count', 'anomaly_candidate_count', 'forecast_count']) {
    const snapshot = localSnapshot(); delete snapshot.summary[key];
    assert.throws(() => localReport(snapshot), { message: 'invalid_local_text_report_input' });
  }
});

test('offline report refuses inconsistent totals, incomplete counters and truncated causes', () => {
  for (const mutate of [s => s.summary.kind_counts.log = 0, s => s.summary.severity_counts.error = 0,
    s => delete s.summary.kind_counts.ci_result, s => delete s.summary.severity_counts.debug,
    s => s.summary.log_event_count = 0, s => s.summary.log_cluster_count = 0,
    s => s.incidents = new Array(101).fill(s.incidents[0]),
    s => s.incidents[0].hypotheses.push({ cause_id: 'unsupported' }),
    s => s.incidents[0].hypotheses.push(s.incidents[0].hypotheses[0]),
    s => s.incidents[0].hypotheses[0].cause_id = ['timeout'],
    s => s.incidents[0].hypotheses[0].cause_id = { toString: 'timeout' },
    s => s.incidents[0].hypotheses = null]) {
    const snapshot = localSnapshot(); mutate(snapshot);
    assert.throws(() => localReport(snapshot), { message: 'invalid_local_text_report_input' });
  }
  assert.match(localReport(buildDashboardSnapshot([])).text, /الأحداث: 0/);
});

test('offline report rejects unknown modes and invalid timestamps without consulting providers', () => {
  for (const [snapshot, mode, time] of [[null, 'local_snapshot', createdAt],
    [localSnapshot(), 'live', createdAt], [localSnapshot(), ['synthetic_fixed'], createdAt],
    [localSnapshot(), { toString: 'local_snapshot' }, createdAt],
    [localSnapshot(), 'synthetic_fixed', new Date(NaN)],
    [localSnapshot(), 'local_snapshot', '2026-11-12']]) {
    assert.throws(() => localReport(snapshot, mode, time), { message: 'invalid_local_text_report_input' });
  }
});

test('Docs report includes bounded aggregates and excludes free text and identifiers', () => {
  const report = buildGoogleDocsReport({
    summary: {
      event_count: 8,
      log_event_count: 5,
      log_cluster_count: 2,
      recommendation_count: 1,
      anomaly_candidate_count: 1,
      forecast_count: 0,
      kind_counts: { log: 5, incident: 1, ci_result: 1, server_metric: 1, [RAW_MARKER]: 77 },
      severity_counts: { error: 2, warning: 3, info: 3, [RAW_MARKER]: 91 },
      raw_log: RAW_MARKER,
      tenant_id: RAW_MARKER,
    },
    incidents: [{
      label: RAW_MARKER,
      event_count: 5,
      hypotheses: [
        { cause_id: 'timeout', evidence_markers: [RAW_MARKER] },
        { cause_id: RAW_MARKER, evidence_markers: ['private'] },
      ],
    }],
    recommendations: [{ runbook_title: RAW_MARKER, read_only_checks: [RAW_MARKER] }],
  }, createdAt);

  assert.equal(report.title, 'Devobs - ملخص تشغيلي 2026-11-12');
  assert.match(report.text, /الأحداث: 8/);
  assert.match(report.text, /مهلة: 1/);
  assert.doesNotMatch(`${report.title}\n${report.text}`, /CUSTOMER_RAW_LOG_MUST_NOT_LEAVE_LOCAL_DASHBOARD|tenant_id|private/);
});

test('Docs report rejects invalid snapshot/time inputs and caps unreasonable counts', () => {
  const report = buildGoogleDocsReport({ summary: { event_count: Number.MAX_SAFE_INTEGER } }, createdAt);
  assert.match(report.text, /الأحداث: 0/);
  assert.throws(() => buildGoogleDocsReport(null, createdAt), { message: 'invalid_google_docs_report_input' });
  assert.throws(() => buildGoogleDocsReport({ summary: {} }, 'not-a-date'), { message: 'invalid_google_docs_report_input' });
});

test('Google Docs client creates one new document and writes only the supplied report', async () => {
  const calls = [];
  const result = await createGoogleDoc({
    accessToken: 'ya29.synthetic_access_token',
    title: 'Devobs - synthetic report',
    text: 'Synthetic-only report',
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return calls.length === 1
        ? { ok: true, json: async () => ({ documentId: 'syntheticDoc_123' }) }
        : { ok: true };
    },
  });

  assert.deepEqual(result, { documentId: 'syntheticDoc_123' });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, 'https://docs.googleapis.com/v1/documents');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ya29.synthetic_access_token');
  assert.equal(calls[0].options.body, JSON.stringify({ title: 'Devobs - synthetic report' }));
  assert.equal(calls[1].url, 'https://docs.googleapis.com/v1/documents/syntheticDoc_123:batchUpdate');
  assert.equal(calls[1].options.headers.Authorization, 'Bearer ya29.synthetic_access_token');
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    requests: [{ insertText: { location: { index: 1 }, text: 'Synthetic-only report' } }],
  });
  assert.equal(calls.some(call => call.url.includes('synthetic_access_token')), false);
});

test('Google Docs client rejects invalid input and hides provider response details', async () => {
  await assert.rejects(createGoogleDoc({ accessToken: '', title: 'x', text: 'y' }), {
    message: 'invalid_google_docs_request',
  });
  await assert.rejects(createGoogleDoc({
    accessToken: 'ya29.synthetic_access_token',
    title: 'x',
    text: 'y',
    fetchImpl: async () => ({ ok: false, status: 403, json: async () => ({ error: 'private provider detail' }) }),
  }), { message: 'google_docs_create_failed' });
});
