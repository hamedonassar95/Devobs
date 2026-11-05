import React from 'react';
import { Sun, Moon, Cpu, Sparkles, RefreshCw, Download } from 'lucide-react';

interface DashboardHeaderProps {
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  activeTab: 'overview' | 'servers' | 'incidents' | 'deployments';
  onTabChange: (tab: 'overview' | 'servers' | 'incidents' | 'deployments') => void;
  onOpenAuditModal: () => void;
  onResetData: () => void;
  onExportAll: () => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  isDarkMode,
  onToggleDarkMode,
  activeTab,
  onTabChange,
  onOpenAuditModal,
  onResetData,
  onExportAll,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-slate-900/95 dark:bg-slate-950/95 backdrop-blur-md border-b border-slate-800 text-slate-100 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-8">
        {/* Zone 1: Brand Wordmark */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-base shadow-inner">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white whitespace-nowrap">
              منظومة رصد الخوادم
            </h1>
            <p className="text-[11px] text-slate-400 font-mono hidden sm:block">
              ServerOps Enterprise Console
            </p>
          </div>
        </div>

        {/* Zone 2: 4 single-line clean navigation links */}
        <nav className="hidden md:flex items-center gap-6 text-xs sm:text-sm font-medium text-slate-300">
          <button
            onClick={() => onTabChange('overview')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'overview' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            نظرة عامة
          </button>
          <button
            onClick={() => onTabChange('servers')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'servers' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            حالة الخوادم
          </button>
          <button
            onClick={() => onTabChange('incidents')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'incidents' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            سجل الأخطاء والحوادث
          </button>
          <button
            onClick={() => onTabChange('deployments')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'deployments' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            عمليات النشر
          </button>
        </nav>

        {/* Zone 3: 1 primary action + Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={onResetData}
            title="إعادة تعيين البيانات الافتراضية"
            aria-label="إعادة تعيين البيانات"
            className="p-2 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={onToggleDarkMode}
            title={isDarkMode ? 'التحويل للوضع النهاري' : 'التحويل للوضع الداكن'}
            aria-label="تبديل المظهر"
            className="p-2 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition-colors"
          >
            {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <button
            onClick={onOpenAuditModal}
            className="px-3.5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-all shadow-md flex items-center gap-1.5 whitespace-nowrap shrink-0"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>تدقيق بـ Gemini</span>
          </button>
        </div>
      </div>
    </header>
  );
};
