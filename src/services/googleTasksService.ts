import { Incident, Server } from '../types/serverDashboard';

export interface GoogleTaskList {
  id: string;
  title: string;
  updated?: string;
  selfLink?: string;
}

export interface GoogleTaskItem {
  id: string;
  title: string;
  updated?: string;
  selfLink?: string;
  parent?: string;
  position?: string;
  notes?: string;
  status: 'needsAction' | 'completed';
  due?: string;
  completed?: string;
  deleted?: boolean;
  hidden?: boolean;
}

const TASKS_BASE_URL = 'https://tasks.googleapis.com/tasks/v1';

/**
 * List all task lists for the authenticated user
 */
export async function listTaskLists(accessToken: string): Promise<GoogleTaskList[]> {
  const res = await fetch(`${TASKS_BASE_URL}/users/@me/lists`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل جلب قوائم مهام Google Tasks: ${res.statusText}`);
  }

  const data = await res.json();
  return data.items || [];
}

/**
 * Create a new task list
 */
export async function createTaskList(accessToken: string, title: string): Promise<GoogleTaskList> {
  const res = await fetch(`${TASKS_BASE_URL}/users/@me/lists`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل إنشاء قائمة المهام: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * List tasks in a specific task list
 */
export async function listTasks(
  accessToken: string,
  taskListId: string = '@default',
  showCompleted: boolean = true,
  showHidden: boolean = false
): Promise<GoogleTaskItem[]> {
  const params = new URLSearchParams({
    showCompleted: String(showCompleted),
    showHidden: String(showHidden),
    maxResults: '100',
  });

  const res = await fetch(`${TASKS_BASE_URL}/lists/${taskListId}/tasks?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل جلب المهام: ${res.statusText}`);
  }

  const data = await res.json();
  return data.items || [];
}

/**
 * Create a new task in a list
 */
export async function createTask(
  accessToken: string,
  taskListId: string = '@default',
  task: {
    title: string;
    notes?: string;
    due?: string; // RFC 3339 timestamp
  }
): Promise<GoogleTaskItem> {
  const res = await fetch(`${TASKS_BASE_URL}/lists/${taskListId}/tasks`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(task),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل إنشاء المهمة: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Update an existing task status (e.g. mark completed or needsAction)
 */
export async function updateTaskStatus(
  accessToken: string,
  taskListId: string = '@default',
  taskId: string,
  status: 'needsAction' | 'completed'
): Promise<GoogleTaskItem> {
  // First retrieve existing task
  const getRes = await fetch(`${TASKS_BASE_URL}/lists/${taskListId}/tasks/${taskId}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!getRes.ok) {
    throw new Error(`تعذر العثور على المهمة لتحديث حالتها.`);
  }

  const existingTask = await getRes.json();
  const updatedTask = {
    ...existingTask,
    status,
    completed: status === 'completed' ? new Date().toISOString() : undefined,
  };

  const res = await fetch(`${TASKS_BASE_URL}/lists/${taskListId}/tasks/${taskId}`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updatedTask),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل تحديث حالة المهمة: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Delete a task
 */
export async function deleteTask(
  accessToken: string,
  taskListId: string = '@default',
  taskId: string
): Promise<boolean> {
  const res = await fetch(`${TASKS_BASE_URL}/lists/${taskListId}/tasks/${taskId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok && res.status !== 204) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل حذف المهمة: ${res.statusText}`);
  }

  return true;
}

/**
 * Create SRE Action Items from an Incident directly into Google Tasks
 */
export async function createIncidentTasks(
  accessToken: string,
  taskListId: string = '@default',
  incident: Incident,
  server?: Server
): Promise<GoogleTaskItem[]> {
  const serverDesc = server ? `${server.name} (${server.ip})` : incident.serverName;
  const dueDate = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(); // 24 hours from now

  const tasksToCreate = [
    {
      title: `[طوارئ SRE] عزل ومعالجة حادثة ${incident.code} على ${serverDesc}`,
      notes: `وصف الحادثة: ${incident.message}\nمستوى الخطورة: ${incident.severity.toUpperCase()}\nوقت الرصد: ${incident.timestamp}\nالتتبع: ${incident.stackTrace || 'N/A'}\n\nتحليل الذكاء الاصطناعي: ${incident.aiAnalysis || 'قيد المتابعة'}`,
      due: dueDate,
    },
    {
      title: `[فحص واختبار] اختبار الجاهزية والتعافي بعد معالجة حادثة ${incident.code}`,
      notes: `إجراء فحص صحة الخدمة (Health check) والتأكد من انخفاض استهلاك الموارد إلى المعدلات الطبيعية بعد إغلاق البلاغ.`,
      due: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
    },
    {
      title: `[توثيق وبحث] تحديث دليل التشغيل Runbook لحادثة ${incident.code}`,
      notes: `إضافة الإجراءات التي تمت لحل الحادثة إلى وثائق الفريق لمنع تكرار العطل مستقبلاً.`,
      due: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
    },
  ];

  const createdItems: GoogleTaskItem[] = [];
  for (const t of tasksToCreate) {
    const created = await createTask(accessToken, taskListId, t);
    createdItems.push(created);
  }

  return createdItems;
}
