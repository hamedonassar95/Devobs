import React, { useState } from 'react';
import { CAPABILITIES, Capability } from '../data/capabilities';
import { Copy, Check, Terminal, ExternalLink } from 'lucide-react';

interface CapabilitiesShowcaseProps {
  onSelectPrompt: (prompt: string) => void;
}

export const CapabilitiesShowcase: React.FC<CapabilitiesShowcaseProps> = ({ onSelectPrompt }) => {
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const categories = ['all', ...Array.from(new Set(CAPABILITIES.map((c) => c.category)))];

  const filteredCapabilities =
    activeFilter === 'all'
      ? CAPABILITIES
      : CAPABILITIES.filter((c) => c.category === activeFilter);

  const handleCopy = (capability: Capability) => {
    navigator.clipboard.writeText(capability.samplePrompt);
    setCopiedId(capability.id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  return (
    <section id="capabilities" className="py-16 md:py-20 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-2">
              إمكانيات غير محدودة
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-2">
              ما الذي تستطيع أن تطلبه مني لبنائه؟
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 max-w-xl">
              من أدوات الذكاء الاصطناعي إلى لوحات التحكم المعقدة والألعاب التفاعلية. انقر على أي فئة لترى مثالاً واقعياً يمكنك طلبه الآن.
            </p>
          </div>

          {/* Interactive filter tabs */}
          <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl self-start">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                activeFilter === 'all'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              الكل
            </button>
            {categories
              .filter((cat) => cat !== 'all')
              .map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveFilter(cat)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                    activeFilter === cat
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  {cat}
                </button>
              ))}
          </div>
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCapabilities.map((item) => {
            const isCopied = copiedId === item.id;
            return (
              <div
                key={item.id}
                className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col justify-between hover:border-indigo-300 dark:hover:border-indigo-700 transition-all shadow-sm"
              >
                <div>
                  {/* Category unboxed metadata */}
                  <div className="flex items-center gap-2 text-xs text-indigo-600 dark:text-indigo-400 font-medium mb-3">
                    <span>{item.category}</span>
                    <span aria-hidden="true">·</span>
                    <span>جاهز للتنفيذ</span>
                  </div>

                  <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                    {item.title}
                  </h3>

                  <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-4">
                    {item.description}
                  </p>

                  {/* Features list */}
                  <div className="space-y-1.5 mb-5 text-xs text-slate-700 dark:text-slate-300">
                    {item.features.map((feat, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                        <span>{feat}</span>
                      </div>
                    ))}
                  </div>

                  {/* Sample prompt box */}
                  <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-3 border border-slate-200 dark:border-slate-800 text-xs mb-4">
                    <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 font-semibold mb-1.5 text-[11px]">
                      <span className="flex items-center gap-1">
                        <Terminal className="w-3 h-3 text-indigo-500" />
                        نموذج أمر يمكنك إرساله لي:
                      </span>
                    </div>
                    <p className="text-slate-800 dark:text-slate-200 leading-relaxed line-clamp-3">
                      "{item.samplePrompt}"
                    </p>
                  </div>
                </div>

                {/* Bottom actions */}
                <div className="pt-2 flex items-center gap-2">
                  <button
                    onClick={() => handleCopy(item)}
                    className="flex-1 py-2 px-3 text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex items-center justify-center gap-1.5"
                  >
                    {isCopied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        <span className="text-emerald-600 dark:text-emerald-400">تم نسخ الطلب!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>نسخ الطلب للشات</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => onSelectPrompt(item.samplePrompt)}
                    title="تعبئة في مولّد الأوامر"
                    className="py-2 px-3 text-xs font-semibold rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-colors flex items-center gap-1"
                  >
                    <span>تخصيص</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
