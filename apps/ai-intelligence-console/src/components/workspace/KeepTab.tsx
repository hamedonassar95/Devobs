import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  BookOpen,
  Plus,
  Trash2,
  Tag,
  CheckCircle2,
  FileText,
  AlertTriangle,
  Info,
  ExternalLink,
  Search,
  Pin,
  Sparkles,
  Upload,
  CheckSquare,
  FileSpreadsheet,
  Download,
  X,
  Check,
  Archive,
  ArchiveRestore,
  Inbox,
} from 'lucide-react';
import { createTask } from '../../services/googleTasksService';
import { createGoogleDoc } from '../../services/googleDocsService';

interface RunbookNote {
  id: string;
  title: string;
  content: string;
  category: 'runbook' | 'checklist' | 'incident' | 'general';
  isPinned: boolean;
  isArchived?: boolean;
  createdAt: string;
}

interface KeepTabProps {
  user?: User | null;
  token?: string | null;
}

const INITIAL_NOTES: RunbookNote[] = [
  {
    id: 'note_1',
    title: 'إجراءات استجابة طوارئ نفاد الذاكرة (OOM Runbook)',
    content: `1. فحص استهلاك العمليات الحالية باستخدام أمر: top -o %MEM أو htop.
2. التحقق من سجلات النواة: dmesg -T | grep -i oom-killer.
3. تفريغ الذاكرة المؤقتة بأمان إذا لزم: sync; echo 3 > /proc/sys/vm/drop_caches.
4. إعادة تشغيل حاوية الخدمة المسببة للاختناق تدريجياً مع تفعيل وضع الصيانة.`,
    category: 'runbook',
    isPinned: true,
    isArchived: false,
    createdAt: '2026-11-05 14:00',
  },
  {
    id: 'note_2',
    title: 'قائمة التحقق قبل ترقية خوادم الإنتاج (Pre-Deployment Checklist)',
    content: `[ ] التأكد من اجتياز جميع اختبارات الـ CI/CD بنجاح.
[ ] أخذ لقطة سريعة (Snapshot) لقاعدة البيانات الأساسية.
[ ] التحقق من جاهزية مسارات التراجع (Rollback Plan).
[ ] إبلاغ مهندس العمليات المناوب ومراقبة مقاييس الـ Latency.`,
    category: 'checklist',
    isPinned: true,
    isArchived: false,
    createdAt: '2026-11-05 15:30',
  },
  {
    id: 'note_3',
    title: 'إرشادات استعادة اتصالات قاعدة البيانات (Connection Pool Exhaustion)',
    content: `في حال وصول اتصالات Postgres إلى الحد الأقصى:
- الاستعلام: SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
- إنهاء الاتصالات المعلقة التي تجاوزت 5 دقائق: SELECT pg_terminate_backend(pid) ...
- رفع حدود الـ max_connections وتفعيل PgBouncer للتحكم في التدفق.`,
    category: 'runbook',
    isPinned: false,
    isArchived: false,
    createdAt: '2026-11-05 16:15',
  },
  {
    id: 'note_4',
    title: 'مذكرة صيانة خوادم التخزين للربع السابق (مؤرشفة)',
    content: `تم الانتهاء بنجاح من توسيع مصفوفات التخزين SAN/NAS وإعادة توجيه حركة المرور الاحتياطية.`,
    category: 'general',
    isPinned: false,
    isArchived: true,
    createdAt: '2026-10-20 11:00',
  },
];

export function KeepTab({ user, token }: KeepTabProps) {
  const [notes, setNotes] = useState<RunbookNote[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('serverops_keep_notes');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error(e);
        }
      }
    }
    return INITIAL_NOTES;
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'active' | 'archived'>('active');
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState<'runbook' | 'checklist' | 'incident' | 'general'>('runbook');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Confirmation modal
  const [confirmationModal, setConfirmationModal] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    confirmLabel?: string;
    confirmStyle?: 'danger' | 'primary';
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    description: '',
    onConfirm: () => {},
  });

  useEffect(() => {
    localStorage.setItem('serverops_keep_notes', JSON.stringify(notes));
  }, [notes]);

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) return;

    const newNote: RunbookNote = {
      id: `note_${Date.now()}`,
      title: newTitle.trim(),
      content: newContent.trim(),
      category: newCategory,
      isPinned: false,
      isArchived: false,
      createdAt: new Date().toISOString().replace('T', ' ').slice(0, 16),
    };

    setNotes((prev) => [newNote, ...prev]);
    setNewTitle('');
    setNewContent('');
    setIsNewModalOpen(false);
    setSuccessMsg('تم حفظ المذكرة بنجاح في سجل Runbooks!');
  };

  const handleDeleteNote = (id: string, title: string) => {
    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد حذف المذكرة نهائياً',
      description: `هل أنت متأكد من حذف المذكرة "${title}" بشكل نهائي؟ لا يمكن التراجع عن هذا الإجراء.`,
      confirmLabel: 'حذف نهائي',
      confirmStyle: 'danger',
      onConfirm: () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        setNotes((prev) => prev.filter((n) => n.id !== id));
        setSuccessMsg(`تم حذف المذكرة "${title}".`);
      },
    });
  };

  const handleTogglePin = (id: string) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, isPinned: !n.isPinned } : n))
    );
  };

  // Archive / Unarchive note
  const handleToggleArchive = (note: RunbookNote) => {
    const isCurrentlyArchived = !!note.isArchived;
    const actionName = isCurrentlyArchived ? 'استعادة من الأرشيف' : 'نقل إلى سلة الأرشيف';

    setConfirmationModal({
      isOpen: true,
      title: `تأكيد ${actionName}`,
      description: isCurrentlyArchived
        ? `هل تريد استعادة المذكرة "${note.title}" إلى قائمة الملاحظات النشطة؟`
        : `هل تريد أرشفة المذكرة "${note.title}" ونقلها إلى سلة الأرشيف؟ ستبقى محفوظة ويمكنك استرجاعها في أي وقت.`,
      confirmLabel: isCurrentlyArchived ? 'استعادة المذكرة' : 'أرشفة المذكرة',
      confirmStyle: 'primary',
      onConfirm: () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        setNotes((prev) =>
          prev.map((n) =>
            n.id === note.id
              ? {
                  ...n,
                  isArchived: !isCurrentlyArchived,
                  isPinned: isCurrentlyArchived ? n.isPinned : false, // Unpin if archiving
                }
              : n
          )
        );
        setSuccessMsg(
          isCurrentlyArchived
            ? `تمت استعادة "${note.title}" بنجاح إلى الملاحظات النشطة.`
            : `تم نقل "${note.title}" إلى سلة الأرشيف بنجاح.`
        );
      },
    });
  };

  // Empty Archive
  const handleEmptyArchive = () => {
    const archivedCount = notes.filter((n) => n.isArchived).length;
    if (archivedCount === 0) return;

    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد إفراغ سلة الأرشيف',
      description: `سيتم حذف جميع الملاحظات المؤرشفة (${archivedCount} مذكرة) نهائياً من النظام. هل أنت متأكد؟`,
      confirmLabel: 'إفراغ الأرشيف نهائياً',
      confirmStyle: 'danger',
      onConfirm: () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        setNotes((prev) => prev.filter((n) => !n.isArchived));
        setSuccessMsg('تم إفراغ سلة الأرشيف بالكامل.');
      },
    });
  };

  // Export note to Google Tasks
  const handleExportToTasks = (note: RunbookNote) => {
    if (!token) {
      setErrorMsg('يرجى تسجيل الدخول بحساب Google Workspace أولاً لتمكين التصدير.');
      return;
    }

    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد تصدير المذكرة إلى Google Tasks',
      description: `سيتم إنشاء مهمة تشغيلية في Google Tasks بعنوان "${note.title}" ومحتواها.`,
      confirmLabel: 'تأكيد التصدير',
      confirmStyle: 'primary',
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        try {
          await createTask(token, '@default', {
            title: `[Runbook SRE] ${note.title}`,
            notes: note.content,
          });
          setSuccessMsg(`تم تصدير "${note.title}" بنجاح كـ مهمة في Google Tasks!`);
        } catch (err: any) {
          setErrorMsg('فشل التصدير إلى Google Tasks: ' + err.message);
        }
      },
    });
  };

  // Export note to Google Docs
  const handleExportToDocs = (note: RunbookNote) => {
    if (!token) {
      setErrorMsg('يرجى تسجيل الدخول بحساب Google Workspace أولاً لتمكين التصدير.');
      return;
    }

    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد تصدير المذكرة إلى Google Docs',
      description: `سيتم إنشاء مستند رسمي في Google Docs بعنوان "${note.title}".`,
      confirmLabel: 'تأكيد التصدير',
      confirmStyle: 'primary',
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        try {
          const doc = await createGoogleDoc(token, `[SRE Playbook] ${note.title}`);
          setSuccessMsg(`تم إنشاء وثيقة Google Docs بنجاح! المعرّف: ${doc.documentId}`);
        } catch (err: any) {
          setErrorMsg('فشل إنشاء مستند Google Docs: ' + err.message);
        }
      },
    });
  };

  const activeNotes = notes.filter((n) => !n.isArchived);
  const archivedNotes = notes.filter((n) => !!n.isArchived);

  const displayedNotes = (viewMode === 'active' ? activeNotes : archivedNotes)
    .filter((n) => {
      const matchSearch =
        n.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        n.content.toLowerCase().includes(searchTerm.toLowerCase());
      const matchCat = selectedCategory === 'all' || n.category === selectedCategory;
      return matchSearch && matchCat;
    })
    .sort((a, b) => (b.isPinned ? 1 : 0) - (a.isPinned ? 1 : 0));

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white">
                سجلات وملاحظات العمليات (Keep Runbooks & Notes)
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 font-medium">
                SRE Playbooks
              </span>
            </div>
            <p className="text-xs text-slate-400">
              إدارة كتيبات الطوارئ، مذكرات الصيانة، وأرشفة الملاحظات المنتهية مع التصدير لـ Workspace
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* View mode toggle: Active vs Archived */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setViewMode('active')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
                viewMode === 'active'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Inbox className="w-3.5 h-3.5" />
              <span>النشطة ({activeNotes.length})</span>
            </button>
            <button
              onClick={() => setViewMode('archived')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
                viewMode === 'archived'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Archive className="w-3.5 h-3.5" />
              <span>الأرشيف ({archivedNotes.length})</span>
            </button>
          </div>

          {viewMode === 'active' ? (
            <button
              onClick={() => setIsNewModalOpen(true)}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg shadow-amber-600/30 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>إضافة مذكرة</span>
            </button>
          ) : (
            archivedNotes.length > 0 && (
              <button
                onClick={handleEmptyArchive}
                className="px-3.5 py-2 bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 border border-rose-800/50 rounded-xl font-medium text-xs flex items-center gap-1.5 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                <span>إفراغ الأرشيف</span>
              </button>
            )
          )}
        </div>
      </div>

      {/* Messages */}
      {successMsg && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-sm flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Enterprise Keep Policy Explanation Box */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-3">
        <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-bold">سياسة تكامل واجهة Google Keep API ونظام الأرشفة:</p>
          <p className="text-slate-300 leading-relaxed text-xs">
            واجهة <code className="text-amber-200 bg-amber-950/60 px-1 py-0.5 rounded">keep.googleapis.com</code> مخصصة لحسابات المؤسسات فقط عبر تفويض النطاق (Domain Delegation).
            يوفر نظام <strong>Runbooks & Notes</strong> المحلي الآن إمكانية <strong>أرشفة الملاحظات غير الضرورية</strong> لعزلها عن قائمة العمل اليومية، مع إمكانية استرجاعها أو تصديرها بنقرة زر إلى <strong>Google Tasks</strong> و <strong>Google Docs</strong>.
          </p>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={viewMode === 'active' ? "بحث في الملاحظات النشطة..." : "بحث في سلة الأرشيف..."}
            className="bg-transparent text-xs text-white placeholder-slate-500 outline-none w-full"
          />
        </div>

        <div className="flex items-center gap-1.5 text-xs">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-1.5 rounded-lg border transition-colors ${
              selectedCategory === 'all'
                ? 'bg-amber-600/30 text-amber-400 border-amber-500/50 font-bold'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            الكل ({viewMode === 'active' ? activeNotes.length : archivedNotes.length})
          </button>
          <button
            onClick={() => setSelectedCategory('runbook')}
            className={`px-3 py-1.5 rounded-lg border transition-colors ${
              selectedCategory === 'runbook'
                ? 'bg-amber-600/30 text-amber-400 border-amber-500/50 font-bold'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            كتيبات Runbooks
          </button>
          <button
            onClick={() => setSelectedCategory('checklist')}
            className={`px-3 py-1.5 rounded-lg border transition-colors ${
              selectedCategory === 'checklist'
                ? 'bg-amber-600/30 text-amber-400 border-amber-500/50 font-bold'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            قوائم التحقق
          </button>
          <button
            onClick={() => setSelectedCategory('incident')}
            className={`px-3 py-1.5 rounded-lg border transition-colors ${
              selectedCategory === 'incident'
                ? 'bg-amber-600/30 text-amber-400 border-amber-500/50 font-bold'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            الحوادث
          </button>
          <button
            onClick={() => setSelectedCategory('general')}
            className={`px-3 py-1.5 rounded-lg border transition-colors ${
              selectedCategory === 'general'
                ? 'bg-amber-600/30 text-amber-400 border-amber-500/50 font-bold'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            عامة
          </button>
        </div>
      </div>

      {/* Notes Grid */}
      {displayedNotes.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 rounded-2xl border border-dashed border-slate-800 text-center">
          {viewMode === 'active' ? (
            <>
              <Inbox className="w-12 h-12 text-slate-600 mb-3" />
              <h4 className="text-base font-medium text-slate-300 mb-1">لا توجد ملاحظات نشطة مطابقة</h4>
              <p className="text-xs text-slate-500 max-w-sm mb-4">
                أضف كتيب إجراءات جديد أو تصفح الملاحظات المؤرشفة.
              </p>
              <button
                onClick={() => setIsNewModalOpen(true)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-amber-400 text-xs rounded-xl border border-slate-700 transition-colors"
              >
                إضافة مذكرة جديدة
              </button>
            </>
          ) : (
            <>
              <Archive className="w-12 h-12 text-slate-600 mb-3" />
              <h4 className="text-base font-medium text-slate-300 mb-1">سلة الأرشيف فارغة</h4>
              <p className="text-xs text-slate-500 max-w-sm">
                الملاحظات غير الضرورية التي تقوم بأرشفتها ستظهر هنا لحفظها والرجوع إليها عند الحاجة.
              </p>
            </>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedNotes.map((note) => {
            const categoryBadge =
              note.category === 'runbook'
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                : note.category === 'checklist'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : note.category === 'incident'
                ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/20';

            const isArchived = !!note.isArchived;

            return (
              <div
                key={note.id}
                className={`p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-3 ${
                  isArchived
                    ? 'bg-slate-900/60 border-slate-800/80 opacity-80'
                    : note.isPinned
                    ? 'bg-slate-900/90 border-amber-500/50 shadow-lg shadow-amber-950/20'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-bold text-white flex-1 leading-snug">
                      {note.title}
                    </h4>

                    <div className="flex items-center gap-1">
                      {/* Pin Button (only for active notes) */}
                      {!isArchived && (
                        <button
                          onClick={() => handleTogglePin(note.id)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            note.isPinned
                              ? 'text-amber-400 bg-amber-500/20'
                              : 'text-slate-600 hover:text-slate-400'
                          }`}
                          title={note.isPinned ? 'إلغاء التثبيت' : 'تثبيت في المقدمة'}
                        >
                          <Pin className="w-3.5 h-3.5" />
                        </button>
                      )}

                      {/* Archive / Unarchive Button */}
                      <button
                        onClick={() => handleToggleArchive(note)}
                        className={`p-1.5 rounded-lg transition-colors ${
                          isArchived
                            ? 'text-amber-400 hover:bg-amber-500/20'
                            : 'text-slate-500 hover:text-amber-400 hover:bg-slate-800'
                        }`}
                        title={isArchived ? 'استعادة من الأرشيف' : 'نقل إلى سلة الأرشيف'}
                      >
                        {isArchived ? (
                          <ArchiveRestore className="w-3.5 h-3.5" />
                        ) : (
                          <Archive className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="whitespace-pre-line text-xs text-slate-300 leading-relaxed font-mono bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                    {note.content}
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800 flex flex-col gap-2">
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span className={`px-2 py-0.5 rounded-full border font-semibold ${categoryBadge}`}>
                      {note.category === 'runbook'
                        ? 'كتيب طوارئ'
                        : note.category === 'checklist'
                        ? 'قائمة تدقيق'
                        : note.category === 'incident'
                        ? 'سجل حادثة'
                        : 'مذكرة عامة'}
                    </span>

                    <div className="flex items-center gap-2">
                      <span>{note.createdAt}</span>
                      <button
                        onClick={() => handleDeleteNote(note.id, note.title)}
                        className="p-1 text-slate-600 hover:text-rose-400 transition-colors"
                        title="حذف نهائي"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Quick Workspace Export Buttons */}
                  <div className="flex items-center gap-2 pt-1 border-t border-slate-800/60 text-xs">
                    <button
                      onClick={() => handleExportToTasks(note)}
                      className="flex-1 py-1 px-2 rounded-lg bg-sky-950/30 hover:bg-sky-900/40 text-sky-400 border border-sky-800/40 flex items-center justify-center gap-1 text-[11px] transition-colors"
                      title="تصدير كـ مهمة في Google Tasks"
                    >
                      <CheckSquare className="w-3 h-3" />
                      <span>إلى Tasks</span>
                    </button>
                    <button
                      onClick={() => handleExportToDocs(note)}
                      className="flex-1 py-1 px-2 rounded-lg bg-blue-950/30 hover:bg-blue-900/40 text-blue-400 border border-blue-800/40 flex items-center justify-center gap-1 text-[11px] transition-colors"
                      title="تصدير كـ مستند في Google Docs"
                    >
                      <FileText className="w-3 h-3" />
                      <span>إلى Docs</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* New Note Modal */}
      {isNewModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleAddNote}
            className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-amber-400" />
                <span>إضافة كتيب أو مذكرة صيانة جديدة</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsNewModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  عنوان الإجراء أو المذكرة:
                </label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="مثال: خطوات إعادة تهيئة شهادات SSL المنتهية"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  نوع التصنيف:
                </label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white outline-none focus:border-amber-500"
                >
                  <option value="runbook">كتيب طوارئ (Runbook)</option>
                  <option value="checklist">قائمة تدقيق (Checklist)</option>
                  <option value="incident">سجل حادثة (Incident Post-Mortem)</option>
                  <option value="general">مذكرة عامة (General Note)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  خطوات وأوامر التنفيذ:
                </label>
                <textarea
                  required
                  rows={5}
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="اكتب الأوامر الهندسية والخطوات بدقة..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white font-mono outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsNewModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
              >
                إلغاء
              </button>
              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-lg shadow-amber-600/30"
              >
                حفظ الكتيب
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Mandatory User Confirmation Modal */}
      {confirmationModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-scaleUp">
            <div className="flex items-center gap-3 text-amber-400 mb-3">
              <div
                className={`p-2.5 rounded-xl border ${
                  confirmationModal.confirmStyle === 'danger'
                    ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                    : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                }`}
              >
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-white text-base">{confirmationModal.title}</h3>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed mb-6">
              {confirmationModal.description}
            </p>

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setConfirmationModal((prev) => ({ ...prev, isOpen: false }))}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:bg-slate-800 transition-colors"
              >
                إلغاء
              </button>
              <button
                type="button"
                onClick={confirmationModal.onConfirm}
                className={`px-5 py-2 rounded-xl text-xs font-medium text-white flex items-center gap-1.5 transition-all shadow-md ${
                  confirmationModal.confirmStyle === 'danger'
                    ? 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20'
                    : 'bg-amber-600 hover:bg-amber-500 shadow-amber-600/20'
                }`}
              >
                <Check className="w-4 h-4" />
                <span>{confirmationModal.confirmLabel || 'تأكيد الإجراء'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
