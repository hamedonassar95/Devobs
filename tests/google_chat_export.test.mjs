import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildGoogleChatReport,
  GOOGLE_CHAT_SCOPE,
  isValidGoogleChatSpaceName,
  sendGoogleChatSummary,
} from '../scripts/ai_intelligence/dashboard_assets/google_chat_export.mjs';

const RAW_MARKER = 'PRIVATE_INCIDENT_TEXT_MUST_NOT_LEAVE_LOCAL_DASHBOARD';
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
    kind_counts: { log: 5, incident: 1, ci_result: 1, server_metric: 1, [RAW_MARKER]: 31 },
    severity_counts: { error: 2, warning: 3, info: 3, [RAW_MARKER]: 91 },
    tenant_id: RAW_MARKER,
  },
  incidents: [{ message: RAW_MARKER, event_id: RAW_MARKER }],
  recommendations: [{ runbook_title: RAW_MARKER }],
};

test('Chat summary contains only fixed labels, aggregate counts, and timestamp', () => {
  const report = buildGoogleChatReport(snapshot, createdAt);
  assert.equal(report.createdAt, '2026-11-12T10:00:00.000Z');
  assert.match(report.message, /الأحداث: 8/);
  assert.match(report.message, /نتائج CI: 1/);
  assert.match(report.message, /شدة الأحداث/);
  assert.match(report.message, /ملاحظة: هذه مجاميع من لقطة محلية/);
  assert.equal(report.message.includes(RAW_MARKER), false);
  assert.equal(new TextEncoder().encode(report.message).byteLength <= 32_000, true);
  assert.equal(GOOGLE_CHAT_SCOPE, 'https://www.googleapis.com/auth/chat.messages.create');
});

test('Chat destination validation accepts only a resource name supplied as spaces/id', () => {
  assert.equal(isValidGoogleChatSpaceName('spaces/AAAA_BBBB-123'), true);
  for (const candidate of ['', 'AAAA', '/spaces/AAA', 'spaces/a/messages/b', 'spaces/../../users/me', 'spaces/with space']) {
    assert.equal(isValidGoogleChatSpaceName(candidate), false, candidate);
  }
});

test('Chat client sends one text-only request to the chosen space without listing or reading', async () => {
  const report = buildGoogleChatReport(snapshot, createdAt);
  const calls = [];
  const result = await sendGoogleChatSummary({
    accessToken: 'ya29.synthetic_access_token',
    spaceName: 'spaces/AAAA_BBBB-123',
    report,
    fetchImpl: async (url, options) => {
      calls.push({ url: String(url), options });
      return {
        ok: true,
        json: async () => ({ name: 'spaces/AAAA_BBBB-123/messages/message-123', text: report.message }),
      };
    },
  });
  assert.deepEqual(result, { sent: true });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://chat.googleapis.com/v1/spaces/AAAA_BBBB-123/messages');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[0].options.credentials, 'omit');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ya29.synthetic_access_token');
  assert.deepEqual(JSON.parse(calls[0].options.body), { text: report.message });
  assert.equal(JSON.stringify(calls.map(({ url, options }) => ({ url, body: options.body }))).includes(RAW_MARKER), false);
  assert.equal(JSON.stringify(calls.map(({ url, options }) => ({ url, body: options.body }))).includes('synthetic_access_token'), false);
});

test('Chat client rejects altered reports, other destinations, provider errors, and uncertain responses', async () => {
  const report = buildGoogleChatReport(snapshot, createdAt);
  const altered = structuredClone(report);
  altered.message += `\n${RAW_MARKER}`;
  await assert.rejects(sendGoogleChatSummary({
    accessToken: 'ya29.synthetic_access_token', spaceName: 'spaces/AAAA_BBBB-123', report: altered,
  }), { message: 'invalid_google_chat_request' });
  await assert.rejects(sendGoogleChatSummary({
    accessToken: 'ya29.synthetic_access_token', spaceName: 'spaces/../../users/me', report,
  }), { message: 'invalid_google_chat_request' });
  await assert.rejects(sendGoogleChatSummary({
    accessToken: '', spaceName: 'spaces/AAAA_BBBB-123', report,
  }), { message: 'invalid_google_chat_request' });
  await assert.rejects(sendGoogleChatSummary({
    accessToken: 'ya29.synthetic_access_token',
    spaceName: 'spaces/AAAA_BBBB-123',
    report,
    fetchImpl: async () => ({ ok: false, json: async () => ({ error: 'private provider response' }) }),
  }), { message: 'google_chat_send_failed' });
  await assert.rejects(sendGoogleChatSummary({
    accessToken: 'ya29.synthetic_access_token',
    spaceName: 'spaces/AAAA_BBBB-123',
    report,
    fetchImpl: async () => ({ ok: true, json: async () => ({ name: 'spaces/OTHER/messages/id', text: report.message }) }),
  }), { message: 'google_chat_invalid_response' });
  await assert.rejects(sendGoogleChatSummary({
    accessToken: 'ya29.synthetic_access_token',
    spaceName: 'spaces/AAAA_BBBB-123',
    report,
    fetchImpl: async () => ({ ok: true, json: async () => ({ name: 'spaces/AAAA_BBBB-123/messages/id', text: RAW_MARKER }) }),
  }), { message: 'google_chat_invalid_response' });
});
