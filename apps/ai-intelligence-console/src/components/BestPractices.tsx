import React, { useState } from 'react';
import { PROMPT_COMPARISONS } from '../data/guidelines';
import { Check, X, HelpCircle, Layers, Sliders, ShieldCheck } from 'lucide-react';

export const BestPractices: React.FC = () => {
  const [activeTab, setActiveTab] = useState<number>(0);

  const goldenRules = [
    {
      title: 'كن محدداً في نوع التطبيق',
      desc: 'بدل وصف غامض، اذكر: "لوحة تحكم"، "أداة إنتاجية"، "لعبة بازل"، أو "متجر". هذا يوجهني مباشرة لاختيار البنية البرمجية الأنسب.',
      icon: <Layers className="w-4 h-4 text-indigo-500" />,
    },
    {
      title: 'حدد الميزات والوظائف التفاعلية',
      desc: 'اذكر ما تود أن يفعله المستخدم بالتحديد: مثلاً "فرز حسب السعر"، "حفظ في LocalStorage"، "زر تنزيل ملف CSV".',
      icon: <Sliders className="w-4 h-4 text-emerald-500" />,
    },
    {
      title: 'اعتمد التدرج: ابنِ الأساس ثم وسّع',
      desc: 'يمكنك البدء بالواجهة الرئيسية وميزاتها، ثم في ردك التالي تطلب مني: "أضف صفحة تفاصيل" أو "اربط مع Gemini AI".',
      icon: <ShieldCheck className="w-4 h-4 text-violet-500" />,
    },
    {
      title: 'في التعديل: وجّهني للعنصر المحدد',
      desc: 'عندما تطلب تعديلاً، حدد الجزء بدقة: "غيّر لون الأزرار الرئيسية للون الزمردي"، "أضف زر حذف بجانب كل مهمة".',
      icon: <HelpCircle className="w-4 h-4 text-amber-500" />,
    },
  ];

  return (
    <section id="guidelines" className="py-16 md:py-20 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-2">
            دليل التوجيه الفعّال
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-3">
            القواعد الذهبية للحصول على أفضل النتائج
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            أمثلة واقعية توضح الفرق بين الطلب العادي والطلب الهندسي الاحترافي، وكيف تتحدث معي لتحصل على تطبيق مذهل فوراً.
          </p>
        </div>

        {/* 4 Golden Rules Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
          {goldenRules.map((rule, idx) => (
            <div
              key={idx}
              className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm"
            >
              <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 w-fit mb-3">
                {rule.icon}
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1.5">
                {rule.title}
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {rule.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Real Comparisons (Do's & Don'ts) */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              مقارنات حية: "بدل أن تقول..." مقابل "الأفضل أن تقول..."
            </h3>
            {/* Category tabs */}
            <div className="flex flex-wrap gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
              {PROMPT_COMPARISONS.map((comp, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveTab(idx)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap ${
                    activeTab === idx
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  {comp.category}
                </button>
              ))}
            </div>
          </div>

          {PROMPT_COMPARISONS[activeTab] && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Bad Example */}
                <div className="bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/40 rounded-xl p-5">
                  <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 text-xs font-bold mb-2.5">
                    <div className="w-5 h-5 rounded-full bg-rose-200 dark:bg-rose-900 flex items-center justify-center">
                      <X className="w-3 h-3 text-rose-700 dark:text-rose-300" />
                    </div>
                    <span>صيغة عامة غير واضحة (قد تؤدي لنتائج عشوائية):</span>
                  </div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-900/80 p-3 rounded-lg border border-rose-200/60 dark:border-rose-900/40">
                    "{PROMPT_COMPARISONS[activeTab].bad}"
                  </p>
                </div>

                {/* Good Example */}
                <div className="bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 rounded-xl p-5">
                  <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 text-xs font-bold mb-2.5">
                    <div className="w-5 h-5 rounded-full bg-emerald-200 dark:bg-emerald-900 flex items-center justify-center">
                      <Check className="w-3 h-3 text-emerald-700 dark:text-emerald-300" />
                    </div>
                    <span>صيغة دقيقة وهندسية (تمنحك نتيجة مثالية ومباشرة):</span>
                  </div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-900/80 p-3 rounded-lg border border-emerald-200/60 dark:border-emerald-900/40">
                    "{PROMPT_COMPARISONS[activeTab].good}"
                  </p>
                </div>
              </div>

              {/* Rationale explanation */}
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                <span className="font-bold text-slate-900 dark:text-white">لماذا هذا مهم؟ </span>
                {PROMPT_COMPARISONS[activeTab].why}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
