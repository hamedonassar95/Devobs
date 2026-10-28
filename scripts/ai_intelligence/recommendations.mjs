import { createRecommendationFeedbackKey } from './feedback_learning.mjs';

const MAX_CLUSTERS = 250;
const MAX_HYPOTHESES_PER_CLUSTER = 8;
const MAX_RECOMMENDATIONS = MAX_CLUSTERS * MAX_HYPOTHESES_PER_CLUSTER;
const FINGERPRINT_PATTERN = /^sha256:[0-9a-f]{24}$/;
const MARKER_PATTERN = /^[A-Za-z0-9_]{1,64}$/;

const RUNBOOKS = Object.freeze({
  timeout: {
    title: 'مهلة عملية أو اعتماد',
    markers: ['ETIMEDOUT', 'timeout', 'timed_out'],
    checks: [
      'راجع أول خطوة متعثرة وتوقيتها في سجل التشغيل المصرح به.',
      'قارن مدة الخطوة بحدودها الموثقة وحالة الاعتماد وقت الحادث.',
    ],
    possible_change: 'بعد تأكيد السبب، قيّم تعديل المهلة أو سياسة إعادة المحاولة ضمن حدود موثقة.',
  },
  connection: {
    title: 'اتصال مرفوض أو مقطوع',
    markers: ['ECONNREFUSED', 'ECONNRESET'],
    checks: [
      'قارن وقت الخطأ بحالة الخدمة المعتمدة وسجل الاتصال المتاح.',
      'تحقق قراءةً من اسم الوجهة والمنفذ الموثقين دون إرسال طلب جديد.',
    ],
    possible_change: 'بعد تأكيد السبب، قيّم مسار الاتصال أو إعداد إعادة المحاولة؛ لا تغيّر قواعد الشبكة تلقائيًا.',
  },
  dns: {
    title: 'حل اسم المضيف',
    markers: ['ENOTFOUND', 'EAI_AGAIN'],
    checks: [
      'راجع قيمة اسم المضيف من مصدر الإعداد المصرح به دون كشف قيم سرية.',
      'قارن سجل الخطأ بتوقيت فشل حل الاسم؛ لا تنفّذ تغييرات DNS.',
    ],
    possible_change: 'بعد تأكيد خطأ الاسم، اقترح تصحيح الإعداد عبر مسار التغيير المعتاد.',
  },
  permission: {
    title: 'صلاحية مورد',
    markers: ['EACCES', 'permission_denied'],
    checks: [
      'راجع هوية العملية والصلاحيات الحالية قراءةً فقط.',
      'تحقق من المورد المحدد دون طباعة اعتماد أو توسيع صلاحيات.',
    ],
    possible_change: 'بعد تأكيد النقص، اقترح أقل صلاحية لازمة للمورد المحدد؛ لا توسّعها آليًا.',
  },
  dependency: {
    title: 'حل وحدة أو اعتماد',
    markers: ['module_not_found', 'cannot_find_module'],
    checks: [
      'قارن ملف القفل واسم الوحدة ومسار الاستيراد في SHA المتأثر.',
      'تحقق من نتيجة التثبيت/البناء الموجودة دون إعادة تشغيل workflow.',
    ],
    possible_change: 'بعد تأكيد عدم التطابق، اقترح تحديثًا محدودًا لملف القفل أو مسار الاستيراد للمراجعة.',
  },
  memory: {
    title: 'حد الذاكرة',
    markers: ['out_of_memory', 'heap_limit'],
    checks: [
      'قارن السجل مع قياسات الذاكرة وحد التشغيل المتاحة لنفس الفترة.',
      'تحقق من حجم الإدخال ومعدل النمو قبل اقتراح تغيير الحد.',
    ],
    possible_change: 'بعد تأكيد ضغط الذاكرة، قيّم تحسين الاستهلاك قبل أي رفع لحدود الموارد.',
  },
});

export class RecommendationError extends Error {
  constructor(code) {
    super(code);
    this.name = 'RecommendationError';
    this.code = code;
  }
}

function reject(code) {
  throw new RecommendationError(code);
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function validateHypothesis(hypothesis) {
  if (!isPlainObject(hypothesis)
    || hypothesis.classification !== 'POSSIBLE'
    || typeof hypothesis.id !== 'string'
    || !/^[a-z][a-z0-9_]{0,39}$/.test(hypothesis.id)
    || !['low', 'medium'].includes(hypothesis.heuristic_confidence)
    || !Array.isArray(hypothesis.evidence_markers)
    || hypothesis.evidence_markers.length === 0
    || hypothesis.evidence_markers.length > 8
    || hypothesis.evidence_markers.some(marker => typeof marker !== 'string' || !MARKER_PATTERN.test(marker))) {
    reject('invalid_hypothesis');
  }
}

/**
 * Maps bounded AI-3 POSSIBLE hypotheses to fixed, local runbook suggestions.
 * The result contains no source log text and never executes a recommendation.
 */
export function recommendFromIncidentAnalysis(analysis) {
  if (!isPlainObject(analysis) || !Array.isArray(analysis.clusters)) reject('invalid_analysis');
  if (analysis.clusters.length > MAX_CLUSTERS) reject('too_many_clusters');

  const recommendations = [];
  let unmappedHypothesisCount = 0;
  const seen = new Map();

  for (const cluster of analysis.clusters) {
    if (!isPlainObject(cluster)
      || typeof cluster.fingerprint !== 'string'
      || !FINGERPRINT_PATTERN.test(cluster.fingerprint)
      || !Number.isSafeInteger(cluster.count)
      || cluster.count < 1
      || cluster.count > MAX_CLUSTERS
      || !Array.isArray(cluster.hypotheses)
      || cluster.hypotheses.length > MAX_HYPOTHESES_PER_CLUSTER) {
      reject('invalid_cluster');
    }

    for (const hypothesis of cluster.hypotheses) {
      validateHypothesis(hypothesis);
      const runbook = RUNBOOKS[hypothesis.id];
      if (!runbook) {
        unmappedHypothesisCount++;
        continue;
      }

      const evidenceMarkers = [...new Set(hypothesis.evidence_markers.filter(marker => runbook.markers.includes(marker)))];
      if (evidenceMarkers.length === 0) reject('invalid_hypothesis_evidence');
      const key = `${cluster.fingerprint}:${hypothesis.id}`;
      const existing = seen.get(key);
      if (existing) {
        existing.evidence_markers = [...new Set([...existing.evidence_markers, ...evidenceMarkers])].sort();
        if (hypothesis.heuristic_confidence === 'medium') existing.heuristic_signal = 'medium';
        continue;
      }
      if (recommendations.length >= MAX_RECOMMENDATIONS) reject('too_many_recommendations');

      const recommendation = {
        review_order: recommendations.length + 1,
        cluster_fingerprint: cluster.fingerprint,
        feedback_key: createRecommendationFeedbackKey(cluster.fingerprint, hypothesis.id),
        event_count: cluster.count,
        cause_id: hypothesis.id,
        classification: 'POSSIBLE',
        heuristic_signal: hypothesis.heuristic_confidence,
        evidence_markers: evidenceMarkers.sort(),
        runbook_title: runbook.title,
        read_only_checks: [...runbook.checks],
        possible_change_after_confirmation: runbook.possible_change,
        requires_human_approval: true,
        automatic_execution: false,
      };
      recommendations.push(recommendation);
      seen.set(key, recommendation);
    }
  }

  return {
    schema_version: 1,
    mode: 'suggestion_only',
    source: 'local_ai3_hypotheses',
    status: recommendations.length > 0 ? 'SUGGESTIONS_AVAILABLE' : 'NO_KNOWN_SUGGESTIONS',
    review_order_note: 'Order is deterministic display order, not severity, probability, or root-cause certainty.',
    unmapped_hypothesis_count: unmappedHypothesisCount,
    requires_human_approval: true,
    automatic_execution: false,
    recommendations,
  };
}
