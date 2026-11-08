import React from 'react';
import { Sun, Moon, Cpu, Sparkles, RefreshCw, Cloud, Mail, MessageSquare, CheckCircle2, Box, Bot, Video, FileText, FileSpreadsheet, BookOpen, Presentation, CheckSquare, Gamepad2, Calendar, FolderGit2 } from 'lucide-react';
import { User } from 'firebase/auth';

export type DashboardTab = 'overview' | 'github' | 'servers' | 'incidents' | 'deployments' | '3d_room' | 'cyber_game' | 'gemini_chat' | 'media_studio' | 'drive' | 'docs' | 'sheets' | 'slides' | 'tasks' | 'calendar' | 'forms' | 'gmail' | 'chat' | 'keep';

interface DashboardHeaderProps {
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
  onOpenAuditModal: () => void;
  onResetData: () => void;
  user: User | null;
  onSignInClick: () => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  isDarkMode,
  onToggleDarkMode,
  activeTab,
  onTabChange,
  onOpenAuditModal,
  onResetData,
  user,
  onSignInClick,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-slate-900/95 dark:bg-slate-950/95 backdrop-blur-md border-b border-slate-800 text-slate-100 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
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

        {/* Zone 2: Navigation links */}
        <nav className="hidden lg:flex items-center gap-4 text-xs font-medium text-slate-300 overflow-x-auto py-2">
          <button
            onClick={() => onTabChange('overview')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'overview' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            نظرة عامة
          </button>
          <button
            onClick={() => onTabChange('github')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'github' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>GitHub Hub</span>
          </button>
          <button
            onClick={() => onTabChange('3d_room')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === '3d_room' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <Box className="w-3.5 h-3.5 text-cyan-400" />
            <span>غرفة 3D</span>
          </button>
          <button
            onClick={() => onTabChange('cyber_game')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'cyber_game' ? 'text-cyan-400 font-bold border-b-2 border-cyan-500 pb-1' : ''
            }`}
          >
            <Gamepad2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>لعبة الدفاع 3D</span>
          </button>
          <button
            onClick={() => onTabChange('gemini_chat')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'gemini_chat' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <Bot className="w-3.5 h-3.5 text-indigo-400" />
            <span>مساعد Gemini</span>
          </button>
          <button
            onClick={() => onTabChange('media_studio')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'media_studio' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <Video className="w-3.5 h-3.5 text-purple-400" />
            <span>استوديو AI</span>
          </button>
          <button
            onClick={() => onTabChange('servers')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'servers' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            الخوادم
          </button>
          <button
            onClick={() => onTabChange('incidents')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'incidents' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            سجل الأخطاء
          </button>
          <button
            onClick={() => onTabChange('deployments')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white ${
              activeTab === 'deployments' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            عمليات النشر
          </button>
          <button
            onClick={() => onTabChange('drive')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'drive' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <Cloud className="w-3.5 h-3.5 text-sky-400" />
            <span>Drive</span>
          </button>
          <button
            onClick={() => onTabChange('docs')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'docs' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-blue-400" />
            <span>Docs</span>
          </button>
          <button
            onClick={() => onTabChange('gmail')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'gmail' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <Mail className="w-3.5 h-3.5 text-rose-400" />
            <span>Gmail</span>
          </button>
          <button
            onClick={() => onTabChange('chat')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'chat' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
            <span>Chat</span>
          </button>
          <button
            onClick={() => onTabChange('forms')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'forms' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-purple-400" />
            <span>Forms</span>
          </button>
          <button
            onClick={() => onTabChange('sheets')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'sheets' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>Sheets</span>
          </button>
          <button
            onClick={() => onTabChange('slides')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'slides' ? 'text-amber-400 font-bold border-b-2 border-amber-500 pb-1' : ''
            }`}
          >
            <Presentation className="w-3.5 h-3.5 text-amber-400" />
            <span>Slides</span>
          </button>
          <button
            onClick={() => onTabChange('tasks')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'tasks' ? 'text-sky-400 font-bold border-b-2 border-sky-500 pb-1' : ''
            }`}
          >
            <CheckSquare className="w-3.5 h-3.5 text-sky-400" />
            <span>Tasks</span>
          </button>
          <button
            onClick={() => onTabChange('calendar')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'calendar' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <Calendar className="w-3.5 h-3.5 text-indigo-400" />
            <span>Calendar</span>
          </button>
          <button
            onClick={() => onTabChange('keep')}
            className={`transition-colors whitespace-nowrap shrink-0 hover:text-white flex items-center gap-1 ${
              activeTab === 'keep' ? 'text-indigo-400 font-bold border-b-2 border-indigo-500 pb-1' : ''
            }`}
          >
            <BookOpen className="w-3.5 h-3.5 text-amber-400" />
            <span>Keep</span>
          </button>
        </nav>

        {/* Zone 3: 1 primary action + Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          {user ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200">
              {user.photoURL ? (
                <img
                  src={user.photoURL}
                  alt={user.displayName || 'User'}
                  className="w-5 h-5 rounded-full"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-5 h-5 rounded-full bg-indigo-600 text-[10px] font-bold flex items-center justify-center text-white">
                  {user.displayName?.[0] || 'U'}
                </div>
              )}
              <span className="hidden xl:inline truncate max-w-[100px]">
                {user.displayName || 'Google'}
              </span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            </div>
          ) : (
            <button
              onClick={onSignInClick}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <span>ربط Google</span>
            </button>
          )}

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
