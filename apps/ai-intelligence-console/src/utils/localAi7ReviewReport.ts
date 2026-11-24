import { parseLocalAi7Snapshot, type LocalAi7Snapshot } from './localAi7Snapshot';
import { LOCAL_AI7_CAUSES, LOCAL_AI7_READ_ONLY_GUIDANCE } from './localAi7Catalog';

function isCanonicalUtcTimestamp(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return false;
  const parsed = new Date(value);
  return Number.isFinite(parsed.valueOf()) && parsed.toISOString() === value;
}

/** Build a bounded, local review file from the validated AI-7 contract only. */
export function buildLocalAi7ReviewReport(
  value: unknown,
  exportedAt: string,
  reviewedOrders: unknown = [],
): string | null {
  const snapshot = parseLocalAi7Snapshot(value);
  if (!snapshot || typeof exportedAt !== 'string' || !isCanonicalUtcTimestamp(exportedAt)) return null;
  if (!Array.isArray(reviewedOrders)) return null;
  const visibleOrders = new Set(snapshot.recommendations.map(item => item.review_order));
  const acknowledgedOrders = new Set<number>();
  for (const order of reviewedOrders) {
    if (!Number.isSafeInteger(order) || !visibleOrders.has(order) || acknowledgedOrders.has(order)) return null;
    acknowledgedOrders.add(order);
  }

  const lines = [
    '# تقرير مراجعة محلي — AI-7',
    '',
    '- الحالة: لقطة محلية استشارية للقراءة فقط؛ ليست مراقبة حية أو جاهزية إنتاج.',
    `- وقت إنشاء هذا الملف (UTC): ${exportedAt}`,
    '- هذا وقت التصدير، وليس وقت التقاط اللقطة أو آخر تحديث للمصدر.',
    '- لا يحتوي التقرير على سجلات خام أو نصوص حوادث أو بيانات اعتماد.',
    '',
    '## الملخص',
    '',
    `- الأحداث المعالجة: ${snapshot.summary.event_count}`,
    `- مجموعات السجلات: ${snapshot.summary.log_cluster_count}`,
    `- مرشحات الشذوذ: ${snapshot.summary.anomaly_candidate_count}`,
    `- التوصيات المعروفة: ${snapshot.summary.recommendation_count}`,
    `- التوصيات المفصلة هنا: ${snapshot.recommendations.length} من أصل ${snapshot.summary.recommendation_count}`,
  ];

  if (snapshot.recommendations.length === 0) {
    lines.push('', 'لا توجد توصيات معروفة في هذه اللقطة. هذا لا يثبت خلو النظام من الأعطال.');
  } else {
    lines.push('', '## توصيات للمراجعة البشرية');
    for (const item of snapshot.recommendations) {
      lines.push(
        '',
        `### ${item.review_order}. ${LOCAL_AI7_CAUSES[item.cause_id]}`,
        '',
        `- التصنيف: ${item.classification} — فرضية ممكنة وليست سببًا مؤكدًا.`,
        `- الإشارة: ${item.heuristic_signal} — مقياس استدلالي غير معاير.`,
        `- عدد الأحداث المرتبطة: ${item.event_count}`,
        `- علامات الدليل المعروفة: ${item.evidence_markers.join('، ')}`,
        `- فحص قراءة فقط: ${LOCAL_AI7_READ_ONLY_GUIDANCE[item.cause_id]}`,
        `- إقرار الاطلاع المحلي عند التصدير: ${acknowledgedOrders.has(item.review_order) ? 'محدد في الواجهة' : 'غير محدد في الواجهة'}`,
        '- يتطلب أي تغيير اعتمادًا بشريًا منفصلًا.',
        '- التنفيذ التلقائي: معطل.',
      );
    }
  }

  lines.push(
    '',
    '## حدود الاستخدام',
    '',
    '- هذه النتائج استشارية ولا تثبت السبب الجذري أو جودة تشغيلية معايرة.',
    '- حالة مربعات الاطلاع تعكس الواجهة وقت التصدير فقط؛ لا تسجل هوية المراجع ولا تعد موافقة أو اعتمادًا أو تفويضًا.',
    '- التصدير لا ينشئ موافقة أو تذكرة، ولا يتصل بخدمة خارجية، ولا ينفذ إجراءً.',
    '- تحقق من الأدلة الحالية يدويًا قبل اتخاذ أي قرار.',
    '',
  );
  return lines.join('\n');
}
