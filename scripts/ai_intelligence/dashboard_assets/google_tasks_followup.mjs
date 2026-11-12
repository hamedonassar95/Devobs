export const GOOGLE_TASKS_SCOPE = 'https://www.googleapis.com/auth/tasks';

const TASKS_API_URL = 'https://tasks.googleapis.com/tasks/v1/lists/@default/tasks';
const TASK_TITLE = 'مراجعة توصيات Devobs AI-7';

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function count(value) {
  return Number.isSafeInteger(value) && value >= 0 && value <= 1_000_000 ? value : 0;
}

function isValidDueDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function validAccessToken(value) {
  return typeof value === 'string' && value.length >= 16 && value.length <= 4096
    && !/[\s\x00-\x1f\x7f]/.test(value);
}

/** Build one fixed follow-up task from allowlisted aggregate counts only. */
export function buildGoogleTasksFollowup(snapshot, dueDate) {
  if (!isRecord(snapshot) || !isRecord(snapshot.summary) || !isValidDueDate(dueDate)) {
    throw new TypeError('invalid_google_tasks_report_input');
  }

  const summary = snapshot.summary;
  return {
    title: TASK_TITLE,
    notes: [
      'راجع توصيات لوحة AI-7 يدويًا؛ النتائج استرشادية ولا تثبت سبب المشكلة.',
      `عدد التوصيات: ${count(summary.recommendation_count)}`,
      `مرشحو الشذوذ: ${count(summary.anomaly_candidate_count)}`,
      `استقراءات الاتجاه: ${count(summary.forecast_count)}`,
      'لا تتضمن هذه المهمة نصوص سجلات أو أسماء عملاء أو معرّفات خدمات.',
    ].join('\n'),
    due: `${dueDate}T00:00:00.000Z`,
  };
}

/** Create one task in the default task list; this module never reads task data. */
export async function createGoogleTasksFollowup({ accessToken, snapshot, dueDate, fetchImpl = fetch }) {
  if (!validAccessToken(accessToken) || typeof fetchImpl !== 'function') {
    throw new TypeError('invalid_google_tasks_request');
  }
  const task = buildGoogleTasksFollowup(snapshot, dueDate);

  let response;
  try {
    response = await fetchImpl(TASKS_API_URL, {
      method: 'POST',
      redirect: 'error',
      cache: 'no-store',
      credentials: 'omit',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(task),
    });
  } catch {
    throw new Error('google_tasks_create_failed');
  }
  if (!response || response.ok !== true) throw new Error('google_tasks_create_failed');

  let created;
  try {
    created = await response.json();
  } catch {
    throw new Error('google_tasks_invalid_response');
  }
  if (!isRecord(created) || typeof created.id !== 'string' || !/^[A-Za-z0-9_-]{1,256}$/.test(created.id)
    || created.title !== TASK_TITLE) {
    throw new Error('google_tasks_invalid_response');
  }
  return { taskId: created.id, dueDate };
}
