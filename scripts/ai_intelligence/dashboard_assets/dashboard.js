import {
  MAX_RUNBOOK_NOTES,
  readRunbookNotes,
  setRunbookNoteArchived,
  setRunbookNotePinned,
} from './runbook_notes.mjs';

const RUNBOOK_STORAGE_KEY = 'devobs_ai7_runbook_notes';
let runbookNotes = [];
let showArchivedRunbookNotes = false;
let pendingRunbookArchiveId = null;

const labels = {
  event_count: 'الأحداث',
  log_event_count: 'سجلات',
  ci_event_count: 'نتائج CI',
  log_cluster_count: 'مجموعات سجلات',
  unknown_group_count: 'بلا فرضية معروفة',
  recommendation_count: 'توصيات',
  metric_series_count: 'سلاسل المقاييس',
  anomaly_candidate_count: 'مرشحو الشذوذ',
  forecast_count: 'استقراءات متاحة',
  trend_range_warning_count: 'تحذيرات نطاق الاستقراء',
  feedback_ranked_recommendation_count: 'ترتيب مدعوم بتغذية راجعة',
};
const causes = {
  timeout: 'مهلة',
  connection: 'اتصال',
  dns: 'DNS',
  permission: 'صلاحية',
  dependency: 'اعتماد',
  memory: 'ذاكرة',
};
const severityLabels = {
  debug: 'تصحيح',
  info: 'معلومات',
  warning: 'تحذير',
  error: 'خطأ',
  critical: 'حرج',
  unknown: 'غير معروف',
};
const stageStatuses = {
  ready: 'جاهز',
  no_data: 'لا توجد بيانات',
  no_metrics: 'لا توجد مقاييس',
  no_logs: 'لا توجد سجلات',
  no_matches: 'لا توجد مطابقة',
  no_events: 'لا توجد أحداث',
  report_available: 'التقرير متاح',
  applied: 'طُبقت الملاحظات المحلية',
  no_feedback: 'لا توجد ملاحظات مشغّل',
  anomaly_candidate: 'مرشح شذوذ',
  no_signal: 'لا توجد إشارة',
  insufficient_data: 'بيانات غير كافية',
};
const metricLabels = {
  cpu_percent: 'استخدام المعالج',
  memory_percent: 'استخدام الذاكرة',
  disk_percent: 'استخدام القرص',
  error_rate: 'معدل الأخطاء',
  request_rate: 'معدل الطلبات',
  latency_ms: 'زمن الاستجابة',
  uptime_seconds: 'مدة التشغيل',
};
const metricUnits = {
  percent: '%',
  per_second: 'طلب/ثانية',
  milliseconds: 'مللي ثانية',
  seconds: 'ثانية',
};
const signalLabels = {
  z_score: 'درجة Z',
  moving_average: 'المتوسط المتحرك',
  ewma: 'المتوسط الأسي',
  error_rate_spike: 'ارتفاع معدل الأخطاء',
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function renderRunbookNotes() {
  const container = document.querySelector('#runbook-notes');
  const query = document.querySelector('#runbook-note-search').value.trim().toLocaleLowerCase('ar');
  const activeCount = runbookNotes.filter(note => !note.isArchived).length;
  document.querySelector('#runbook-active-count').textContent = String(activeCount);
  document.querySelector('#runbook-archived-count').textContent = String(runbookNotes.length - activeCount);
  document.querySelector('#runbook-active-tab').setAttribute('aria-pressed', String(!showArchivedRunbookNotes));
  document.querySelector('#runbook-archived-tab').setAttribute('aria-pressed', String(showArchivedRunbookNotes));
  container.replaceChildren();

  const notes = runbookNotes
    .filter(note => note.isArchived === showArchivedRunbookNotes)
    .filter(note => !query || `${note.title} ${note.content}`.toLocaleLowerCase('ar').includes(query))
    .sort((left, right) => {
      if (!showArchivedRunbookNotes && left.isPinned !== right.isPinned) return left.isPinned ? -1 : 1;
      return right.updatedAt.localeCompare(left.updatedAt);
    });

  if (notes.length === 0) {
    const message = query ? 'لا توجد مذكرات تطابق البحث.' : showArchivedRunbookNotes ? 'الأرشيف فارغ.' : 'لا توجد مذكرات نشطة بعد.';
    container.append(element('p', 'empty', message));
    return;
  }

  for (const note of notes) {
    const card = element('article', 'card runbook-card');
    const heading = element('div', 'runbook-heading');
    const title = element('h3', '', note.title);
    heading.append(title);
    if (note.isPinned && !note.isArchived) heading.append(element('span', 'runbook-pinned', 'مثبتة'));
    card.append(heading);
    card.append(element('p', 'muted runbook-date', `آخر تحديث: ${new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(note.updatedAt))}`));
    card.append(element('p', 'runbook-content', note.content));

    const actions = element('div', 'runbook-actions');
    if (!note.isArchived) {
      const pin = element('button', 'runbook-action', note.isPinned ? 'إلغاء التثبيت' : 'تثبيت');
      pin.type = 'button';
      pin.dataset.runbookAction = 'pin';
      pin.dataset.noteId = note.id;
      pin.setAttribute('aria-label', `${pin.textContent} المذكرة ${note.title}`);
      actions.append(pin);
    }
    const archive = element('button', 'runbook-action', note.isArchived ? 'استعادة' : 'أرشفة');
    archive.type = 'button';
    archive.dataset.runbookAction = 'archive';
    archive.dataset.noteId = note.id;
    archive.setAttribute('aria-label', `${archive.textContent} المذكرة ${note.title}`);
    actions.append(archive);
    card.append(actions);
    container.append(card);
  }
}

function saveRunbookNotes(nextNotes, successMessage) {
  try {
    localStorage.setItem(RUNBOOK_STORAGE_KEY, JSON.stringify(nextNotes));
    runbookNotes = nextNotes;
    document.querySelector('#runbook-note-status').textContent = successMessage;
    renderRunbookNotes();
    return true;
  } catch {
    document.querySelector('#runbook-note-status').textContent = 'تعذر الحفظ في تخزين المتصفح؛ لم يتغير السجل.';
    return false;
  }
}

function initializeRunbookNotes() {
  const status = document.querySelector('#runbook-note-status');
  try {
    runbookNotes = readRunbookNotes(localStorage.getItem(RUNBOOK_STORAGE_KEY));
  } catch {
    status.textContent = 'تخزين المتصفح غير متاح؛ لن تُحفظ المذكرات في هذه الجلسة.';
  }
  renderRunbookNotes();
}

function requestRunbookArchive(noteId) {
  const note = runbookNotes.find(item => item.id === noteId);
  if (!note) return;
  pendingRunbookArchiveId = noteId;
  const restoring = note.isArchived;
  document.querySelector('#runbook-archive-title').textContent = restoring ? 'تأكيد استعادة المذكرة' : 'تأكيد أرشفة المذكرة';
  document.querySelector('#runbook-archive-description').textContent = restoring
    ? `هل تريد استعادة المذكرة «${note.title}» إلى المذكرات النشطة؟`
    : `هل تريد أرشفة المذكرة «${note.title}»؟ ستبقى محفوظة ويمكنك استعادتها لاحقًا.`;
  document.querySelector('#runbook-archive-confirm').textContent = restoring ? 'تأكيد الاستعادة' : 'تأكيد الأرشفة';
  document.querySelector('#runbook-archive-dialog').showModal();
}

function bindRunbookNotes() {
  const form = document.querySelector('#runbook-note-form');
  form.addEventListener('submit', event => {
    event.preventDefault();
    const title = document.querySelector('#runbook-note-title').value.trim();
    const content = document.querySelector('#runbook-note-content').value.trim();
    if (!title || !content) return;
    if (runbookNotes.length >= MAX_RUNBOOK_NOTES) {
      document.querySelector('#runbook-note-status').textContent = `وصلت إلى الحد المحلي البالغ ${MAX_RUNBOOK_NOTES} مذكرة.`;
      return;
    }
    const now = new Date().toISOString();
    const randomId = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const note = { id: `note-${randomId}`, title, content, isArchived: false, isPinned: false, createdAt: now, updatedAt: now };
    if (saveRunbookNotes([note, ...runbookNotes], 'حُفظت المذكرة في هذا المتصفح فقط.')) form.reset();
  });

  document.querySelector('#runbook-notes').addEventListener('click', event => {
    const button = event.target.closest('button[data-runbook-action]');
    if (!button) return;
    const note = runbookNotes.find(item => item.id === button.dataset.noteId);
    if (!note) return;
    if (button.dataset.runbookAction === 'archive') {
      requestRunbookArchive(note.id);
      return;
    }
    if (button.dataset.runbookAction === 'pin') {
      const nextNotes = setRunbookNotePinned(runbookNotes, note.id, !note.isPinned);
      saveRunbookNotes(nextNotes, note.isPinned ? 'أُلغي تثبيت المذكرة محليًا.' : 'ثُبتت المذكرة محليًا.');
    }
  });

  document.querySelector('#runbook-archive-confirm').addEventListener('click', () => {
    const note = runbookNotes.find(item => item.id === pendingRunbookArchiveId);
    if (!note) return;
    const restoring = note.isArchived;
    const nextNotes = setRunbookNoteArchived(runbookNotes, note.id, !note.isArchived);
    if (saveRunbookNotes(nextNotes, restoring ? 'استُعيدت المذكرة محليًا.' : 'أُرشفت المذكرة محليًا.')) {
      pendingRunbookArchiveId = null;
      document.querySelector('#runbook-archive-dialog').close();
    }
  });

  document.querySelector('#runbook-archive-cancel').addEventListener('click', () => {
    pendingRunbookArchiveId = null;
    document.querySelector('#runbook-archive-dialog').close();
  });
  document.querySelector('#runbook-archive-dialog').addEventListener('cancel', () => {
    pendingRunbookArchiveId = null;
  });
  document.querySelector('#runbook-active-tab').addEventListener('click', () => {
    showArchivedRunbookNotes = false;
    renderRunbookNotes();
  });
  document.querySelector('#runbook-archived-tab').addEventListener('click', () => {
    showArchivedRunbookNotes = true;
    renderRunbookNotes();
  });
  document.querySelector('#runbook-note-search').addEventListener('input', renderRunbookNotes);
}

function renderSummary(summary) {
  const container = document.querySelector('#summary');
  container.replaceChildren();
  for (const [key, label] of Object.entries(labels)) {
    const term = element('dt', '', label);
    const value = element('dd', '', summary[key] ?? 0);
    const card = element('div', 'metric-card');
    card.append(term, value);
    container.append(card);
  }
}

function metricName(metric) {
  return metricLabels[metric] ?? 'مقياس غير معروف';
}

function displayValue(value) {
  return Number.isFinite(value) ? String(value) : '—';
}

function renderPipeline(stages) {
  const container = document.querySelector('#pipeline');
  container.replaceChildren();
  for (const stage of stages) {
    const card = element('article', 'card stage-card');
    card.append(element('h3', '', stage.id));
    card.append(element('p', '', stage.name));
    card.append(element('p', 'muted', `الحالة: ${stageStatuses[stage.status] ?? 'حالة غير معروفة'} · العناصر: ${stage.count}`));
    if (stage.candidate_count !== undefined) {
      card.append(element('p', 'muted', `مرشحو الشذوذ: ${stage.candidate_count}`));
    }
    container.append(card);
  }
}

function renderAnomalies(analysis) {
  const container = document.querySelector('#anomalies');
  container.replaceChildren();
  if (analysis.metrics.length === 0) {
    container.append(element('p', 'empty', 'لا توجد مقاييس خادم في سجل الأحداث المحلي.'));
    return;
  }
  for (const metric of analysis.metrics) {
    const card = element('article', 'card');
    const unit = metricUnits[metric.unit] ?? '';
    card.append(element('h3', '', metricName(metric.metric)));
    card.append(element('p', 'muted', `الحالة: ${stageStatuses[metric.status] ?? 'حالة غير معروفة'} · آخر قيمة: ${displayValue(metric.latest_value)} ${unit}`));
    card.append(element('p', '', `عدد العينات: ${metric.observations} · عينات خط الأساس: ${metric.baseline_observations}`));
    const signals = metric.signals.map(signal => signalLabels[signal] ?? 'إشارة غير معروفة');
    card.append(element('p', 'muted', signals.length ? `الإشارات: ${signals.join('، ')}` : 'لم تظهر إشارة شذوذ وفق القواعد الحالية.'));
    container.append(card);
  }
}

function renderTrends(analysis) {
  const container = document.querySelector('#trends');
  container.replaceChildren();
  if (analysis.status === 'no_events') {
    container.append(element('p', 'empty', 'لا توجد أحداث محلية لحساب الاتجاهات.'));
    return;
  }
  const dailyCount = analysis.daily?.event_count ?? 0;
  const weeklyCount = analysis.weekly?.event_count ?? 0;
  const summary = element('article', 'card');
  summary.append(element('h3', '', 'ملخص النوافذ المحلية'));
  summary.append(element('p', 'muted', `أحداث اليوم الأخير في السجل: ${dailyCount} · أحداث آخر سبعة أيام: ${weeklyCount}`));
  container.append(summary);
  if (analysis.metric_forecasts.length === 0) {
    container.append(element('p', 'empty', 'لا توجد مقاييس خادم لإظهار استقراء.'));
    return;
  }
  for (const forecast of analysis.metric_forecasts) {
    const card = element('article', 'card');
    const unit = metricUnits[forecast.unit] ?? '';
    const state = forecast.status === 'range_warning' ? 'تحذير: خرج مرشح عن النطاق' : forecast.status === 'forecast_candidate' ? 'مرشح استرشادي' : 'تاريخ متصل غير كافٍ';
    card.append(element('h3', '', metricName(forecast.metric)));
    card.append(element('p', 'muted', `${state} · أيام متصلة: ${forecast.consecutive_observations}/${forecast.minimum_consecutive_observations}+`));
    card.append(element('p', '', `آخر قيمة يومية: ${displayValue(forecast.latest_value)} ${unit}`));
    if (forecast.linear_regression && forecast.simple_exponential_smoothing) {
      card.append(element('p', '', `مرشح الانحدار الخطي: ${displayValue(forecast.linear_regression.next_day_candidate)} ${unit}`));
      card.append(element('p', '', `مرشح التمهيد الأسي: ${displayValue(forecast.simple_exponential_smoothing.next_day_candidate)} ${unit}`));
    }
    container.append(card);
  }
}

function renderIncidents(incidents) {
  const container = document.querySelector('#incidents');
  container.replaceChildren();
  if (incidents.length === 0) {
    container.append(element('p', 'empty', 'لا توجد مجموعات حوادث في هذه اللقطة.'));
    return;
  }
  for (const incident of incidents) {
    const card = element('article', 'card');
    card.append(element('h3', '', incident.label));
    card.append(element('p', 'muted', `عدد الأحداث: ${incident.event_count}`));
    const list = element('ul', 'compact-list');
    for (const hypothesis of incident.hypotheses) {
      const confidence = hypothesis.heuristic_signal === 'medium' ? 'إشارة heuristic متوسطة' : 'إشارة heuristic منخفضة';
      list.append(element('li', '', `${causes[hypothesis.cause_id] ?? 'فئة غير معروفة'} · ${confidence} · ${hypothesis.evidence_markers.join('، ')}`));
    }
    if (incident.hypotheses.length === 0) list.append(element('li', '', 'لا توجد فرضية من القواعد المعروفة.'));
    card.append(list);
    container.append(card);
  }
}

function renderRecommendations(recommendations) {
  const container = document.querySelector('#recommendations');
  container.replaceChildren();
  if (recommendations.length === 0) {
    container.append(element('p', 'empty', 'لا توجد توصيات معروفة لهذه اللقطة.'));
    return;
  }
  for (const recommendation of recommendations) {
    const card = element('article', 'card recommendation');
    card.append(element('h3', '', `${recommendation.review_order}. ${recommendation.runbook_title}`));
    card.append(element('p', 'muted', `الفئة: ${causes[recommendation.cause_id] ?? 'غير معروفة'} · التصنيف: ${recommendation.classification} · إشارة heuristic: ${recommendation.heuristic_signal}`));
    card.append(element('p', '', `عدد الأحداث: ${recommendation.event_count} · المؤشرات: ${recommendation.evidence_markers.join('، ')}`));
    const checks = element('ul', 'compact-list');
    for (const check of recommendation.read_only_checks) checks.append(element('li', '', check));
    card.append(checks);
    const feedback = recommendation.feedback_review_signal;
    if (feedback.sample_count > 0) {
      const rate = `${(feedback.smoothed_acceptance_rate * 100).toFixed(1)}%`;
      card.append(element('p', 'muted', `إشارة قبول محلية: ${rate} من ${feedback.sample_count} قرارات مختلفة؛ ليست احتمال صحة.`));
    }
    card.append(element('p', 'approval', 'اقتراح فقط · اعتماد بشري مطلوب · التنفيذ التلقائي متوقف'));
    container.append(card);
  }
}

async function load(path) {
  const response = await fetch(path, { method: 'GET', cache: 'no-store', credentials: 'same-origin' });
  if (!response.ok) throw new Error('local_api_unavailable');
  return response.json();
}

async function render() {
  const status = document.querySelector('#status');
  try {
    const intelligence = await load('/api/v1/intelligence');
    renderSummary(intelligence.summary);
    renderPipeline(intelligence.pipeline.stages);
    renderAnomalies(intelligence.anomaly_analysis);
    renderTrends(intelligence.trend_analysis);
    renderIncidents(intelligence.incidents);
    renderRecommendations(intelligence.recommendations);
    status.textContent = 'البيانات من لقطة محلية للقراءة فقط.';
  } catch {
    status.textContent = 'تعذر تحميل اللقطة المحلية. تحقق من الملف ثم أعد تشغيل الخادم.';
  }
}

initializeRunbookNotes();
bindRunbookNotes();
void render();
