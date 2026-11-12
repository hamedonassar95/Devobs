import { Incident, Server } from '../types/serverDashboard';

export interface GoogleCalendarItem {
  id: string;
  summary: string;
  description?: string;
  location?: string;
  start: {
    dateTime?: string;
    date?: string;
    timeZone?: string;
  };
  end: {
    dateTime?: string;
    date?: string;
    timeZone?: string;
  };
  status?: string;
  htmlLink?: string;
  hangoutLink?: string;
  conferenceData?: {
    entryPoints?: Array<{
      entryPointType: string;
      uri: string;
      label?: string;
    }>;
    conferenceSolution?: {
      name: string;
      iconUri?: string;
    };
  };
  attendees?: Array<{
    email: string;
    displayName?: string;
    responseStatus?: string;
    self?: boolean;
  }>;
  created?: string;
  updated?: string;
}

export interface GoogleCalendarListEntry {
  id: string;
  summary: string;
  description?: string;
  primary?: boolean;
  backgroundColor?: string;
  foregroundColor?: string;
  timeZone?: string;
}

const CALENDAR_BASE_URL = 'https://www.googleapis.com/calendar/v3';

/**
 * List all calendars available to the authenticated user
 */
export async function listUserCalendars(accessToken: string): Promise<GoogleCalendarListEntry[]> {
  const res = await fetch(`${CALENDAR_BASE_URL}/users/me/calendarList`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل جلب قائمة تقاويم Google Calendar: ${res.statusText}`);
  }

  const data = await res.json();
  return data.items || [];
}

/**
 * List events for a specific calendar
 */
export async function listCalendarEvents(
  accessToken: string,
  calendarId: string = 'primary',
  timeMin?: string,
  maxResults: number = 50
): Promise<GoogleCalendarItem[]> {
  const params = new URLSearchParams({
    singleEvents: 'true',
    orderBy: 'startTime',
    maxResults: String(maxResults),
  });

  if (timeMin) {
    params.set('timeMin', timeMin);
  } else {
    // Default to events from start of today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    params.set('timeMin', today.toISOString());
  }

  const res = await fetch(`${CALENDAR_BASE_URL}/calendars/${encodeURIComponent(calendarId)}/events?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل جلب أحداث التقويم: ${res.statusText}`);
  }

  const data = await res.json();
  return data.items || [];
}

/**
 * Create a new event on Google Calendar
 */
export async function createCalendarEvent(
  accessToken: string,
  calendarId: string = 'primary',
  eventData: {
    summary: string;
    description?: string;
    location?: string;
    startDateTime: string; // ISO string
    endDateTime: string;   // ISO string
    attendees?: string[];  // Email list
    withGoogleMeet?: boolean;
  }
): Promise<GoogleCalendarItem> {
  const body: any = {
    summary: eventData.summary,
    description: eventData.description,
    location: eventData.location,
    start: {
      dateTime: eventData.startDateTime,
    },
    end: {
      dateTime: eventData.endDateTime,
    },
  };

  if (eventData.attendees && eventData.attendees.length > 0) {
    body.attendees = eventData.attendees.map((email) => ({ email: email.trim() }));
  }

  if (eventData.withGoogleMeet) {
    body.conferenceData = {
      createRequest: {
        requestId: `meet-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        conferenceSolutionKey: { type: 'hangoutsMeet' },
      },
    };
  }

  const url = `${CALENDAR_BASE_URL}/calendars/${encodeURIComponent(calendarId)}/events?conferenceDataVersion=1`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل إنشاء حدث التقويم: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Delete a calendar event
 */
export async function deleteCalendarEvent(
  accessToken: string,
  calendarId: string = 'primary',
  eventId: string
): Promise<boolean> {
  const res = await fetch(`${CALENDAR_BASE_URL}/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok && res.status !== 204) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل حذف الحدث من التقويم: ${res.statusText}`);
  }

  return true;
}

/**
 * Schedule SRE Incident Post-Mortem / War Room meeting
 */
export async function scheduleIncidentWarRoom(
  accessToken: string,
  calendarId: string = 'primary',
  incident: Incident,
  server?: Server,
  attendeeEmails: string[] = []
): Promise<GoogleCalendarItem> {
  const serverDesc = server ? `${server.name} (${server.ip})` : incident.serverName;
  const now = new Date();
  const startTime = new Date(now.getTime() + 15 * 60 * 1000); // 15 minutes from now
  const endTime = new Date(startTime.getTime() + 45 * 60 * 1000); // 45 minute duration

  const summary = `[War Room SRE] مراجعة طوارئ الحادثة ${incident.code} - ${serverDesc}`;
  const description = `اجتماع طوارئ واستجابة سريعة لحادثة تشغيلية:
- رمز الحادثة: ${incident.code}
- مستوى الخطورة: ${incident.severity.toUpperCase()}
- الخادم المتأثر: ${serverDesc}
- توقيت الرصد: ${incident.timestamp}
- تفاصيل العطل: ${incident.message}

أجندة الاجتماع:
1. استعراض تقرير الأثر المباشر والخدمات المتوقفة.
2. عزل السبب الجذري والتحقق من سجلات الأخطاء.
3. اعتماد خطة المعالجة أو التراجع (Rollback).
4. توثيق الاستخلاصات في كتيب التشغيل (Post-Mortem Runbook).

تتبع الخطأ (Stack Trace):
${incident.stackTrace || 'غير متوفر'}

تحليل الذكاء الاصطناعي:
${incident.aiAnalysis || 'قيد المتابعة'}`;

  return await createCalendarEvent(accessToken, calendarId, {
    summary,
    description,
    location: `غرفة عمليات الأنظمة - DevOps War Room`,
    startDateTime: startTime.toISOString(),
    endDateTime: endTime.toISOString(),
    attendees: attendeeEmails,
    withGoogleMeet: true,
  });
}

/**
 * Schedule Planned Server Maintenance Window
 */
export async function scheduleServerMaintenanceWindow(
  accessToken: string,
  calendarId: string = 'primary',
  server: Server,
  startDateTime: string,
  durationHours: number = 2,
  notes: string = '',
  attendeeEmails: string[] = []
): Promise<GoogleCalendarItem> {
  const start = new Date(startDateTime);
  const end = new Date(start.getTime() + durationHours * 60 * 60 * 1000);

  const summary = `[نافذة صيانة] تحديثات دورية للخادم ${server.name} (${server.ip})`;
  const description = `نافذة صيانة مجدولة للأنظمة والخوادم:
- الخادم: ${server.name}
- العنوان الرقمي: ${server.ip}
- المنطقة: ${server.region}
- نظام التشغيل: ${server.os}
- الاستهلاك الحالي: CPU ${server.cpu}% | الذاكرة ${server.memory}%
- مدة النافذة المحددة: ${durationHours} ساعة

إجراءات الصيانة المستهدفة:
${notes || '- تطبيق التحديثات الأمنية وتحديث حزم النواة (Kernel patches).\n- تنظيف السجلات المؤقتة وتدوير ملفات الـ logs.\n- اختبار مسار التعافي والنسخ الاحتياطي.'}

ملاحظة للمناوبين:
يرجى التأكد من تحويل حركة البيانات (Traffic rerouting) قبل بدء الصيانة وإجراء فحص الجاهزية فور الانتهاء.`;

  return await createCalendarEvent(accessToken, calendarId, {
    summary,
    description,
    location: `مركز البيانات (${server.region})`,
    startDateTime: start.toISOString(),
    endDateTime: end.toISOString(),
    attendees: attendeeEmails,
    withGoogleMeet: true,
  });
}
