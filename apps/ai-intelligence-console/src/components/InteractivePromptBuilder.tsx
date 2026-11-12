import React, { useState } from 'react';
import { Sparkles, Copy, Check, RotateCcw, Send } from 'lucide-react';

interface InteractivePromptBuilderProps {
  initialPrompt?: string;
  onSendToChatHint: () => void;
}

export const InteractivePromptBuilder: React.FC<InteractivePromptBuilderProps> = ({
  initialPrompt,
  onSendToChatHint,
}) => {
  const [appType, setAppType] = useState<string>('productivity');
  const [customIdea, setCustomIdea] = useState<string>('');
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([
    'storage',
    'darkmode',
    'search',
  ]);
  const [designStyle, setDesignStyle] = useState<string>('minimal');
  const [languageMode, setLanguageMode] = useState<string>('ar-rtl');
  const [copied, setCopied] = useState<boolean>(false);

  const appTypes = [
    { id: 'productivity', label: 'أداة إنتاجية وإدارة مهام', defaultIdea: 'تطبيق لإدارة العادات والمشاريع اليومية' },
    { id: 'dashboard', label: 'لوحة تحكم إدارية ومبيعات', defaultIdea: 'لوحة تحكم لمتابعة العملاء والأرباح' },
    { id: 'ai-tool', label: 'أداة ذكاء اصطناعي (Gemini)', defaultIdea: 'مساعد ذكي لكتابة وتلخيص المحتوى' },
    { id: 'ecommerce', label: 'متجر إلكتروني وسلة تسوق', defaultIdea: 'متجر لبيع المنتجات الرقمية أو العطور' },
    { id: 'game', label: 'لعبة تفاعلية وبازل', defaultIdea: 'لعبة تخمين كلمات وألغاز ذهنية باللغة العربية' },
    { id: 'educational', label: 'أداة تعليمية أو محاكاة حاسوبية', defaultIdea: 'محاكي تفاعلي لحساب الفائدة أو التخطيط المالي' },
  ];

  const availableFeatures = [
    { id: 'storage', label: 'حفظ تلقائي للبيانات في المتصفح (LocalStorage)' },
    { id: 'darkmode', label: 'تبديل سلس بين الوضع الداكن والنهاري' },
    { id: 'search', label: 'شريط بحث وفلاتر تصفية لحظية' },
    { id: 'charts', label: 'رسوم بيانية ومخططات إحصائية تفاعلية' },
    { id: 'export', label: 'تصدير البيانات بصيغة CSV أو تنزيل تقارير' },
    { id: 'motion', label: 'تأثيرات حركية ناعمة وانتقالات بصرية' },
    { id: 'gemini', label: 'دمج نموذج Gemini للذكاء الاصطناعي' },
  ];

  const designStyles = [
    { id: 'minimal', label: 'عصري هادئ (Minimalist Modern)' },
    { id: 'tech-dark', label: 'داكن احترافي (High-End Dark Tech)' },
    { id: 'warm', label: 'أنيق دافئ (Warm & Elegant Editorial)' },
    { id: 'vibrant', label: 'حيوي وجذاب (Vibrant & Friendly)' },
  ];

  const toggleFeature = (featureId: string) => {
    if (selectedFeatures.includes(featureId)) {
      setSelectedFeatures(selectedFeatures.filter((f) => f !== featureId));
    } else {
      setSelectedFeatures([...selectedFeatures, featureId]);
    }
  };

  const getGeneratedPrompt = () => {
    const currentTypeObj = appTypes.find((t) => t.id === appType);
    const ideaText = customIdea.trim() || currentTypeObj?.defaultIdea || 'تطبيق ويب متكامل';

    const featureLabels = selectedFeatures
      .map((fId) => availableFeatures.find((f) => f.id === fId)?.label)
      .filter(Boolean);

    const styleLabel = designStyles.find((s) => s.id === designStyle)?.label;

    let prompt = `اصنع لي ${ideaText}.\n\nالمواصفات والميزات المطلوبة:\n`;
    featureLabels.forEach((label) => {
      prompt += `- ${label}\n`;
    });

    prompt += `- أسلوب التصميم: ${styleLabel}\n`;
    prompt +=
      languageMode === 'ar-rtl'
        ? '- الواجهة باللغة العربية بالكامل مع مراعاة اتجاه القراءة من اليمين لليسار (RTL) وخطوط عربية واضحة ومقروءة.'
        : '- دعم اللغتين العربية والإنجليزية مع زر للتبديل بينهما.';

    prompt += '\n\nيرجى بناء التطبيق كاملاً مع عناصر تفاعلية حقيقية تعمل بدون أي نواقص.';
    return prompt;
  };

  const handleCopyPrompt = () => {
    const text = getGeneratedPrompt();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleReset = () => {
    setAppType('productivity');
    setCustomIdea('');
    setSelectedFeatures(['storage', 'darkmode', 'search']);
    setDesignStyle('minimal');
    setLanguageMode('ar-rtl');
  };

  return (
    <section id="generator" className="py-16 md:py-20 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-2">
            الأداة التفاعلية العملية
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-3">
            مولّد الأوامر الاحترافي الذكي
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            حدد ما تريده ببضع نقرات، ودع المولّد يصيغ لك طلباً هندسياً دقيقاً يمكنك نسخه وإرساله لي مباشرة لبدء البناء!
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Controls Column */}
          <div className="lg:col-span-7 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 space-y-6 shadow-sm">
            {/* Step 1: App Type */}
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-2.5">
                1. اختر نوع التطبيق:
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {appTypes.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setAppType(type.id)}
                    className={`p-3 text-xs font-semibold rounded-xl border text-right transition-all ${
                      appType === type.id
                        ? 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-500 text-indigo-700 dark:text-indigo-300 font-bold'
                        : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Idea field */}
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                2. فكرتك المحددة (اختياري - يمكنك التعديل):
              </label>
              <input
                type="text"
                value={customIdea}
                onChange={(e) => setCustomIdea(e.target.value)}
                placeholder="مثال: تطبيق لإدارة مصاريف السفر وتقسيم الفواتير بين الأصدقاء"
                className="w-full px-3.5 py-2.5 text-xs sm:text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Step 3: Features */}
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-2.5">
                3. الميزات التقنية المرغوبة:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {availableFeatures.map((feat) => {
                  const isChecked = selectedFeatures.includes(feat.id);
                  return (
                    <button
                      key={feat.id}
                      onClick={() => toggleFeature(feat.id)}
                      className={`flex items-center gap-2.5 p-2.5 text-xs rounded-xl border text-right transition-colors ${
                        isChecked
                          ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-400 dark:border-indigo-600 text-indigo-900 dark:text-indigo-200'
                          : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }`}
                    >
                      <div
                        className={`w-4 h-4 rounded flex items-center justify-center border text-[10px] ${
                          isChecked
                            ? 'bg-indigo-600 text-white border-indigo-600 font-bold'
                            : 'border-slate-300 dark:border-slate-600'
                        }`}
                      >
                        {isChecked && '✓'}
                      </div>
                      <span className="truncate">{feat.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Step 4: Design Style & Language */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">
                  4. الطابع البصري والتصميم:
                </label>
                <div className="space-y-1.5">
                  {designStyles.map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setDesignStyle(style.id)}
                      className={`w-full p-2 text-xs rounded-lg border text-right transition-colors ${
                        designStyle === style.id
                          ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-500 text-indigo-700 dark:text-indigo-300 font-semibold'
                          : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }`}
                    >
                      {style.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">
                  5. لغة الواجهة والاتجاه:
                </label>
                <div className="space-y-1.5">
                  <button
                    onClick={() => setLanguageMode('ar-rtl')}
                    className={`w-full p-2 text-xs rounded-lg border text-right transition-colors ${
                      languageMode === 'ar-rtl'
                        ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-500 text-indigo-700 dark:text-indigo-300 font-semibold'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    عربي كامل (RTL) مع خطوط متناسقة
                  </button>
                  <button
                    onClick={() => setLanguageMode('bilingual')}
                    className={`w-full p-2 text-xs rounded-lg border text-right transition-colors ${
                      languageMode === 'bilingual'
                        ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-500 text-indigo-700 dark:text-indigo-300 font-semibold'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    ثنائي اللغة (عربي / إنجليزي مع تبديل)
                  </button>
                </div>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <button
                onClick={handleReset}
                className="text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-1.5 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>إعادة تعيين الخيارات الافتراضية</span>
              </button>
            </div>
          </div>

          {/* Generated Result Output Column */}
          <div className="lg:col-span-5 sticky top-20">
            <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6 text-slate-100 shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-bold text-slate-200">الطلب المكتمل الجاهز للإرسال</span>
                </div>
                <span className="text-[11px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-2 py-0.5 rounded-full">
                  جاهز للنسخ
                </span>
              </div>

              {/* Preformatted text display */}
              <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 text-xs leading-relaxed text-slate-300 font-mono whitespace-pre-wrap max-h-80 overflow-y-auto">
                {getGeneratedPrompt()}
              </div>

              {/* Action Buttons */}
              <div className="space-y-2 pt-2">
                <button
                  onClick={handleCopyPrompt}
                  className="w-full py-3 px-4 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center justify-center gap-2 shadow-sm"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-300" />
                      <span>تم نسخ الطلب بنجاح إلى الحافظة!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span>نسخ الطلب (Copy Prompt)</span>
                    </>
                  )}
                </button>

                <div className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/50 text-[11px] text-slate-400 leading-normal flex items-start gap-2">
                  <Send className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                  <span>
                    الآن الصق هذا النص في صندوق المحادثة معي بالأسفل، واضغط Enter، وسأبدأ فوراً في تشييد تطبيقك المخصص!
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
