import React from 'react';

interface FooterProps {
  onNavigate: (sectionId: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate }) => {
  return (
    <footer className="py-12 bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-1 text-center md:text-right">
          <div className="text-sm font-bold text-slate-900 dark:text-white">
            محراب البناء الذكي — Google AI Studio
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            مهندس برمجياتك الفوري لتحويل الأفكار إلى تطبيقات ويب متكاملة وحقيقية.
          </p>
        </div>

        {/* Quiet navigation links */}
        <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-600 dark:text-slate-400">
          <button
            onClick={() => onNavigate('workflow')}
            className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            كيف أعمل؟
          </button>
          <span aria-hidden="true">·</span>
          <button
            onClick={() => onNavigate('capabilities')}
            className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            ما يمكنني بناؤه
          </button>
          <span aria-hidden="true">·</span>
          <button
            onClick={() => onNavigate('generator')}
            className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            مولّد الأوامر
          </button>
          <span aria-hidden="true">·</span>
          <button
            onClick={() => onNavigate('guidelines')}
            className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            القواعد الذهبية
          </button>
          <span aria-hidden="true">·</span>
          <button
            onClick={() => onNavigate('simulator')}
            className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            مختبر الأفكار
          </button>
        </div>

        <div className="text-xs text-slate-400 dark:text-slate-500">
          جاهز لتنفيذ طلبك القادم
        </div>
      </div>
    </footer>
  );
};
