import React, { useState } from 'react';
import type { DashboardTab } from './DashboardHeader';

type Item = { id: DashboardTab; label: string };
type Group = { title: string; hint: string; items: Item[] };

const GROUPS: Group[] = [
  {
    title: 'التشغيل',
    hint: 'الحالة والسجلات التجريبية',
    items: [
      { id: 'overview', label: 'نظرة عامة' },
      { id: 'servers', label: 'الخوادم' },
      { id: 'incidents', label: 'سجل الأخطاء' },
      { id: 'deployments', label: 'عمليات النشر' },
    ],
  },
  {
    title: 'المختبر',
    hint: 'معاينات محلية، ليست تشغيلًا',
    items: [
      { id: 'github', label: 'GitHub Hub' },
      { id: '3d_room', label: 'غرفة 3D' },
      { id: 'cyber_game', label: 'لعبة الدفاع' },
      { id: 'gemini_chat', label: 'المساعد' },
      { id: 'media_studio', label: 'استوديو AI' },
    ],
  },
  {
    title: 'مساحة العمل',
    hint: 'عينات واجهة، بدون حساب حي',
    items: [
      { id: 'docs', label: 'Docs' },
      { id: 'sheets', label: 'Sheets' },
      { id: 'slides', label: 'Slides' },
      { id: 'tasks', label: 'Tasks' },
      { id: 'calendar', label: 'Calendar' },
      { id: 'forms', label: 'Forms' },
      { id: 'keep', label: 'Keep' },
      { id: 'drive', label: 'Drive' },
      { id: 'gmail', label: 'Gmail' },
      { id: 'chat', label: 'Chat' },
    ],
  },
];

const LABELS = new Map(GROUPS.flatMap((group) => group.items.map((item) => [item.id, item.label])));

export function MobileSectionMenu({
  activeTab,
  onTabChange,
}: {
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = LABELS.get(activeTab) ?? 'قسم';

  return (
    <div className="lg:hidden">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="mobile-section-panel"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 rounded-2xl border border-indigo-500/40 bg-slate-900 px-4 py-3 text-start shadow-lg shadow-indigo-950/30"
      >
        <span>
          <span className="block text-[11px] font-semibold tracking-wide text-indigo-300">القسم الحالي</span>
          <span className="mt-0.5 block text-sm font-extrabold text-white">{current}</span>
        </span>
        <span className="shrink-0 rounded-full border border-slate-700 px-3 py-1 text-xs font-bold text-slate-200">
          {open ? 'إغلاق' : 'كل الأقسام'}
        </span>
      </button>
      {open && (
        <div id="mobile-section-panel" className="mt-3 space-y-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-3">
          {GROUPS.map((group) => (
            <section key={group.title} aria-label={group.title}>
              <div className="mb-2 flex items-baseline justify-between gap-3">
                <h3 className="text-xs font-extrabold text-slate-100">{group.title}</h3>
                <p className="text-[10px] text-slate-500">{group.hint}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {group.items.map((item) => {
                  const selected = item.id === activeTab;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      aria-current={selected ? 'page' : undefined}
                      onClick={() => {
                        onTabChange(item.id);
                        setOpen(false);
                      }}
                      className={`min-h-11 rounded-xl border px-3 py-2 text-xs font-bold transition-colors ${
                        selected
                          ? 'border-indigo-400 bg-indigo-600 text-white'
                          : 'border-slate-800 bg-slate-900 text-slate-200 hover:border-slate-600'
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
