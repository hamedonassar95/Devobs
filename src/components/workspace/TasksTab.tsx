import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  CheckSquare,
  Plus,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  Check,
  X,
  Trash2,
  Calendar,
  Sparkles,
  ListFilter,
  FileCheck2,
  Clock,
  ArrowRight,
} from 'lucide-react';
import {
  listTaskLists,
  listTasks,
  createTask,
  updateTaskStatus,
  deleteTask,
  createIncidentTasks,
  GoogleTaskList,
  GoogleTaskItem,
} from '../../services/googleTasksService';
import { googleSignIn } from '../../services/googleAuth';
import { Server, Incident } from '../../types/serverDashboard';

interface TasksTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  onAuthSuccess: (user: User, token: string) => void;
}

export function TasksTab({ user, token, servers, incidents, onAuthSuccess }: TasksTabProps) {
  const [taskLists, setTaskLists] = useState<GoogleTaskList[]>([]);
  const [selectedListId, setSelectedListId] = useState<string>('@default');
  const [tasks, setTasks] = useState<GoogleTaskItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filter state
  const [filterMode, setFilterMode] = useState<'all' | 'needsAction' | 'completed'>('all');

  // New Task Modal state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [taskTitleInput, setTaskTitleInput] = useState('');
  const [taskNotesInput, setTaskNotesInput] = useState('');
  const [taskDueInput, setTaskDueInput] = useState('');

  // Confirmation Modal state for mutating/destructive actions
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

  const fetchTaskLists = async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const lists = await listTaskLists(token);
      setTaskLists(lists);
      if (lists.length > 0 && selectedListId === '@default') {
        setSelectedListId(lists[0].id);
      }
    } catch (err: any) {
      console.error('Error fetching task lists:', err);
      setError(err.message || 'فشل جلب قوائم مهام Google Tasks');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTasksForCurrentList = async (listId: string) => {
    if (!token) return;
    setIsLoadingTasks(true);
    setError(null);
    try {
      const items = await listTasks(token, listId, true);
      setTasks(items);
    } catch (err: any) {
      console.error('Error fetching tasks:', err);
      setError(err.message || 'فشل جلب قائمة المهام');
    } finally {
      setIsLoadingTasks(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchTaskLists();
    }
  }, [token]);

  useEffect(() => {
    if (token && selectedListId) {
      fetchTasksForCurrentList(selectedListId);
    }
  }, [token, selectedListId]);

  const handleConnectGoogle = async () => {
    try {
      setError(null);
      const res = await googleSignIn();
      if (res) {
        onAuthSuccess(res.user, res.accessToken);
      }
    } catch (err: any) {
      setError('فشل تسجيل الدخول أو إعطاء أذونات Google Tasks: ' + err.message);
    }
  };

  // Toggle task status
  const handleToggleTaskStatus = (task: GoogleTaskItem) => {
    if (!token) return;
    const nextStatus = task.status === 'completed' ? 'needsAction' : 'completed';
    const actionDesc = nextStatus === 'completed' ? 'تعيين المهمة كمكتملة' : 'إعادة فتح المهمة';

    setConfirmationModal({
      isOpen: true,
      title: `تأكيد ${actionDesc}`,
      description: `هل ترغب في ${actionDesc} بعنوان "${task.title}" في قائمة Google Tasks؟`,
      confirmLabel: 'تأكيد التحديث',
      confirmStyle: 'primary',
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        try {
          await updateTaskStatus(token, selectedListId, task.id, nextStatus);
          setSuccessMsg(`تم تحديث حالة المهمة بنجاح.`);
          await fetchTasksForCurrentList(selectedListId);
        } catch (err: any) {
          setError('فشل تحديث حالة المهمة: ' + err.message);
        }
      },
    });
  };

  // Delete task
  const handleDeleteTask = (task: GoogleTaskItem) => {
    if (!token) return;
    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد حذف المهمة من Google Tasks',
      description: `هل أنت متأكد من حذف المهمة "${task.title}" نهائياً من حساب Google الخاص بك؟ هذا الإجراء لا يمكن التراجع عنه.`,
      confirmLabel: 'حذف نهائي',
      confirmStyle: 'danger',
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        try {
          await deleteTask(token, selectedListId, task.id);
          setSuccessMsg(`تم حذف المهمة بنجاح.`);
          await fetchTasksForCurrentList(selectedListId);
        } catch (err: any) {
          setError('فشل حذف المهمة: ' + err.message);
        }
      },
    });
  };

  // Create new manual task
  const handleCreateTaskSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskTitleInput.trim()) return;

    setIsCreateModalOpen(false);
    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد إنشاء مهمة جديدة في Google Tasks',
      description: `سيتم إنشاء مهمة جديدة بعنوان "${taskTitleInput}" في حساب Google Tasks الخاص بك.`,
      confirmLabel: 'تأكيد الإنشاء',
      confirmStyle: 'primary',
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        if (!token) return;
        try {
          await createTask(token, selectedListId, {
            title: taskTitleInput,
            notes: taskNotesInput,
            due: taskDueInput ? new Date(taskDueInput).toISOString() : undefined,
          });
          setSuccessMsg('تمت إضافة المهمة إلى Google Tasks بنجاح!');
          setTaskTitleInput('');
          setTaskNotesInput('');
          setTaskDueInput('');
          await fetchTasksForCurrentList(selectedListId);
        } catch (err: any) {
          setError('فشل إنشاء المهمة: ' + err.message);
        }
      },
    });
  };

  // Create tasks from Incident
  const handleGenerateIncidentTasks = (incident: Incident) => {
    if (!token) return;
    const targetServer = servers.find((s) => s.id === incident.serverId);

    setConfirmationModal({
      isOpen: true,
      title: `توليد مهام متابعة للحادثة: ${incident.code}`,
      description: `سيتم إنشاء 3 مهام متابعة وتشغيل احترافية لفرق SRE (معالجة طارئة، اختبار تعافي، وتحديث Runbook) في Google Tasks للحادثة "${incident.message}".`,
      confirmLabel: 'توليد المهام الـ 3',
      confirmStyle: 'primary',
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        try {
          await createIncidentTasks(token, selectedListId, incident, targetServer);
          setSuccessMsg(`تم إنشاء مهام متابعة الحادثة ${incident.code} في Google Tasks بنجاح!`);
          await fetchTasksForCurrentList(selectedListId);
        } catch (err: any) {
          setError('فشل إنشاء مهام الحادثة: ' + err.message);
        }
      },
    });
  };

  const filteredTasks = tasks.filter((t) => {
    if (filterMode === 'needsAction') return t.status === 'needsAction';
    if (filterMode === 'completed') return t.status === 'completed';
    return true;
  });

  const pendingCount = tasks.filter((t) => t.status === 'needsAction').length;
  const completedCount = tasks.filter((t) => t.status === 'completed').length;

  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] p-8 text-center bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800">
        <div className="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center mb-4 text-sky-400">
          <CheckSquare className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">ربط Google Tasks™ بالمنظومة السحابية</h2>
        <p className="text-slate-400 max-w-lg mb-6 text-sm leading-relaxed">
          قم بتسجيل الدخول بحساب Google Workspace لمزامنة مهام SRE، وجدولة خطط معالجة الأعطال، ومتابعة إجراءات الصيانة الدورية وتحديث الكتيبات.
        </p>
        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm max-w-md flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <button
          onClick={handleConnectGoogle}
          className="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white font-medium rounded-xl shadow-lg shadow-sky-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <CheckSquare className="w-5 h-5" />
          <span>تسجيل الدخول وربط Google Tasks</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Quick Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-slate-900/70 border border-slate-800 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 shadow-inner">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white">إدارة مهام العمليات (Google Tasks™)</h2>
              <span className="px-2 py-0.5 text-xs rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30">
                Workspace مفعّل
              </span>
            </div>
            <p className="text-sm text-slate-400">
              تتبع مهام SRE التشغيلية وخطط معالجة الحوادث ومزامنتها لحظياً مع تطبيقات Google Tasks
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Select Task List */}
          {taskLists.length > 0 && (
            <select
              value={selectedListId}
              onChange={(e) => setSelectedListId(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-3 py-2 focus:outline-none focus:border-sky-500"
            >
              {taskLists.map((list) => (
                <option key={list.id} value={list.id}>
                  قائمة: {list.title}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => {
              fetchTaskLists();
              if (selectedListId) fetchTasksForCurrentList(selectedListId);
            }}
            disabled={isLoading || isLoadingTasks}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm transition-all border border-slate-700 disabled:opacity-50"
            title="تحديث المهام"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingTasks ? 'animate-spin text-sky-400' : ''}`} />
            <span>تحديث</span>
          </button>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white text-sm font-medium shadow-md shadow-sky-600/20 transition-all border border-sky-500/30"
          >
            <Plus className="w-4 h-4" />
            <span>مهمة جديدة</span>
          </button>
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

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Metric Counters & Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400">إجمالي المهام</p>
            <h4 className="text-xl font-bold text-white mt-1">{tasks.length}</h4>
          </div>
          <div className="w-10 h-10 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center">
            <CheckSquare className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs text-amber-400">مهام قيد الانتظار</p>
            <h4 className="text-xl font-bold text-amber-300 mt-1">{pendingCount}</h4>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-xs text-emerald-400">مهام مكتملة</p>
            <h4 className="text-xl font-bold text-emerald-300 mt-1">{completedCount}</h4>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-around">
          <button
            onClick={() => setFilterMode('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              filterMode === 'all'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            الكل ({tasks.length})
          </button>
          <button
            onClick={() => setFilterMode('needsAction')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              filterMode === 'needsAction'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            المتبقية ({pendingCount})
          </button>
          <button
            onClick={() => setFilterMode('completed')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              filterMode === 'completed'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            المكتملة ({completedCount})
          </button>
        </div>
      </div>

      {/* Main Grid: Tasks List & SRE Incident Action Generators */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Tasks items */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <ListFilter className="w-4 h-4 text-sky-400" />
              <span>مهام القائمة الحالية ({filteredTasks.length})</span>
            </h3>
            <span className="text-xs text-slate-500">انقر على المربع لتحديث حالة المهمة</span>
          </div>

          {isLoadingTasks ? (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 rounded-2xl border border-slate-800">
              <Loader2 className="w-8 h-8 animate-spin text-sky-400 mb-3" />
              <p className="text-sm text-slate-400">جاري قراءة المهام من Google Tasks...</p>
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 rounded-2xl border border-dashed border-slate-800 text-center">
              <CheckSquare className="w-12 h-12 text-slate-600 mb-3" />
              <h4 className="text-base font-medium text-slate-300 mb-1">لا توجد مهام مطابقة حالياً</h4>
              <p className="text-sm text-slate-500 max-w-sm mb-4">
                أضف مهمة جديدة أو قم بتوليد مهام عمل تلقائية من حوادث المنظومة المرصودة.
              </p>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-sky-400 text-sm rounded-xl border border-slate-700 transition-colors"
              >
                إضافة مهمة جديدة
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {filteredTasks.map((task) => {
                const isDone = task.status === 'completed';
                return (
                  <div
                    key={task.id}
                    className={`p-4 rounded-xl border transition-all flex items-start justify-between gap-3 ${
                      isDone
                        ? 'bg-slate-900/40 border-slate-800/60 opacity-75'
                        : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 shadow-sm'
                    }`}
                  >
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <button
                        onClick={() => handleToggleTaskStatus(task)}
                        className={`w-6 h-6 rounded-lg border flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors ${
                          isDone
                            ? 'bg-emerald-500 border-emerald-500 text-white'
                            : 'border-slate-600 hover:border-sky-400 text-transparent hover:text-sky-400/40'
                        }`}
                        title={isDone ? 'إعادة المهمة كقيد التنفيذ' : 'إكمال المهمة'}
                      >
                        <Check className="w-4 h-4 stroke-[3]" />
                      </button>

                      <div className="min-w-0 flex-1">
                        <p
                          className={`text-sm font-medium ${
                            isDone ? 'line-through text-slate-400' : 'text-slate-100'
                          }`}
                        >
                          {task.title}
                        </p>

                        {task.notes && (
                          <p className="text-xs text-slate-400 mt-1 whitespace-pre-line leading-relaxed">
                            {task.notes}
                          </p>
                        )}

                        <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-slate-500">
                          {task.due && (
                            <span className="flex items-center gap-1 text-sky-400 bg-sky-950/40 px-2 py-0.5 rounded border border-sky-900/50">
                              <Calendar className="w-3 h-3" />
                              <span>موعد الإنجاز: {new Date(task.due).toLocaleDateString('ar-EG')}</span>
                            </span>
                          )}
                          {task.updated && (
                            <span>آخر تحديث: {new Date(task.updated).toLocaleDateString('ar-EG')}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteTask(task)}
                      className="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 transition-colors"
                      title="حذف المهمة من Google Tasks"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right 1 Col: SRE Incident Tasks Auto-Generator */}
        <div className="space-y-4">
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl">
            <h3 className="font-semibold text-slate-200 text-sm mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-sky-400" />
              <span>توليد مهام SRE تلقائية من الحوادث</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              تحويل أي حادثة تشغيلية إلى خطة عمل من 3 مهام دقيقة (العزل الفوري، التحقق والتعافي، وتوثيق Runbook) وإرسالها مباشرة لحساب Google Tasks.
            </p>

            {incidents.length === 0 ? (
              <p className="text-xs text-slate-500">لا توجد حوادث مسجلة حالياً.</p>
            ) : (
              <div className="space-y-3">
                {incidents.slice(0, 4).map((inc) => (
                  <div
                    key={inc.id}
                    className="p-3 bg-slate-800/50 border border-slate-700/60 rounded-xl flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            inc.severity === 'critical'
                              ? 'bg-rose-500'
                              : inc.severity === 'warning'
                              ? 'bg-amber-500'
                              : 'bg-blue-500'
                          }`}
                        />
                        <span className="font-semibold text-slate-200 truncate">[{inc.code}]</span>
                      </div>
                      <p className="text-slate-400 truncate mt-0.5">{inc.message}</p>
                    </div>

                    <button
                      onClick={() => handleGenerateIncidentTasks(inc)}
                      className="px-2.5 py-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 text-xs font-medium border border-sky-500/30 whitespace-nowrap transition-colors flex items-center gap-1 shrink-0"
                    >
                      <span>توليد المهام</span>
                      <ArrowRight className="w-3 h-3 rotate-180" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* SRE Security Notice */}
          <div className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-start gap-3 text-xs text-slate-400">
            <ShieldCheck className="w-5 h-5 text-sky-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-slate-300">حوكمة المهام ومطابقة الأمان</p>
              <p className="mt-0.5 leading-relaxed text-slate-400">
                يتم إشعار المستخدم ومطالبته بالتأكيد الصريح قبل أي حذف أو تعديل أو إضافة للمهام لحماية سير العمليات.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Manual Task Creation Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-scaleUp">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <div className="flex items-center gap-2 text-white font-bold text-lg">
                <CheckSquare className="w-5 h-5 text-sky-400" />
                <span>إضافة مهمة جديدة إلى Google Tasks</span>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateTaskSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">عنوان المهمة</label>
                <input
                  type="text"
                  required
                  value={taskTitleInput}
                  onChange={(e) => setTaskTitleInput(e.target.value)}
                  placeholder="مثال: فحص شهادات SSL وتحديث مفاتيح التشفير"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500 placeholder-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">تفاصيل وملاحظات إضافية (اختياري)</label>
                <textarea
                  rows={3}
                  value={taskNotesInput}
                  onChange={(e) => setTaskNotesInput(e.target.value)}
                  placeholder="خطوات التنفيذ، روابط التوثيق، أسماء الخوادم المعنية..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500 placeholder-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">تاريخ الاستحقاق (اختياري)</label>
                <input
                  type="date"
                  value={taskDueInput}
                  onChange={(e) => setTaskDueInput(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:bg-slate-800 transition-colors"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl text-xs font-medium bg-sky-600 hover:bg-sky-500 text-white transition-all shadow-md shadow-sky-600/20"
                >
                  المتابعة إلى التأكيد
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Mandatory User Confirmation Modal */}
      {confirmationModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-scaleUp">
            <div className="flex items-center gap-3 text-sky-400 mb-3">
              <div
                className={`p-2.5 rounded-xl border ${
                  confirmationModal.confirmStyle === 'danger'
                    ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                    : 'bg-sky-500/10 border-sky-500/20 text-sky-400'
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
                إلغاء الأمر
              </button>
              <button
                type="button"
                onClick={confirmationModal.onConfirm}
                className={`px-5 py-2 rounded-xl text-xs font-medium text-white flex items-center gap-1.5 transition-all shadow-md ${
                  confirmationModal.confirmStyle === 'danger'
                    ? 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20'
                    : 'bg-sky-600 hover:bg-sky-500 shadow-sky-600/20'
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
