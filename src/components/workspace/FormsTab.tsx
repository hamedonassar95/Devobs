import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  FileText,
  Plus,
  RefreshCw,
  ExternalLink,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Send,
  Loader2,
  MessageSquare,
  ShieldCheck,
  Server as ServerIcon,
  HelpCircle,
  Users,
  Eye,
  Check,
  X,
} from 'lucide-react';
import {
  listGoogleForms,
  getGoogleForm,
  getGoogleFormResponses,
  createGoogleForm,
  deleteGoogleForm,
  GoogleFormItem,
  FormDetails,
  FormResponseItem,
} from '../../services/googleFormsService';
import { googleSignIn } from '../../services/googleAuth';
import { Server, Incident } from '../../types/serverDashboard';

interface FormsTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  onAuthSuccess: (user: User, token: string) => void;
}

export function FormsTab({ user, token, servers, incidents, onAuthSuccess }: FormsTabProps) {
  const [forms, setForms] = useState<GoogleFormItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected form for inspection & responses
  const [selectedForm, setSelectedForm] = useState<FormDetails | null>(null);
  const [responses, setResponses] = useState<FormResponseItem[]>([]);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Create Form Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [templateType, setTemplateType] = useState<'incident' | 'access' | 'deployment' | 'custom'>('incident');
  const [customTitle, setCustomTitle] = useState('');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>('');
  const [isCreating, setIsCreating] = useState(false);

  // Confirmation Modal
  const [confirmationModal, setConfirmationModal] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    description: '',
    onConfirm: () => {},
  });

  const loadForms = async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const items = await listGoogleForms(token);
      setForms(items);
    } catch (err: any) {
      console.error('Failed to load Google Forms:', err);
      setError(err.message || 'فشل في تحميل نماذج Google');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadForms();
    }
  }, [token]);

  // View Form Details and Responses
  const handleInspectForm = async (formItem: GoogleFormItem) => {
    if (!token) return;
    setIsLoadingDetails(true);
    try {
      const details = await getGoogleForm(token, formItem.id);
      setSelectedForm(details);
      try {
        const respList = await getGoogleFormResponses(token, formItem.id);
        setResponses(respList);
      } catch (e) {
        console.warn('Responses read error:', e);
        setResponses([]);
      }
    } catch (err: any) {
      console.error('Inspect form error:', err);
      alert(`تعذر جلب تفاصيل النموذج: ${err.message}`);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  // Trigger Create Form with explicit confirmation
  const handleConfirmCreateForm = () => {
    let formTitle = '';
    let questions: { title: string; required?: boolean; type?: 'text' | 'choice'; options?: string[] }[] = [];

    if (templateType === 'incident') {
      const targetInc = incidents.find((i) => i.id === selectedIncidentId) || incidents[0];
      formTitle = `استبيان ما بعد الحادث (Post-Mortem Review) - ${targetInc ? targetInc.code : 'INC-001'}`;
      questions = [
        { title: 'ما هو السبب الجذري الفعلي للحادثة بحسب تقييمك؟', required: true, type: 'text' },
        { title: 'هل كانت أدوات المراقبة كافية لاكتشاف العطل مبكراً؟', required: true, type: 'choice', options: ['نعم بالكامل', 'إلى حد ما', 'لا، تأخر التنبيه'] },
        { title: 'ما هو الإجراء الوقائي الدائم لمنع تكرار الحادث؟', required: true, type: 'text' },
        { title: 'تقييم كفاءة التنسيق وسرعة الاستجابة الهندسية:', required: true, type: 'choice', options: ['ممتاز (أقل من 15 دقيقة)', 'مقبول (15 - 45 دقيقة)', 'بطيء (أكثر من 45 دقيقة)'] },
      ];
    } else if (templateType === 'access') {
      formTitle = 'طلب صلاحيات وصول استثنائي للخادم (Server Access Request)';
      questions = [
        { title: 'اسم المطور / المهندس صاحب الطلب:', required: true, type: 'text' },
        { title: 'الخادم المطلوب منحه الصلاحية:', required: true, type: 'choice', options: servers.map((s) => `${s.name} (${s.ip})`) },
        { title: 'نوع الصلاحية المطلوبة:', required: true, type: 'choice', options: ['وصول SSH مؤقت', 'صلاحيات Sudo / Root', 'تعديل قواعد الجدار الناري', 'قراءة السجلات فقط'] },
        { title: 'المبرر الفني وتفاصيل المهمة:', required: true, type: 'text' },
        { title: 'المدة المقدرة بالساعات:', required: true, type: 'text' },
      ];
    } else if (templateType === 'deployment') {
      formTitle = 'نموذج موافقة نشر الإنتاج (Production Deployment Sign-Off)';
      questions = [
        { title: 'رقم الإصدار والخدمة المراد ترقيتها:', required: true, type: 'text' },
        { title: 'هل اجتاز الإصدار كافة اختبارات التكامل الآلية (CI/CD)؟', required: true, type: 'choice', options: ['نعم، بنجاح 100%', 'تجاوز يدوي معتمد'] },
        { title: 'هل تم اختبار خطة التراجع (Rollback Plan)؟', required: true, type: 'choice', options: ['نعم، جاهزة وتلقائية', 'لا توجد خطة تراجع'] },
        { title: 'توقيع موافقة مهندس المناوبة:', required: true, type: 'text' },
      ];
    } else {
      formTitle = customTitle.trim() || 'نموذج عمليات DevOps مخصص';
      questions = [
        { title: 'السؤال الأول:', required: true, type: 'text' },
        { title: 'الملاحظات الإضافية:', required: false, type: 'text' },
      ];
    }

    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد إنشاء نموذج Google Form جديد',
      description: `أنت على وشك إنشاء نموذج جديد بعنوان "${formTitle}" يتضمن ${questions.length} أسئلة في حساب Google الخاص بك. هل تود المتابعة؟`,
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        setIsCreating(true);
        try {
          await createGoogleForm(token!, formTitle, formTitle, questions);
          setIsCreateModalOpen(false);
          await loadForms();
        } catch (err: any) {
          alert(`فشل في إنشاء النموذج: ${err.message}`);
        } finally {
          setIsCreating(false);
        }
      },
    });
  };

  // Delete Form with confirmation
  const handleDeleteForm = (formItem: GoogleFormItem) => {
    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد حذف النموذج',
      description: `هل أنت متأكد من حذف النموذج "${formItem.name}"؟ سيتم نقل الملف إلى سلة مهملات Google Drive.`,
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        try {
          await deleteGoogleForm(token!, formItem.id);
          if (selectedForm?.formId === formItem.id) {
            setSelectedForm(null);
            setResponses([]);
          }
          await loadForms();
        } catch (err: any) {
          alert(`فشل في حذف النموذج: ${err.message}`);
        }
      },
    });
  };

  if (!user || !token) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center max-w-xl mx-auto my-8 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center mx-auto mb-4">
          <FileText className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">ربط Google Forms</h3>
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          قم بتسجيل الدخول بحساب Google لإنشاء وإدارة نماذج استبيانات ما بعد الأعطال (Post-Mortem)، طلبات الصلاحيات، وموافقات النشر التلقائية.
        </p>

        <button
          onClick={async () => {
            try {
              const res = await googleSignIn();
              if (res) onAuthSuccess(res.user, res.accessToken);
            } catch (e: any) {
              alert('فشل في تسجيل الدخول: ' + e.message);
            }
          }}
          className="px-6 py-3 bg-white text-slate-900 hover:bg-slate-100 rounded-xl font-bold text-sm shadow-lg transition-all inline-flex items-center gap-2"
        >
          <span>تسجيل الدخول باستخدام Google</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              نماذج واستبيانات Google Forms
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30 font-medium">
                Google Workspace API
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              إنشاء استبيانات ما بعد الأعطال، موافقات ترقيات الإنتاج، وطلبات وصول الخوادم
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadForms}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="تحديث قائمة النماذج"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>إنشاء نموذج جديد</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Main Grid: Form List + Form Details Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Forms List */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between pb-1">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-400" />
              النماذج المتوفرة في حسابك ({forms.length})
            </h4>
          </div>

          {isLoading ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto mb-2" />
              <p className="text-sm text-slate-400">جاري تحميل النماذج من Google Forms...</p>
            </div>
          ) : forms.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
              <FileText className="w-12 h-12 text-slate-600 mx-auto stroke-[1.2]" />
              <p className="text-sm font-bold text-white">لم يتم العثور على أي نماذج Google</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                يمكنك إنشاء أول نموذج لاستبيان الأعطال أو طلبات وصول الخوادم بالنقر على "إنشاء نموذج جديد" أعلاه.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {forms.map((item) => (
                <div
                  key={item.id}
                  className={`p-4 rounded-xl border transition-all flex items-center justify-between gap-4 ${
                    selectedForm?.formId === item.id
                      ? 'bg-purple-950/30 border-purple-500/50 shadow-md'
                      : 'bg-slate-900 hover:bg-slate-800/80 border-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <h5 className="text-sm font-bold text-white hover:text-purple-400 cursor-pointer" onClick={() => handleInspectForm(item)}>
                        {item.name}
                      </h5>
                      <p className="text-xs text-slate-500">
                        آخر تعديل: {item.modifiedTime ? new Date(item.modifiedTime).toLocaleDateString('ar-EG') : 'غير محدد'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleInspectForm(item)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      title="فحص الأسئلة والردود"
                    >
                      <Eye className="w-3.5 h-3.5 text-purple-400" />
                      <span>فحص</span>
                    </button>

                    {item.webViewLink && (
                      <a
                        href={item.webViewLink}
                        target="_blank"
                        rel="noreferrer"
                        className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                        title="فتح النموذج في Google Forms"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}

                    <button
                      onClick={() => handleDeleteForm(item)}
                      className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs transition-colors"
                      title="حذف النموذج"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Col: Form Details & Submissions Inspector */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-purple-400" />
              تفاصيل النموذج والردود
            </h4>
            {selectedForm && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
                {responses.length} ردود
              </span>
            )}
          </div>

          {isLoadingDetails ? (
            <div className="py-12 text-center text-slate-400 space-y-2">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-purple-400" />
              <p className="text-xs">جاري جلب تفاصيل النموذج والردود...</p>
            </div>
          ) : selectedForm ? (
            <div className="space-y-4 text-xs">
              <div>
                <h5 className="font-bold text-white text-sm mb-1">{selectedForm.info?.title}</h5>
                {selectedForm.info?.description && (
                  <p className="text-slate-400">{selectedForm.info.description}</p>
                )}
              </div>

              {selectedForm.responderUri && (
                <div className="p-3 rounded-xl bg-purple-950/40 border border-purple-500/30 space-y-1.5">
                  <span className="text-[11px] font-semibold text-purple-300 block">رابط استجابة النموذج (للجمهور):</span>
                  <a
                    href={selectedForm.responderUri}
                    target="_blank"
                    rel="noreferrer"
                    className="text-purple-400 hover:underline break-all block font-mono text-[11px]"
                  >
                    {selectedForm.responderUri}
                  </a>
                </div>
              )}

              {/* Questions list */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <span className="font-semibold text-slate-300 block">
                  الأسئلة المسجلة في النموذج ({selectedForm.items?.length || 0}):
                </span>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {selectedForm.items?.map((q, idx) => (
                    <div key={idx} className="p-2 bg-slate-950 rounded-lg border border-slate-800 text-slate-300 flex items-start gap-2">
                      <span className="text-purple-400 font-mono font-bold">{idx + 1}.</span>
                      <span>{q.title || 'سؤال بدون عنوان'}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Live Responses summary */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <span className="font-semibold text-slate-300 block">
                  آخر الاستجابات المسجلة:
                </span>
                {responses.length === 0 ? (
                  <p className="text-slate-500 text-xs">لم يتم تسجيل أي ردود بعد.</p>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {responses.slice(0, 5).map((resp, i) => (
                      <div key={i} className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-300 space-y-1">
                        <div className="flex items-center justify-between text-slate-500">
                          <span>رد #{i + 1}</span>
                          <span>{new Date(resp.lastSubmittedTime || resp.createTime).toLocaleTimeString('ar-EG')}</span>
                        </div>
                        <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                          <CheckCircle2 className="w-3 h-3" />
                          تم الإرسال بنجاح
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs">
              حدد أي نموذج من القائمة لعرض تفاصيله ورابط المشاركة والردود الحية.
            </div>
          )}
        </div>
      </div>

      {/* Create Form Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-400" />
                إنشاء نموذج Google Form جديد
              </h3>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  اختر قالب النموذج الجاهز (DevOps Templates):
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setTemplateType('incident')}
                    className={`p-3 rounded-xl border text-right transition-colors ${
                      templateType === 'incident'
                        ? 'bg-purple-600/30 text-white border-purple-500'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    <div className="font-bold flex items-center gap-1.5 text-purple-400 mb-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      استبيان ما بعد الحادث
                    </div>
                    <span className="text-[11px] text-slate-400">Post-Mortem Review</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setTemplateType('access')}
                    className={`p-3 rounded-xl border text-right transition-colors ${
                      templateType === 'access'
                        ? 'bg-purple-600/30 text-white border-purple-500'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    <div className="font-bold flex items-center gap-1.5 text-cyan-400 mb-1">
                      <ServerIcon className="w-3.5 h-3.5" />
                      طلب وصول للخادم
                    </div>
                    <span className="text-[11px] text-slate-400">Server Access Request</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setTemplateType('deployment')}
                    className={`p-3 rounded-xl border text-right transition-colors ${
                      templateType === 'deployment'
                        ? 'bg-purple-600/30 text-white border-purple-500'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    <div className="font-bold flex items-center gap-1.5 text-emerald-400 mb-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      موافقة نشر الإنتاج
                    </div>
                    <span className="text-[11px] text-slate-400">Deployment Sign-Off</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setTemplateType('custom')}
                    className={`p-3 rounded-xl border text-right transition-colors ${
                      templateType === 'custom'
                        ? 'bg-purple-600/30 text-white border-purple-500'
                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    <div className="font-bold flex items-center gap-1.5 text-indigo-400 mb-1">
                      <HelpCircle className="w-3.5 h-3.5" />
                      نموذج مخصص
                    </div>
                    <span className="text-[11px] text-slate-400">Custom Survey Form</span>
                  </button>
                </div>
              </div>

              {templateType === 'incident' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    اختر الحادثة المراد ربط الاستبيان بها:
                  </label>
                  <select
                    value={selectedIncidentId}
                    onChange={(e) => setSelectedIncidentId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white outline-none focus:border-purple-500"
                  >
                    {incidents.map((inc) => (
                      <option key={inc.id} value={inc.id}>
                        [{inc.code}] {inc.serverName} - {inc.message.slice(0, 45)}...
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {templateType === 'custom' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    عنوان النموذج المخصص:
                  </label>
                  <input
                    type="text"
                    value={customTitle}
                    onChange={(e) => setCustomTitle(e.target.value)}
                    placeholder="مثال: استطلاع آراء فريق العمليات حول البنية التحتية"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white outline-none focus:border-purple-500"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
              >
                إلغاء
              </button>
              <button
                type="button"
                onClick={handleConfirmCreateForm}
                disabled={isCreating}
                className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-600/30"
              >
                {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                إنشاء النموذج
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mandatory User Confirmation Modal */}
      {confirmationModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">{confirmationModal.title}</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {confirmationModal.description}
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setConfirmationModal((prev) => ({ ...prev, isOpen: false }))}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition-colors"
              >
                إلغاء
              </button>
              <button
                onClick={confirmationModal.onConfirm}
                className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-lg shadow-purple-600/30 transition-all flex items-center gap-1.5"
              >
                <Check className="w-4 h-4" />
                تأكيد الإجراء
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
