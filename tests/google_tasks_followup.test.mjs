import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildGoogleTasksFollowup,
  createGoogleTasksFollowup,
  GOOGLE_TASKS_SCOPE,
} from '../scripts/ai_intelligence/dashboard_assets/google_tasks_followup.mjs';

const ACCESS_TOKEN = 'synthetic_google_access_token_123';
const RAW_MARKER = 'PRIVATE_INCIDENT_TEXT_MUST_NOT_LEAVE_LOCAL_DASHBOARD';
const snapshot = {
  summary: {
    recommendation_count: 2,
    anomaly_candidate_count: 1,
    forecast_count: 3,
    [RAW_MARKER]: 99,
  },
  incidents: [{ message: RAW_MARKER, event_id: RAW_MARKER }],
  recommendations: [{ runbook_title: RAW_MARKER }],
};

function jsonResponse(value, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => value };
}

test('task preview contains fixed text, allowlisted counts and a valid due date only', () => {
  const task = buildGoogleTasksFollowup(snapshot, '2030-02-03');
  assert.equal(GOOGLE_TASKS_SCOPE, 'https://www.googleapis.com/auth/tasks');
  assert.equal(task.title, 'مراجعة توصيات Devobs AI-7');
  assert.match(task.notes, /عدد التوصيات: 2/);
  assert.match(task.notes, /مرشحو الشذوذ: 1/);
  assert.match(task.notes, /استقراءات الاتجاه: 3/);
  assert.equal(task.due, '2030-02-03T00:00:00.000Z');
  assert.equal(JSON.stringify(task).includes(RAW_MARKER), false);
  assert.throws(() => buildGoogleTasksFollowup(snapshot, '2030-02-30'), {
    message: 'invalid_google_tasks_report_input',
  });
  assert.throws(() => buildGoogleTasksFollowup({}, '2030-02-03'), {
    message: 'invalid_google_tasks_report_input',
  });
});

test('creator posts exactly one task to the default list and never reads existing tasks', async () => {
  const calls = [];
  const result = await createGoogleTasksFollowup({
    accessToken: ACCESS_TOKEN,
    snapshot,
    dueDate: '2030-02-03',
    fetchImpl: async (url, options) => {
      calls.push({ url: String(url), options });
      return jsonResponse({ id: 'task_123', title: 'مراجعة توصيات Devobs AI-7' });
    },
  });

  assert.deepEqual(result, { taskId: 'task_123', dueDate: '2030-02-03' });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://tasks.googleapis.com/tasks/v1/lists/@default/tasks');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[0].options.credentials, 'omit');
  assert.equal(calls[0].options.headers.Authorization, `Bearer ${ACCESS_TOKEN}`);
  assert.equal(calls[0].url.includes(ACCESS_TOKEN), false);
  assert.equal(calls[0].options.body.includes(ACCESS_TOKEN), false);
  assert.equal(JSON.stringify(calls).includes(RAW_MARKER), false);
  assert.equal(JSON.stringify(calls).includes('GET'), false);
});

test('creator rejects invalid input, provider errors and uncertain responses without exposing details', async () => {
  await assert.rejects(createGoogleTasksFollowup({
    accessToken: '', snapshot, dueDate: '2030-02-03',
  }), { message: 'invalid_google_tasks_request' });
  await assert.rejects(createGoogleTasksFollowup({
    accessToken: ACCESS_TOKEN, snapshot, dueDate: 'not-a-date',
  }), { message: 'invalid_google_tasks_report_input' });
  await assert.rejects(createGoogleTasksFollowup({
    accessToken: ACCESS_TOKEN,
    snapshot,
    dueDate: '2030-02-03',
    fetchImpl: async () => { throw new Error(RAW_MARKER); },
  }), { message: 'google_tasks_create_failed' });
  await assert.rejects(createGoogleTasksFollowup({
    accessToken: ACCESS_TOKEN,
    snapshot,
    dueDate: '2030-02-03',
    fetchImpl: async () => jsonResponse({ error: RAW_MARKER }, 403),
  }), { message: 'google_tasks_create_failed' });
  await assert.rejects(createGoogleTasksFollowup({
    accessToken: ACCESS_TOKEN,
    snapshot,
    dueDate: '2030-02-03',
    fetchImpl: async () => jsonResponse({ id: 'task_123', title: RAW_MARKER }),
  }), { message: 'google_tasks_invalid_response' });
});
