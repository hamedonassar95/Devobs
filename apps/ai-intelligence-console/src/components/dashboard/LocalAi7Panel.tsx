import React, { useEffect, useRef, useState } from 'react';
import { Activity, RefreshCw, ShieldCheck } from 'lucide-react';

type Stage = { id: string; status: string; count: number };
type Recommendation = {
  review_order: number;
  cause_id: string;
  classification: 'POSSIBLE';
  heuristic_signal: 'low' | 'medium';
  event_count: number;
  evidence_markers: string[];
  requires_human_approval: true;
  automatic_execution: false;
};

const CAUSES: Readonly<Record<string, string>> = {
  timeout: 'مهلة عملية أو اعتماد',
  connection: 'اتصال مرفوض أو مقطوع',
  dns: 'حل اسم المضيف',
  permission: 'صلاحية مورد',
  dependency: 'حل وحدة أو اعتماد',
  memory: 'حد الذاكرة',
};
const READ_ONLY_GUIDANCE: Readonly<Record<string, string>> = {
  timeout: 'راجع توقيت أول خطوة متعثرة وحدود المهلة المسجلة، دون تعديل التشغيل.',
  connection: 'قارن وقت الخطأ بحالة الخدمة وسجل الاتصال المصرح به، دون طلب تشغيل جديد.',
  dns: 'راجع اسم الوجهة من الإعدادات المصرح بها دون إظهار أسرار أو تغيير DNS.',
  permission: 'راجع هوية العملية وصلاحيات المورد قراءةً فقط دون توسيعها.',
  dependency: 'قارن ملف القفل ومسار الاستيراد في SHA المتأثر دون إعادة النشر.',
  memory: 'قارن قياسات الذاكرة وحجم المدخلات قبل اقتراح أي تغيير للموارد.',
};

type Snapshot = {
  source: 'local_ai7_snapshot';
  mode: 'local_advisory_only';
  read_only: true;
  summary: {
    event_count: number;
    log_cluster_count: number;
    recommendation_count: number;
    anomaly_candidate_count: number;
  };
  stages: Stage[];
  recommendations: Recommendation[];
};

/** No implicit polling or network calls: refresh requires a direct click. */
export function LocalAi7Panel() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [message, setMessage] = useState('لم يُطلب اتصال بالمحرك المحلي بعد.');
  const [loading, setLoading] = useState(false);
  const [reviewedOrders, setReviewedOrders] = useState<number[]>([]);
  const active = useRef<AbortController | null>(null);

  useEffect(() => () => active.current?.abort(), []);

  const refresh = async () => {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setSnapshot(null);
    setReviewedOrders([]);
    setMessage('جارٍ قراءة ملخص AI-7 المحلي...');
    try {
      const response = await fetch('/api/local-ai7/summary', {
        method: 'GET', credentials: 'omit', cache: 'no-store',
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('local_snapshot_not_available');
      const data: unknown = await response.json();
      if (!data || typeof data !== 'object') throw new Error('invalid_snapshot');
      const checked = data as Snapshot;
      if (checked.source !== 'local_ai7_snapshot' || checked.read_only !== true
          || checked.mode !== 'local_advisory_only' || !Array.isArray(checked.stages)
          || checked.stages.length !== 7 || !checked.summary
          || !Array.isArray(checked.recommendations)) {
        throw new Error('invalid_snapshot');
      }
      if (!controller.signal.aborted) {
        setSnapshot(checked);
        setMessage('لقطة محلية محمّلة للقراءة فقط. ليست مراقبة حية أو جاهزية إنتاج.');
      }
    } catch {
      if (!controller.signal.aborted) {
        setMessage('المحرك المحلي غير متصل أو لم يُفعّل الربط. لا توجد نتائج مؤكدة للعرض.');
      }
    } finally {
      if (active.current === controller) {
        active.current = null;
        if (!controller.signal.aborted) setLoading(false);
      }
    }
  };

  return (
    <section aria-label="ملخص AI-7 المحلي" className="rounded-2xl border border-indigo-800/70 bg-slate-900 p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h3 className="flex items-center gap-2 text-base font-bold text-white">
            <Activity className="h-5 w-5 text-indigo-400" />
            محرك AI-7 — ملخص محلي قابل للتحقق
          </h3>
          <p className="text-xs text-slate-400">بيانات تحليلية من المحرك المحلي عند الطلب، ولا تُستخدم لتنفيذ إصلاح أو نشر.</p>
        </div>
        <button type="button" disabled={loading} onClick={() => { void refresh(); }}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-600 bg-indigo-950/60 px-3 py-2 text-sm font-semibold text-indigo-200 hover:bg-indigo-900 disabled:opacity-50">
          <RefreshCw className="h-4 w-4" />
          {loading ? 'جاري التحميل' : 'قراءة المحرك المحلي'}
        </button>
      </div>
      <p role="status" aria-live="polite" className="text-sm text-amber-200">{message}</p>
      {snapshot && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {([
              ['الأحداث المعالجة', snapshot.summary.event_count],
              ['مجموعات السجلات', snapshot.summary.log_cluster_count],
              ['مرشحات الشذوذ', snapshot.summary.anomaly_candidate_count],
              ['التوصيات الاستشارية', snapshot.summary.recommendation_count],
            ] as const).map(([label, count]) => (
              <div key={label} className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-3">
                <p className="text-xs text-slate-400">{label}</p>
                <p className="mt-1 text-2xl font-bold tabular-nums text-white">{count}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
            {snapshot.stages.map(stage => (
              <div key={stage.id} className="rounded-lg border border-slate-700 bg-slate-950 p-3 text-center">
                <p className="font-bold text-indigo-300">{stage.id}</p>
                <p className="mt-1 break-words text-[11px] text-slate-400">{stage.status}</p>
                <p className="text-xs text-slate-400">عدد: {stage.count}</p>
              </div>
            ))}
          </div>
          <div className="space-y-3">
            <h4 className="font-bold text-indigo-200">
              توصيات AI-4 الاستشارية ({snapshot.recommendations.length} معروضة من أصل {snapshot.summary.recommendation_count})
            </h4>
            {snapshot.recommendations.length === 0 && (
              <p className="text-xs text-slate-400">لا توجد توصيات معروفة في اللقطة الحالية. هذا لا يثبت خلو النظام من الأعطال.</p>
            )}
            {snapshot.recommendations.map(item => (
              <article key={item.review_order} className="rounded-xl border border-slate-700 bg-slate-950 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h5 className="font-bold text-white">
                    {item.review_order}. {CAUSES[item.cause_id]}
                  </h5>
                  <span className="rounded-md border border-amber-800 bg-amber-950/40 px-2 py-1 text-xs text-amber-200">
                    POSSIBLE — إشارة {item.heuristic_signal === 'medium' ? 'متوسطة' : 'منخفضة'} غير معايرة
                  </span>
                </div>
                <p className="text-xs text-slate-300">
                  علامات الدليل: {item.evidence_markers.join(' · ')} · الأحداث المرتبطة: {item.event_count}
                </p>
                <p className="text-xs text-slate-300">
                  فحص للقراءة فقط: {READ_ONLY_GUIDANCE[item.cause_id]}
                </p>
                <label className="flex items-start gap-2 text-xs text-slate-300">
                  <input type="checkbox" checked={reviewedOrders.includes(item.review_order)}
                    onChange={event => setReviewedOrders(previous =>
                      event.target.checked
                        ? [...previous, item.review_order]
                        : previous.filter(order => order !== item.review_order))}
                    className="mt-0.5 accent-indigo-500" />
                  اطلعت على التوصية والأدلة (تأكيد قراءة محلي فقط؛ ليس موافقة على أي تغيير).
                </label>
                <p className="text-xs text-amber-200">
                  يلزم اعتماد بشري منفصل قبل أي تغيير. التنفيذ التلقائي معطل.
                </p>
              </article>
            ))}
          </div>
          <p className="flex items-center gap-2 text-xs text-slate-400">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            المخرجات منقّحة للقراءة فقط. لا توجد بيانات سجلات خام أو تنفيذ تلقائي.
          </p>
        </>
      )}
    </section>
  );
}
