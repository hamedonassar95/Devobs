import { inspectPublicPortfolio, PUBLIC_TARGETS } from './portfolio-api.mjs';
import { buildPortfolioCloudEvents } from './portfolio-export.mjs';

// This view makes no requests until the user clicks the button.
const button = document.getElementById('check-portfolio-ci');
const status = document.getElementById('portfolio-status');
const results = document.getElementById('portfolio-results');
const download = document.getElementById('download-portfolio-ci');
const LABELS = Object.freeze({
  success: 'CI ناجح للتشغيل المطابق',
  failure: 'CI فاشل', stale: 'نتيجة قديمة لا تطابق main',
  cancelled: 'تشغيل ملغى', timed_out: 'انتهت مهلة CI',
  neutral: 'نتيجة محايدة', skipped: 'تم تخطي CI',
  pending: 'قيد الانتظار', running: 'قيد التنفيذ',
  action_required: 'تدخل مطلوب', startup_failure: 'فشل بدء CI',
  missing: 'لا يوجد تشغيل CI مطابق', unverified: 'تعذر التحقق من الحالة',
});
let loading = false;
let downloadableJsonl = null;

function clearRows() {
  downloadableJsonl = null;
  if (download) download.disabled = true;
  results.replaceChildren();
  results.hidden = true;
}
function row(title, value) {
  const container = document.createElement('div');
  const heading = document.createElement('dt');
  heading.textContent = title;
  const detail = document.createElement('dd');
  detail.textContent = value;
  container.append(heading, detail);
  return container;
}

button.addEventListener('click', async () => {
  if (loading) return;
  loading = true;
  button.disabled = true;
  clearRows();
  status.textContent = 'جارٍ فحص بيانات GitHub العامة للمشاريع الأربعة…';
  try {
    const report = await inspectPublicPortfolio();
    if (report.checked_count !== PUBLIC_TARGETS.length
        || report.results.length !== PUBLIC_TARGETS.length
        || report.private_repositories_queried !== false || report.read_only !== true) {
      throw new Error('invalid_portfolio_report');
    }
    for (let i = 0; i < report.results.length; i++) {
      const entry = report.results[i];
      if (entry.repository !== PUBLIC_TARGETS[i].repo) throw new Error('invalid_portfolio_source');
      const suffix = entry.status === 'unverified'
        ? ' — لا توجد نتيجة موثوقة'
        : entry.status === 'stale' ? ' — لا تعرض على أنها نجاح حالي' : '';
      results.append(row(entry.repository, (LABELS[entry.status] ?? LABELS.unverified) + suffix));
    }
    const exportResult = buildPortfolioCloudEvents(report);
    downloadableJsonl = exportResult.jsonl;
    if (download) download.disabled = downloadableJsonl === null;
    results.hidden = false;
    status.textContent = 'اكتمل الفحص اليدوي. المؤهلة للتصدير: ' + exportResult.included
      + ' من 4؛ والباقي غير مكتمل الأدلة أو غير مؤهل. نجاح CI ليس تشخيصًا.';
  } catch {
    clearRows();
    status.textContent = 'تعذر إكمال فحص المحفظة، ولم تُثبت أي نتيجة جديدة.';
  } finally {
    loading = false;
    button.disabled = false;
  }
});
download?.addEventListener('click', () => {
  if (loading || downloadableJsonl === null) return;
  const url = URL.createObjectURL(new Blob([downloadableJsonl], { type: 'application/x-ndjson' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'devobs-portfolio-ci.cloudevents.jsonl';
  document.body.append(link);
  try { link.click(); }
  finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
});
status.textContent = 'لم يُنفّذ الفحص بعد. اضغط الزر لقراءة الحالة العامة عند الطلب.';
button.disabled = false;
