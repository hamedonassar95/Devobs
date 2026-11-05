import React, { useState } from 'react';
import { Lightbulb, ArrowLeft, Copy, Check, Terminal, Cpu } from 'lucide-react';

export const IdeaSimulator: React.FC = () => {
  const [userInput, setUserInput] = useState<string>('تطبيق لتنظيم ميزانية مصاريف السفر وتقسيم الفواتير بين الأصدقاء');
  const [isAnalyzed, setIsAnalyzed] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  const quickIdeas = [
    'تطبيق لتنظيم ميزانية مصاريف السفر وتقسيم الفواتير بين الأصدقاء',
    'حاسبة زكاة وصدقات ذكية مع تقارير وتذكير سنوي',
    'منصة إدارة حجوزات مواعيد لعيادة طبية أو صالون تجميل',
    'لعبة تخمين أمثال شعبية عربية مع مستويات ونقاط',
  ];

  // Dynamic analysis simulation based on keywords in input
  const getDeconstruction = () => {
    const text = userInput.toLowerCase();
    
    let isFinance = text.includes('ميزانية') || text.includes('مصاريف') || text.includes('زكاة') || text.includes('فواتير') || text.includes('مال');
    let isGame = text.includes('لعبة') || text.includes('تخمين') || text.includes('نقاط') || text.includes('مستويات');
    let isBooking = text.includes('حجز') || text.includes('مواعيد') || text.includes('عيادة') || text.includes('صالون');

    if (isGame) {
      return {
        type: 'لعبة تفاعلية (Interactive Web Game)',
        components: ['GameBoard (رقعة اللعب)', 'ScoreTracker (عداد النقاط والمحاولات)', 'WordDeck (بنك الأسئلة والأمثال)', 'ResultModal (نافذة إعلان الفائز)'],
        dataModel: '{ currentScore: number, level: number, completedWords: string[], timerSeconds: number }',
        features: ['مؤقت تنازلي لكل جولة', 'نظام تلميحات ذكي', 'حفظ أعلى نتيجة High-Score في LocalStorage', 'مؤثرات بصرية احتفالية عند الفوز'],
        prompt: `اصنع لي ${userInput}.\nالمواصفات المطلوبة:\n- رقعة لعب تفاعلية مع أسئلة وأمثال عربية ومستويات متدرجة الصعوبة.\n- مؤقت تنازلي، عداد نقاط ومحاولات، ونظام تلميحات.\n- حفظ أعلى نتيجة محلياً.\n- تصميم عصري سريع ومتوافق مع الهواتف والشاشات الكبيرة باللغة العربية.`
      };
    } else if (isBooking) {
      return {
        type: 'نظام إدارة حجوزات ومواعيد (Booking & Scheduling)',
        components: ['CalendarView (تقويم الأيام والساعات)', 'ServiceSelector (قائمة الخدمات والأسعار)', 'ClientForm (نموذج بيانات العميل)', 'BookingsTable (جدول إدارة الحجوزات)'],
        dataModel: '{ appointments: [{ id, clientName, phone, service, date, timeSlot, status }] }',
        features: ['اختيار التاريخ والوقت المتاح بمرونة', 'تأكيد الحجز الفوري وإصدار تذكرة مرقمة', 'فلترة الحجوزات حسب اليوم وحالة الحضور', 'حفظ سجل الحجوزات محلياً'],
        prompt: `اصنع لي ${userInput}.\nالمواصفات المطلوبة:\n- واجهة حجز مواعيد مرئية مع اختيار الخدمات والتاريخ والساعات المتاحة.\n- نموذج لتسجيل بيانات العميل مع إصدار بطاقة تأكيد حجز.\n- لوحة تحكم مصغرة للإدارة لمشاهدة جميع الحجوزات وتغيير حالتها (مؤكد، ملغى، مكتمل).\n- تصميم عربي متقن مع حفظ البيانات في المتصفح.`
      };
    } else {
      // Default to Finance / Productivity
      return {
        type: 'أداة إنتاجية وحاسبة مالية تفاعلية (Productivity & Calculator)',
        components: ['ExpenseInput (نموذج إضافة العمليات)', 'SplitSummary (موجز تقسيم الحصص بالأشخاص)', 'AnalyticsChart (رسم بياني لتوزيع المصاريف)', 'ExportReport (زر تصدير التقرير)'],
        dataModel: '{ members: string[], expenses: [{ id, payer, amount, category, splitBetween, date }] }',
        features: ['إضافة أسماء المشاركين وتحديد من دفع وماذا دفع', 'حساب صافي المبالغ المستحقة لكل شخص بدقة', 'رسم بياني لتوزيع النفقات حسب الفئة', 'حفظ تلقائي لكافة العمليات في المتصفح'],
        prompt: `اصنع لي ${userInput}.\nالمواصفات المطلوبة:\n- إضافة أسماء المشاركين والمصاريف مع تحديد الفئة (سكن، طعام، تنقلات).\n- حساب فوري وصافٍ للمستحقات بين الأصدقاء مع بيان من يدفع لمن.\n- رسم بياني لتوزيع النفقات وحفظ البيانات في LocalStorage.\n- واجهة عربية أنيقة وسهلة الاستخدام بالوضع الداكن والفاتح.`
      };
    }
  };

  const deconstruction = getDeconstruction();

  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(deconstruction.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <section id="simulator" className="py-16 md:py-20 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-2">
            مختبر التفكير الهندسي
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-3">
            مختبر تفكيك الأفكار وتحليلها البرمجي
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            اكتب أي فكرة تدور في ذهنك، واشهد كيف أقوم بهندستها وتفكيكها إلى مكونات وبيانات وأمر تنفيذي جاهز للبدء!
          </p>
        </div>

        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-sm">
          {/* Input field */}
          <div className="space-y-3 mb-6">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              ما هي فكرة التطبيق التي ترغب ببنائها؟
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={userInput}
                onChange={(e) => {
                  setUserInput(e.target.value);
                  setIsAnalyzed(true);
                }}
                placeholder="اكتب فكرتك هنا..."
                className="flex-1 px-4 py-3 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                onClick={() => setIsAnalyzed(true)}
                className="px-6 py-3 text-xs sm:text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors whitespace-nowrap shadow-sm flex items-center justify-center gap-2"
              >
                <Cpu className="w-4 h-4" />
                <span>حلل الفكرة هندسياً</span>
              </button>
            </div>

            {/* Quick Suggestions */}
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
              <span className="text-slate-400 font-medium">أفكار مقترحة للتجربة:</span>
              {quickIdeas.map((idea, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setUserInput(idea);
                    setIsAnalyzed(true);
                  }}
                  className="px-2.5 py-1 text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                >
                  {idea}
                </button>
              ))}
            </div>
          </div>

          {/* Analysis Result */}
          {isAnalyzed && (
            <div className="pt-6 border-t border-slate-100 dark:border-slate-800 space-y-6">
              <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 dark:text-indigo-400">
                <Lightbulb className="w-4 h-4" />
                <span>التحليل الهندسي الأولي لفكرتك: {deconstruction.type}</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Components */}
                <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-2">
                    المكونات الرئيسية (Components):
                  </h4>
                  <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                    {deconstruction.components.map((c, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-indigo-500 font-bold">›</span>
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* State & Data Model */}
                <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-2">
                    بنية البيانات والتخزين (Data Model):
                  </h4>
                  <div className="bg-white dark:bg-slate-900 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 font-mono text-[11px] text-indigo-600 dark:text-indigo-400 break-all leading-normal">
                    {deconstruction.dataModel}
                  </div>
                </div>

                {/* Features */}
                <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-2">
                    الميزات التفاعلية البارزة:
                  </h4>
                  <ul className="space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
                    {deconstruction.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-500 font-bold">✓</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Ready to send Prompt */}
              <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 text-slate-100 space-y-3">
                <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-800">
                  <span className="flex items-center gap-1.5 font-bold text-indigo-300">
                    <Terminal className="w-3.5 h-3.5" />
                    الطلب المقترح الموجه لمهندس الذكاء الاصطناعي:
                  </span>
                  <span className="text-slate-400 text-[11px]">يمكنك إرساله لي الآن في الدردشة</span>
                </div>

                <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-mono">
                  {deconstruction.prompt}
                </p>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={handleCopyPrompt}
                    className="py-2 px-4 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-2 shadow-sm"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-300" />
                        <span>تم نسخ الطلب!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>نسخ الطلب ولصقه في الشات</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
