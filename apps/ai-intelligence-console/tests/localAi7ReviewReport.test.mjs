import test from 'node:test';
import assert from 'node:assert/strict';
import { buildLocalAi7ReviewReport } from '../src/utils/localAi7ReviewReport.ts';

const EXPORTED_AT = '2026-11-24T12:00:00.000Z';

function snapshot(overrides = {}) {
  return {
    source: 'local_ai7_snapshot',
    status: 'local_snapshot',
    mode: 'local_advisory_only',
    read_only: true,
    summary: {
      event_count: 24,
      log_cluster_count: 2,
      recommendation_count: 1,
      anomaly_candidate_count: 2,
    },
    stages: Array.from({ length: 7 }, (_, index) => ({
      id: `AI-${index + 1}`,
      status: 'ready',
      count: 1,
    })),
    recommendations: [{
      review_order: 1,
      cause_id: 'timeout',
      classification: 'POSSIBLE',
      heuristic_signal: 'medium',
      event_count: 3,
      evidence_markers: ['ETIMEDOUT'],
      requires_human_approval: true,
      automatic_execution: false,
    }],
    ...overrides,
  };
}

test('report contains only bounded aggregates and advisory fields', () => {
  const report = buildLocalAi7ReviewReport(snapshot(), EXPORTED_AT);
  assert.ok(report);
  assert.match(report, /2026-11-24T12:00:00\.000Z/);
  assert.match(report, /ليس وقت التقاط اللقطة/);
  assert.match(report, /POSSIBLE/);
  assert.match(report, /ETIMEDOUT/);
  assert.match(report, /يتطلب أي تغيير اعتمادًا بشريًا منفصلًا/);
  assert.match(report, /التنفيذ التلقائي: معطل/);
  assert.doesNotMatch(report, /raw event|source_sha|accessToken|PRIVATE/);
});

test('report limits detailed recommendations to the validated visible prefix', () => {
  const base = snapshot();
  const report = buildLocalAi7ReviewReport({
    ...base,
    summary: { ...base.summary, recommendation_count: 7 },
    recommendations: Array.from({ length: 5 }, (_, index) => ({
      ...base.recommendations[0],
      review_order: index + 1,
    })),
  }, EXPORTED_AT);
  assert.ok(report);
  assert.match(report, /5 من أصل 7/);
  assert.equal((report.match(/^### /gm) ?? []).length, 5);
});

test('report includes only the current local read acknowledgements and denies approval meaning', () => {
  const base = snapshot({
    summary: { event_count: 24, log_cluster_count: 2, recommendation_count: 2, anomaly_candidate_count: 2 },
    recommendations: [
      snapshot().recommendations[0],
      { ...snapshot().recommendations[0], review_order: 2, cause_id: 'dns', evidence_markers: ['ENOTFOUND'] },
    ],
  });
  const report = buildLocalAi7ReviewReport(base, EXPORTED_AT, [1]);

  assert.ok(report);
  assert.deepEqual(report.split('\n').filter(line => line.startsWith('- إقرار الاطلاع المحلي عند التصدير: ')), [
    '- إقرار الاطلاع المحلي عند التصدير: محدد في الواجهة',
    '- إقرار الاطلاع المحلي عند التصدير: غير محدد في الواجهة',
  ]);
  assert.match(report, /لا تسجل هوية المراجع ولا تعد موافقة أو اعتمادًا أو تفويضًا/);
});

test('empty recommendation set is reported without claiming the system is healthy', () => {
  const base = snapshot();
  const report = buildLocalAi7ReviewReport({
    ...base,
    summary: { ...base.summary, recommendation_count: 0 },
    recommendations: [],
  }, EXPORTED_AT);
  assert.ok(report);
  assert.match(report, /لا توجد توصيات معروفة/);
  assert.match(report, /لا يثبت خلو النظام من الأعطال/);
});

test('invalid snapshots and non-canonical timestamps cannot produce a report', () => {
  assert.equal(buildLocalAi7ReviewReport({ ...snapshot(), recommendations: [{
    ...snapshot().recommendations[0],
    runbook_text: 'UNTRUSTED_CONTENT',
  }] }, EXPORTED_AT), null);
  assert.equal(buildLocalAi7ReviewReport(snapshot(), 'yesterday'), null);
  assert.equal(buildLocalAi7ReviewReport(snapshot(), '2026-02-30T12:00:00.000Z'), null);
});

test('invalid local acknowledgements cannot produce a report', () => {
  for (const invalid of [[2], [1, 1], ['1'], {}, null]) {
    assert.equal(buildLocalAi7ReviewReport(snapshot(), EXPORTED_AT, invalid), null);
  }
});
