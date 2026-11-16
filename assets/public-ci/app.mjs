import { buildPublicCiCloudEvent, fetchPublicCi } from './api.mjs';
import './portfolio-view.mjs';

const labels = Object.freeze({
  success: 'نجحت فحوص CI لهذا التشغيل', failure: 'فشلت فحوص CI',
  pending: 'قيد الانتظار', running: 'قيد التنفيذ', cancelled: 'أُلغي التشغيل',
  timed_out: 'انتهت مهلة التشغيل', neutral: 'نتيجة محايدة', skipped: 'تم تجاوز التشغيل',
  action_required: 'يتطلب التشغيل تدخلًا', stale: 'نتيجة قديمة أو لا تطابق main',
  startup_failure: 'تعذر بدء التشغيل', missing: 'لا يوجد تشغيل مطابق للفرع والسير المحددين',
});
const errors = Object.freeze({
  rate_limited: 'بلغت حد الطلبات لدى GitHub. انتظر ثم جرّب يدويًا.',
  timeout: 'لم يصل رد GitHub في المهلة. يمكنك المحاولة يدويًا.',
  not_available: 'لم تتوفر بيانات المستودع العام أو سير CI المحدد.',
  invalid_response: 'وصل رد غير متوافق؛ الحالة غير متحققة.',
  unavailable: 'تعذر الاتصال بـGitHub الآن. لا توجد نتيجة جديدة.',
});
const button = document.getElementById('check-public-ci');
const downloadButton = document.getElementById('download-public-ci');
const status = document.getElementById('ci-status');
const evidence = document.getElementById('ci-evidence');
const runLink = document.getElementById('ci-run-link');
const fields = ['ci-outcome', 'ci-match', 'ci-main-sha', 'ci-run-sha', 'ci-updated', 'ci-observed'];
let loading = false;
let downloadableEvent = null;
function clearEvidence() {
  downloadableEvent = null;
  if (downloadButton) downloadButton.disabled = true;
  evidence.hidden = true;
  for (const id of fields) document.getElementById(id).textContent = '';
  runLink.hidden = true; runLink.removeAttribute('href');
}
function put(id, value) { document.getElementById(id).textContent = value; }
function utc(value) {
  return new Intl.DateTimeFormat('ar', { timeZone: 'UTC', dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
}
button.addEventListener('click', async () => {
  if (loading) return;
  loading = true; button.disabled = true;
  clearEvidence(); status.textContent = 'جارٍ قراءة بيانات GitHub العامة…';
  try {
    const result = await fetchPublicCi();
    downloadableEvent = buildPublicCiCloudEvent(result);
    if (downloadButton) downloadButton.disabled = downloadableEvent === null;
    put('ci-outcome', labels[result.state]);
    put('ci-main-sha', result.mainSha.slice(0, 12));
    put('ci-run-sha', result.runSha ? result.runSha.slice(0, 12) : '—');
    put('ci-match', result.matchesHead === undefined ? 'غير متحققة'
      : result.matchesHead ? 'متطابقان في الردين المسترجعين' : 'غير متطابقين');
    put('ci-updated', result.updatedAt ? utc(result.updatedAt) : '—');
    put('ci-observed', utc(new Date()));
    if (result.runUrl) { runLink.href = result.runUrl; runLink.hidden = false; }
    evidence.hidden = false;
    status.textContent = 'اكتملت القراءة العامة. النتيجة تخص البيانات المسترجعة عند هذا الطلب.';
  } catch (error) {
    clearEvidence(); status.textContent = errors[error?.code] ?? errors.unavailable;
  } finally { loading = false; button.disabled = false; }
});
downloadButton?.addEventListener('click', () => {
  if (loading || downloadableEvent === null) return;
  const url = URL.createObjectURL(new Blob([downloadableEvent], { type: 'application/x-ndjson' }));
  const link = document.createElement('a');
  link.href = url; link.download = 'devobs-public-ci.cloudevents.jsonl';
  document.body.append(link);
  try { link.click(); }
  finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
});
status.textContent = 'لم يبدأ الفحص. اضغط الزر عند رغبتك في جلب البيانات العامة.';
button.disabled = false;
