export const GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.app.created';
export const FOLLOWUP_CALENDAR_NAME = 'Devobs AI-7 Follow-ups';
export const FOLLOWUP_CALENDAR_MARKER = 'devobs-local-ai7-followup-calendar-v1';

const CALENDAR_API_BASE = 'https://www.googleapis.com/calendar/v3';
const EVENT_TITLE = 'Devobs follow-up review';
const EVENT_DESCRIPTION = 'A user-scheduled review of local Devobs recommendations. No incident logs or customer data are attached.';
const EVENT_DURATION_MS = 30 * 60 * 1000;

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function validAccessToken(value) {
  return typeof value === 'string' && value.length >= 16 && value.length <= 4096
    && !/[\s\x00-\x1f\x7f]/.test(value);
}

function validCalendarId(value) {
  return typeof value === 'string' && value.length > 0 && value.length <= 320
    && /^[A-Za-z0-9._@+-]+$/.test(value);
}

function validStartDateTime(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return false;
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString() === value;
}

export function deriveFollowupEventId(startDateTime) {
  if (!validStartDateTime(startDateTime)) {
    throw new TypeError('invalid_google_calendar_event_id_input');
  }
  return `devobs${Date.parse(startDateTime).toString(16)}`;
}

function buildEvent({ startDateTime, eventId, now }) {
  if (!validStartDateTime(startDateTime) || typeof eventId !== 'string' || !/^[0-9a-v]{5,1024}$/.test(eventId)
    || typeof now !== 'function') {
    throw new TypeError('invalid_google_calendar_followup');
  }
  const startMs = Date.parse(startDateTime);
  const currentMs = now();
  if (!Number.isFinite(currentMs) || startMs <= currentMs) throw new TypeError('google_calendar_time_must_be_future');
  return {
    id: eventId,
    summary: EVENT_TITLE,
    description: EVENT_DESCRIPTION,
    start: { dateTime: new Date(startMs).toISOString() },
    end: { dateTime: new Date(startMs + EVENT_DURATION_MS).toISOString() },
  };
}

async function readJson(response, code) {
  if (!response || response.ok !== true) throw new Error(code);
  try {
    const value = await response.json();
    if (!isRecord(value)) throw new Error(code);
    return value;
  } catch {
    throw new Error(code);
  }
}

function requestOptions(accessToken, method, body) {
  const options = {
    method,
    redirect: 'error',
    cache: 'no-store',
    credentials: 'omit',
    headers: { Authorization: `Bearer ${accessToken}` },
  };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  return options;
}

async function getFollowupCalendar(accessToken, calendarId, fetchImpl) {
  let response;
  try {
    response = await fetchImpl(`${CALENDAR_API_BASE}/calendars/${encodeURIComponent(calendarId)}`, requestOptions(accessToken, 'GET'));
  } catch {
    throw new Error('google_calendar_saved_calendar_unavailable');
  }
  const payload = await readJson(response, 'google_calendar_saved_calendar_unavailable');
  if (payload.id !== calendarId || payload.summary !== FOLLOWUP_CALENDAR_NAME
    || payload.description !== FOLLOWUP_CALENDAR_MARKER) {
    throw new Error('google_calendar_saved_calendar_unavailable');
  }
  return payload;
}

async function resolveFollowupCalendar(accessToken, fetchImpl, calendarId) {
  if (calendarId) {
    if (!validCalendarId(calendarId)) throw new TypeError('invalid_google_calendar_request');
    await getFollowupCalendar(accessToken, calendarId, fetchImpl);
    return { id: calendarId, created: false };
  }
  let response;
  try {
    response = await fetchImpl(`${CALENDAR_API_BASE}/calendars`, requestOptions(accessToken, 'POST', {
      summary: FOLLOWUP_CALENDAR_NAME,
      description: FOLLOWUP_CALENDAR_MARKER,
    }));
  } catch {
    throw new Error('google_calendar_create_failed');
  }
  const created = await readJson(response, 'google_calendar_create_failed');
  if (!validCalendarId(created.id) || created.summary !== FOLLOWUP_CALENDAR_NAME
    || created.description !== FOLLOWUP_CALENDAR_MARKER) {
    throw new Error('google_calendar_invalid_response');
  }
  return { id: created.id, created: true };
}

async function confirmExistingEvent(accessToken, calendarId, event, fetchImpl) {
  let response;
  try {
    const url = `${CALENDAR_API_BASE}/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(event.id)}`;
    response = await fetchImpl(url, requestOptions(accessToken, 'GET'));
  } catch {
    throw new Error('google_calendar_event_conflict');
  }
  const existing = await readJson(response, 'google_calendar_event_conflict');
  if (existing.id !== event.id || existing.summary !== event.summary
    || existing.description !== event.description
    || existing.start?.dateTime !== event.start.dateTime
    || existing.end?.dateTime !== event.end.dateTime) {
    throw new Error('google_calendar_event_conflict');
  }
}

/** Create one fixed, attendee-free review event on a dedicated app-created calendar. */
export async function scheduleGoogleCalendarFollowup({
  accessToken,
  startDateTime,
  eventId,
  calendarId = '',
  onCalendarCreated,
  fetchImpl = fetch,
  now = Date.now,
}) {
  if (!validAccessToken(accessToken) || typeof fetchImpl !== 'function'
    || typeof calendarId !== 'string' || (calendarId !== '' && !validCalendarId(calendarId))
    || (onCalendarCreated !== undefined && typeof onCalendarCreated !== 'function')) {
    throw new TypeError('invalid_google_calendar_request');
  }
  const event = buildEvent({ startDateTime, eventId, now });
  const calendar = await resolveFollowupCalendar(accessToken, fetchImpl, calendarId);
  if (calendar.created && onCalendarCreated) {
    try {
      onCalendarCreated(calendar.id);
    } catch {
      throw new Error('google_calendar_id_store_failed');
    }
  }

  let response;
  try {
    const url = `${CALENDAR_API_BASE}/calendars/${encodeURIComponent(calendar.id)}/events?sendUpdates=none`;
    response = await fetchImpl(url, requestOptions(accessToken, 'POST', event));
  } catch {
    throw new Error('google_calendar_event_create_failed');
  }
  if (response?.status === 409) {
    await confirmExistingEvent(accessToken, calendar.id, event, fetchImpl);
    return { calendarCreated: calendar.created, alreadyScheduled: true };
  }
  const created = await readJson(response, 'google_calendar_event_create_failed');
  if (created.id !== event.id || created.summary !== EVENT_TITLE) {
    throw new Error('google_calendar_invalid_response');
  }
  return { calendarCreated: calendar.created, alreadyScheduled: false };
}
