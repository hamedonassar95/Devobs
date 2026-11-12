import React from 'react';
import { Sun, Moon, Sparkles } from 'lucide-react';

interface HeaderProps {
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onNavigate: (sectionId: string) => void;
  activeSection: string;
}

export const Header: React.FC<HeaderProps> = ({
  isDarkMode,
  onToggleDarkMode,
  onNavigate,
  activeSection,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-8">
        {/* Zone 1: Brand Wordmark */}
        <a
          href="#home"
          onClick={(e) => {
            e.preventDefault();
            onNavigate('home');
          }}
          className="text-lg font-bold tracking-tight text-slate-900 dark:text-white whitespace-nowrap shrink-0 flex items-center gap-2"
        >
          <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-base shadow-sm">
            AI
          </div>
          <span>محراب البناء الذكي</span>
        </a>

        {/* Zone 2: Clean 4-5 single-line navigation links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600 dark:text-slate-300">
          <button
            onClick={() => onNavigate('workflow')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-indigo-600 dark:hover:text-indigo-400 ${
              activeSection === 'workflow' ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : ''
            }`}
          >
            كيف أعمل؟
          </button>
          <button
            onClick={() => onNavigate('capabilities')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-indigo-600 dark:hover:text-indigo-400 ${
              activeSection === 'capabilities' ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : ''
            }`}
          >
            ما يمكنني بناؤه
          </button>
          <button
            onClick={() => onNavigate('generator')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-indigo-600 dark:hover:text-indigo-400 ${
              activeSection === 'generator' ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : ''
            }`}
          >
            مولّد الأوامر التفاعلي
          </button>
          <button
            onClick={() => onNavigate('guidelines')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-indigo-600 dark:hover:text-indigo-400 ${
              activeSection === 'guidelines' ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : ''
            }`}
          >
            القواعد الذهبية
          </button>
          <button
            onClick={() => onNavigate('simulator')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-indigo-600 dark:hover:text-indigo-400 ${
              activeSection === 'simulator' ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : ''
            }`}
          >
            مختبر الأفكار
          </button>
        </nav>

        {/* Zone 3: 1 primary action */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onToggleDarkMode}
            aria-label="تبديل المظهر"
            className="p-2 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={() => onNavigate('generator')}
            className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-500 rounded-lg transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>اصنع طلبك الأول</span>
          </button>
        </div>
      </div>
    </header>
  );
};
