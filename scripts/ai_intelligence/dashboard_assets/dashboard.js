const labels = {
  event_count: 'الأحداث',
  log_event_count: 'سجلات',
  ci_event_count: 'نتائج CI',
  log_cluster_count: 'مجموعات سجلات',
  unknown_group_count: 'بلا فرضية معروفة',
  recommendation_count: 'توصيات',
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

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
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
    const [summary, incidents, recommendations] = await Promise.all([
      load('/api/v1/summary'),
      load('/api/v1/incidents'),
      load('/api/v1/recommendations'),
    ]);
    renderSummary(summary);
    renderIncidents(incidents.incidents);
    renderRecommendations(recommendations.recommendations);
    status.textContent = 'البيانات من لقطة محلية للقراءة فقط.';
  } catch {
    status.textContent = 'تعذر تحميل اللقطة المحلية. تحقق من الملف ثم أعد تشغيل الخادم.';
  }
}

void render();
