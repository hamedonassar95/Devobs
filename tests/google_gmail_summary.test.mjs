import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildGoogleGmailReport, GOOGLE_GMAIL_SCOPE, isValidGoogleGmailAddress, sendGoogleGmailSummary,
} from '../scripts/ai_intelligence/dashboard_assets/google_gmail_summary.mjs';

const PRIVATE_MARKER = 'PRIVATE_INCIDENT_TEXT_MUST_NOT_LEAVE_LOCAL_DASHBOARD';
const createdAt = new Date('2026-11-12T10:00:00.000Z');
const snapshot = {
  summary: {
    event_count: 8, ci_event_count: 1, tenant_id: PRIVATE_MARKER,
    kind_counts: { log: 5, incident: 1, ci_result: 1, server_metric: 1, [PRIVATE_MARKER]: 9 },
    severity_counts: { error: 2, warning: 3, info: 3, [PRIVATE_MARKER]: 4 },
  },
  incidents: [{ message: PRIVATE_MARKER, event_id: PRIVATE_MARKER }],
  recommendations: [{ runbook_title: PRIVATE_MARKER }],
};
const defaults = { accessToken: 'ya29.synthetic_access_token', snapshot, recipient: 'team@example.com', createdAt };
const send = overrides => sendGoogleGmailSummary({ ...defaults, ...overrides });
const decode = value => new TextDecoder().decode(Uint8Array.from(atob(value), char => char.charCodeAt(0)));
const decodeRaw = raw => decode(raw.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - raw.length % 4) % 4));
const decodeBody = mime => decode(mime.split('\r\n\r\n').at(-1).replaceAll('\r\n', ''));

test('recipient validation rejects header injection and multiple targets', () => {
  assert.equal(isValidGoogleGmailAddress('ops+alerts@example.co.uk'), true);
  for (const value of ['', ' team@example.com', 'team@example.com,other@example.com',
    'team@example.com\r\nBcc:x@y.z', 'team@localhost', 'a..b@example.com', 'team@-example.com']) {
    assert.equal(isValidGoogleGmailAddress(value), false, value);
  }
});

test('preview includes fixed aggregates only and rejects invalid input', () => {
  const report = buildGoogleGmailReport(snapshot, 'team@example.com', createdAt);
  assert.equal(report.createdAt, '2026-11-12T10:00:00.000Z');
  assert.equal(report.subject, 'Devobs AI-7 aggregate summary 2026-11-12');
  assert.match(report.body, /الأحداث: 8/);
  assert.match(report.body, /نتائج CI: 1/);
  assert.equal(report.body.includes(PRIVATE_MARKER), false);
  assert.equal(GOOGLE_GMAIL_SCOPE, 'https://www.googleapis.com/auth/gmail.send');
  assert.throws(() => buildGoogleGmailReport(snapshot, 'a@b.com\nBcc:x@y.z', createdAt), {
    message: 'invalid_google_gmail_report_input',
  });
  assert.throws(() => buildGoogleGmailReport(snapshot, 'team@example.com', new Date('invalid')), {
    message: 'invalid_google_gmail_report_input',
  });
});

test('client sends one MIME report to Gmail without redirects or browser credentials', async () => {
  const calls = [];
  assert.deepEqual(await send({ fetchImpl: async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ id: 'message-123', threadId: 'thread-123' }) };
  } }), { sent: true });
  assert.equal(calls.length, 1); assert.equal(calls[0].url, 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[0].options.credentials, 'omit');
  assert.equal(calls[0].options.headers.Authorization, `Bearer ${defaults.accessToken}`);
  const raw = JSON.parse(calls[0].options.body).raw;
  const mime = decodeRaw(raw);
  assert.match(mime, /^To: team@example\.com\r\nSubject: Devobs AI-7 aggregate summary 2026-11-12/m);
  assert.match(mime, /Content-Type: text\/plain; charset=UTF-8/);
  assert.match(decodeBody(mime), /الأحداث: 8/);
  assert.equal(mime.includes(PRIVATE_MARKER), false);
  assert.equal(calls[0].options.body.includes(defaults.accessToken), false);
});

test('client fails closed on invalid input, provider errors, malformed response and transport failure', async () => {
  const errors = [
    [send({ accessToken: '' }), 'invalid_google_gmail_request'],
    [send({ recipient: 'bad@example.com\nBcc:x@y.z' }), 'invalid_google_gmail_report_input'],
    [send({ fetchImpl: async () => ({ ok: false }) }), 'google_gmail_send_failed'],
    [send({ fetchImpl: async () => ({ ok: true, json: async () => ({ id: '../bad', threadId: 'thread-1' }) }) }), 'google_gmail_invalid_response'],
    [send({ fetchImpl: async () => { throw new Error(PRIVATE_MARKER); } }), 'google_gmail_send_failed'],
  ];
  for (const [pending, message] of errors) await assert.rejects(pending, { message });
});
