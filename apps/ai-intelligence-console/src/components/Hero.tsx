import React from 'react';
import { ArrowLeft, Wand2, Terminal, Code, Cpu } from 'lucide-react';

interface HeroProps {
  onExploreClick: () => void;
  onTryPromptClick: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onExploreClick, onTryPromptClick }) => {
  return (
    <section className="relative pt-12 pb-16 md:pt-16 md:pb-24 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Top unboxed kicker */}
        <div className="flex items-center gap-2 text-xs font-medium text-indigo-600 dark:text-indigo-400 mb-4">
          <span>دليل الاستخدام الشامل</span>
          <span aria-hidden="true">·</span>
          <span>Google AI Studio Build</span>
          <span aria-hidden="true">·</span>
          <span>من الفكرة إلى التطبيق الحي</span>
        </div>

        {/* Main Hero Headline */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-7 space-y-6">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight [text-wrap:balance]">
              علمني كيف استخدمك؟
              <span className="block text-indigo-600 dark:text-indigo-400 mt-2">
                أنا مهندس برمجياتك الذكي، جاهز لبناء أي تطبيق في مخيلتك!
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed [text-wrap:balance]">
              أنت لست بحاجة لكتابة الكود أو إعداد خوادم معقدة. كل ما عليك فعله هو التحدث معي باللغة الطبيعية (عربي أو إنجليزي)، ووصف التطبيق أو الميزة التي ترغب بها. أقوم فوراً بهندسة الكود وبنائه وتشغيله حياً أمامك في نافذة المعاينة.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={onTryPromptClick}
                className="px-6 py-3 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-500 rounded-xl transition-all shadow-md hover:shadow-lg flex items-center gap-2"
              >
                <span>جرب مولّد الأوامر التفاعلي</span>
                <ArrowLeft className="w-4 h-4" />
              </button>
              <button
                onClick={onExploreClick}
                className="px-6 py-3 text-sm font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 rounded-xl transition-colors"
              >
                شاهد نماذج حية لما يمكنني بناؤه
              </button>
            </div>

            {/* Quick trust metrics */}
            <div className="pt-4 flex flex-wrap items-center gap-6 text-xs text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1.5 font-medium">
                <Code className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                تطبيقات React وTailwind حقيقية
              </span>
              <span aria-hidden="true">·</span>
              <span className="flex items-center gap-1.5 font-medium">
                <Wand2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                معاينة حية فورية وتفاعلية
              </span>
              <span aria-hidden="true">·</span>
              <span className="flex items-center gap-1.5 font-medium">
                <Cpu className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                دعم دمج Gemini وقواعد البيانات
              </span>
            </div>
          </div>

          {/* Interactive Hero Side Card */}
          <div className="lg:col-span-5">
            <div className="bg-slate-900 text-slate-100 rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-indigo-400" />
                  <span className="font-semibold text-slate-300">كيف تجري المحادثة معي؟</span>
                </div>
                <span>نمط التوجيه المباشر</span>
              </div>

              {/* Chat snippet demo */}
              <div className="space-y-3 text-xs leading-relaxed">
                <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60">
                  <p className="font-bold text-indigo-300 mb-1">أنت تسأل ببساطة:</p>
                  <p className="text-slate-200">
                    "ابنِ لي تطبيقاً لإدارة المصروفات اليومية مع رسم بياني للإنفاق الشهري وحفظ البيانات في المتصفح."
                  </p>
                </div>

                <div className="bg-indigo-950/60 p-3 rounded-lg border border-indigo-800/50">
                  <p className="font-bold text-indigo-300 mb-1">أنا أقوم بـ:</p>
                  <ul className="space-y-1.5 text-slate-300">
                    <li className="flex items-start gap-1.5">
                      <span className="text-indigo-400 font-bold">✓</span>
                      <span>هندسة المكونات (حقول الإدخال، الجداول، الرسوم البيانية).</span>
                    </li>
                    <li className="flex items-start gap-1.5">
                      <span className="text-indigo-400 font-bold">✓</span>
                      <span>كتابة كود TypeScript نظيف مع تخزين دائم LocalStorage.</span>
                    </li>
                    <li className="flex items-start gap-1.5">
                      <span className="text-indigo-400 font-bold">✓</span>
                      <span>تشغيل التطبيق فوراً لترى واجهة حية يمكنك استخدامها فوراً!</span>
                    </li>
                  </ul>
                </div>
              </div>

              <div className="pt-2 text-center">
                <p className="text-xs text-slate-400">
                  ثم يمكنك الرد علي: <span className="text-slate-200">"أضف زراً لتصدير تقرير PDF"</span> وسأقوم بتنفيذه مباشرة!
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
