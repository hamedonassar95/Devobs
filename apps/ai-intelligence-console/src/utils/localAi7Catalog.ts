import type { LocalAi7Recommendation } from './localAi7Snapshot';

type CauseId = LocalAi7Recommendation['cause_id'];

export const LOCAL_AI7_CAUSES: Readonly<Record<CauseId, string>> = {
  timeout: 'مهلة عملية أو اعتماد',
  connection: 'اتصال مرفوض أو مقطوع',
  dns: 'حل اسم المضيف',
  permission: 'صلاحية مورد',
  dependency: 'حل وحدة أو اعتماد',
  memory: 'حد الذاكرة',
};

export const LOCAL_AI7_READ_ONLY_GUIDANCE: Readonly<Record<CauseId, string>> = {
  timeout: 'راجع توقيت أول خطوة متعثرة وحدود المهلة المسجلة، دون تعديل التشغيل.',
  connection: 'قارن وقت الخطأ بحالة الخدمة وسجل الاتصال المصرح به، دون طلب تشغيل جديد.',
  dns: 'راجع اسم الوجهة من الإعدادات المصرح بها دون إظهار أسرار أو تغيير DNS.',
  permission: 'راجع هوية العملية وصلاحيات المورد قراءةً فقط دون توسيعها.',
  dependency: 'قارن ملف القفل ومسار الاستيراد في SHA المتأثر دون إعادة النشر.',
  memory: 'قارن قياسات الذاكرة وحجم المدخلات قبل اقتراح أي تغيير للموارد.',
};
