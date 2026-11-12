import assert from 'node:assert/strict';
import test from 'node:test';
import {
  deriveFollowupEventId,
  FOLLOWUP_CALENDAR_MARKER,
  FOLLOWUP_CALENDAR_NAME,
  GOOGLE_CALENDAR_SCOPE,
  scheduleGoogleCalendarFollowup,
} from '../scripts/ai_intelligence/dashboard_assets/google_calendar_followup.mjs';

const token = 'synthetic_google_access_token_123';
const calendarId = 'devobs-followups@group.calendar.google.com';
const startDateTime = '2030-01-02T03:04:00.000Z';
const now = () => Date.parse('2030-01-01T00:00:00.000Z');

function jsonResponse(value, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => value };
}

function eventShape() {
  return {
    id: deriveFollowupEventId(startDateTime),
    summary: 'Devobs follow-up review',
    description: 'A user-scheduled review of local Devobs recommendations. No incident logs or customer data are attached.',
    start: { dateTime: startDateTime },
    end: { dateTime: '2030-01-02T03:34:00.000Z' },
  };
}

test('calendar scope and deterministic event id use Google supported id characters', () => {
  const first = deriveFollowupEventId(startDateTime);
  assert.equal(GOOGLE_CALENDAR_SCOPE, 'https://www.googleapis.com/auth/calendar.app.created');
  assert.match(first, /^[0-9a-v]{5,1024}$/);
  assert.equal(first, deriveFollowupEventId(startDateTime));
  assert.notEqual(first, deriveFollowupEventId('2030-01-02T03:05:00.000Z'));
  assert.throws(() => deriveFollowupEventId('2030-01-02T03:04:00Z'), { message: 'invalid_google_calendar_event_id_input' });
});

test('first use creates one dedicated calendar and a fixed event without incident data or invitees', async () => {
  const calls = [];
  let storedCalendarId = '';
  const result = await scheduleGoogleCalendarFollowup({
    accessToken: token,
    startDateTime,
    eventId: deriveFollowupEventId(startDateTime),
    now,
    onCalendarCreated: value => { storedCalendarId = value; },
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      if (calls.length === 1) return jsonResponse({
        id: calendarId,
        summary: FOLLOWUP_CALENDAR_NAME,
        description: FOLLOWUP_CALENDAR_MARKER,
      });
      return jsonResponse({ id: deriveFollowupEventId(startDateTime), summary: 'Devobs follow-up review' });
    },
  });

  assert.deepEqual(result, { calendarCreated: true, alreadyScheduled: false });
  assert.equal(storedCalendarId, calendarId);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, 'https://www.googleapis.com/calendar/v3/calendars');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.credentials, 'omit');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.headers.Authorization, `Bearer ${token}`);
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    summary: FOLLOWUP_CALENDAR_NAME,
    description: FOLLOWUP_CALENDAR_MARKER,
  });
  assert.match(calls[1].url, /devobs-followups%40group\.calendar\.google\.com\/events\?sendUpdates=none$/);
  const event = JSON.parse(calls[1].options.body);
  assert.deepEqual(event, eventShape());
  assert.equal(Object.hasOwn(event, 'attendees'), false);
  assert.equal(Object.hasOwn(event, 'conferenceData'), false);
  assert.equal(calls.some(call => call.url.includes('calendarList')), false);
  assert.equal(calls.some(call => call.url.includes(token)), false);
  assert.equal(JSON.stringify(calls).includes('CUSTOMER_RAW_MARKER'), false);
});

test('reuses only the locally saved app-created calendar and verifies duplicate events', async () => {
  const calls = [];
  const expectedEvent = eventShape();
  const result = await scheduleGoogleCalendarFollowup({
    accessToken: token,
    startDateTime,
    eventId: expectedEvent.id,
    calendarId,
    now,
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      if (calls.length === 1) return jsonResponse({
        id: calendarId,
        summary: FOLLOWUP_CALENDAR_NAME,
        description: FOLLOWUP_CALENDAR_MARKER,
      });
      if (calls.length === 2) return { ...jsonResponse({ error: 'private provider response' }, 409), ok: false };
      return jsonResponse(expectedEvent);
    },
  });

  assert.deepEqual(result, { calendarCreated: false, alreadyScheduled: true });
  assert.equal(calls.length, 3);
  assert.match(calls[0].url, /\/calendars\/devobs-followups%40group\.calendar\.google\.com$/);
  assert.equal(calls[0].options.method, 'GET');
  assert.match(calls[1].url, /\/events\?sendUpdates=none$/);
  assert.match(calls[2].url, /\/events\/devobs[0-9a-v]+$/);
  assert.equal(calls[2].options.method, 'GET');
});

test('fails closed on foreign calendars, API errors, conflicts, invalid input, and nonfuture times', async () => {
  const eventId = deriveFollowupEventId(startDateTime);
  const scheduleNew = fetchImpl => scheduleGoogleCalendarFollowup({
    accessToken: token,
    startDateTime,
    eventId,
    now,
    fetchImpl,
  });

  await assert.rejects(scheduleNew(async () => jsonResponse({
    id: calendarId,
    summary: FOLLOWUP_CALENDAR_NAME,
    description: 'not owned by this integration',
  })), { message: 'google_calendar_invalid_response' });
  await assert.rejects(scheduleGoogleCalendarFollowup({
    accessToken: token,
    startDateTime,
    eventId,
    calendarId,
    now,
    fetchImpl: async () => jsonResponse({ id: calendarId, summary: 'another calendar', description: FOLLOWUP_CALENDAR_MARKER }),
  }), { message: 'google_calendar_saved_calendar_unavailable' });
  await assert.rejects(scheduleNew(async () => { throw new Error('CUSTOMER_RAW_MARKER'); }), {
    message: 'google_calendar_create_failed',
  });
  await assert.rejects(scheduleNew(async () => ({ ok: false, status: 403, json: async () => ({ error: 'CUSTOMER_RAW_MARKER' }) })), {
    message: 'google_calendar_create_failed',
  });

  const conflictCalls = [];
  await assert.rejects(scheduleGoogleCalendarFollowup({
    accessToken: token,
    startDateTime,
    eventId,
    calendarId,
    now,
    fetchImpl: async url => {
      conflictCalls.push(url);
      if (conflictCalls.length === 1) return jsonResponse({
        id: calendarId,
        summary: FOLLOWUP_CALENDAR_NAME,
        description: FOLLOWUP_CALENDAR_MARKER,
      });
      if (conflictCalls.length === 2) return { ...jsonResponse({}, 409), ok: false };
      return jsonResponse({ ...eventShape(), summary: 'unrelated event' });
    },
  }), { message: 'google_calendar_event_conflict' });

  await assert.rejects(scheduleGoogleCalendarFollowup({
    accessToken: token,
    startDateTime: '2030-01-02T03:04:00',
    eventId,
    now,
    fetchImpl: async () => { throw new Error('must_not_call'); },
  }), { message: 'invalid_google_calendar_followup' });
  await assert.rejects(scheduleGoogleCalendarFollowup({
    accessToken: token,
    startDateTime,
    eventId,
    now: () => Date.parse(startDateTime),
    fetchImpl: async () => { throw new Error('must_not_call'); },
  }), { message: 'google_calendar_time_must_be_future' });
  await assert.rejects(scheduleGoogleCalendarFollowup({
    accessToken: 'short', startDateTime, eventId, now,
  }), { message: 'invalid_google_calendar_request' });
});
