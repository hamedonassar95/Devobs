import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  FileText,
  Plus,
  RefreshCw,
  ExternalLink,
  Download,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FileCode,
  ShieldCheck,
  Eye,
  Check,
  X,
  Sparkles,
} from 'lucide-react';
import {
  listGoogleDocs,
  getGoogleDoc,
  createGoogleDoc,
  exportIncidentRcaToDoc,
  exportAuditReportToDoc,
  DocFileItem,
  DocumentDetails,
} from '../../services/googleDocsService';
import { googleSignIn } from '../../services/googleAuth';
import { Server, Incident } from '../../types/serverDashboard';

interface DocsTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  onAuthSuccess: (user: User, token: string) => void;
}

export function DocsTab({ user, token, servers, incidents, onAuthSuccess }: DocsTabProps) {
  const [docs, setDocs] = useState<DocFileItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inspector state
  const [selectedDocDetails, setSelectedDocDetails] = useState<DocumentDetails | null>(null);
  const [docTextContent, setDocTextContent] = useState<string>('');
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Export action state
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccessMsg, setExportSuccessMsg] = useState<string | null>(null);

  // Create Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [docTitleInput, setDocTitleInput] = useState('');
  const [docType, setDocType] = useState<'rca' | 'sop' | 'custom'>('rca');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>('');

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

  const loadDocs = async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const files = await listGoogleDocs(token);
      setDocs(files);
    } catch (err: any) {
      console.error('Failed to load Google Docs:', err);
      setError(err.message || 'فشل في استرجاع وثائق Google Docs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadDocs();
    }
  }, [token]);

  // Inspect Doc
  const handleInspectDoc = async (item: DocFileItem) => {
    if (!token) return;
    setIsLoadingDetails(true);
    try {
      const details = await getGoogleDoc(token, item.id);
      setSelectedDocDetails(details);

      // Extract plain text from Google Docs JSON AST
      let fullText = '';
      if (details.body?.content) {
        for (const elem of details.body.content) {
          if (elem.paragraph?.elements) {
            for (const pElem of elem.paragraph.elements) {
              if (pElem.textRun?.content) {
                fullText += pElem.textRun.content;
              }
            }
          }
        }
      }
      setDocTextContent(fullText || 'المستند فارغ حالياً.');
    } catch (err: any) {
      console.error('Inspect doc error:', err);
      alert(`تعذر جلب محتوى المستند: ${err.message}`);
    } finally {
      setIsLoadingDetails(false);
    }
  };

  // Create Doc with confirmation
  const handleConfirmCreateDoc = () => {
    let finalTitle = '';
    if (docType === 'rca') {
      const targetInc = incidents.find((i) => i.id === selectedIncidentId) || incidents[0];
      finalTitle = `تقرير تحليل السبب الجذري (RCA) - ${targetInc ? targetInc.code : 'INC-001'}`;
    } else if (docType === 'sop') {
      finalTitle = `إجراءات التشغيل القياسية (SOP Playbook) - ${new Date().toLocaleDateString('ar-EG')}`;
    } else {
      finalTitle = docTitleInput.trim() || 'وثيقة هندسية جديدة';
    }

    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد إنشاء مستند Google Docs جديد',
      description: `سيتم إنشاء مستند رسمي بعنوان "${finalTitle}" في مساحة Google Drive الخاصة بك. هل تود المتابعة؟`,
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        setIsExporting(true);
        setExportSuccessMsg(null);
        try {
          if (docType === 'rca') {
            const targetInc = incidents.find((i) => i.id === selectedIncidentId) || incidents[0];
            const res = await exportIncidentRcaToDoc(
              token!,
              targetInc,
              targetInc.aiAnalysis || 'تم توثيق الحادثة وخطوات التعافي بنجاح.'
            );
            setExportSuccessMsg(`تم بنجاح إنشاء تقرير الـ RCA وحفظه في Google Docs!`);
            if (res.webViewLink) window.open(res.webViewLink, '_blank');
          } else {
            const newDoc = await createGoogleDoc(token!, finalTitle);
            setExportSuccessMsg(`تم بنجاح إنشاء المستند الجديد!`);
            window.open(`https://docs.google.com/document/d/${newDoc.documentId}/edit`, '_blank');
          }

          setIsCreateModalOpen(false);
          await loadDocs();
        } catch (err: any) {
          alert(`فشل في إنشاء المستند: ${err.message}`);
        } finally {
          setIsExporting(false);
        }
      },
    });
  };

  if (!user || !token) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center max-w-xl mx-auto my-8 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center mx-auto mb-4">
          <FileText className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">ربط Google Docs</h3>
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          قم بتسجيل الدخول بحساب Google لتصدير تقارير تدقيق البنية التحتية، وتوليد وثائق تحليل الأسباب الجذرية (RCA Post-Mortem) الرسمية مباشرة في Google Docs.
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
          <div className="p-3 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              وثائق وتقارير Google Docs
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 font-medium">
                Google Docs API v1
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              تصدير تقارير التدقيق الهندسي، مذكرات تحليل الأعطال (Post-Mortems)، وإدارة الوثائق
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadDocs}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="تحديث المستندات"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg shadow-blue-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>إنشاء مستند جديد</span>
          </button>
        </div>
      </div>

      {exportSuccessMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {exportSuccessMsg}
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Main Grid: Docs List + Document Preview Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Files List */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center justify-between pb-1">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-400" />
              المستندات المتوفرة ({docs.length})
            </h4>
          </div>

          {isLoading ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-blue-400 mx-auto mb-2" />
              <p className="text-sm text-slate-400">جاري قراءة المستندات من Google Drive...</p>
            </div>
          ) : docs.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center space-y-3">
              <FileText className="w-10 h-10 text-slate-600 mx-auto stroke-[1.2]" />
              <p className="text-sm font-bold text-white">لا توجد مستندات Google Docs</p>
              <p className="text-xs text-slate-500">
                انقر على "إنشاء مستند جديد" لإنشاء أول تقرير أو مذكرة تشغيلية.
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[580px] overflow-y-auto">
              {docs.map((item) => (
                <div
                  key={item.id}
                  className={`p-3.5 rounded-xl border transition-all flex items-center justify-between gap-3 ${
                    selectedDocDetails?.documentId === item.id
                      ? 'bg-blue-950/30 border-blue-500/50 shadow'
                      : 'bg-slate-900 hover:bg-slate-800/80 border-slate-800'
                  }`}
                >
                  <div
                    className="flex items-center gap-2.5 cursor-pointer min-w-0"
                    onClick={() => handleInspectDoc(item)}
                  >
                    <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="truncate">
                      <h5 className="text-xs font-bold text-white hover:text-blue-400 truncate">
                        {item.name}
                      </h5>
                      <p className="text-[10px] text-slate-500 font-mono">
                        {item.modifiedTime ? new Date(item.modifiedTime).toLocaleDateString('ar-EG') : ''}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => handleInspectDoc(item)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                      title="عرض محتوى المستند"
                    >
                      <Eye className="w-3.5 h-3.5 text-blue-400" />
                    </button>

                    {item.webViewLink && (
                      <a
                        href={item.webViewLink}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                        title="فتح في Google Docs"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Document Content Viewer */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <FileCode className="w-4 h-4 text-blue-400" />
              {selectedDocDetails?.title || 'معاينة محتوى المستند'}
            </h4>
            {selectedDocDetails && (
              <a
                href={`https://docs.google.com/document/d/${selectedDocDetails.documentId}/edit`}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-blue-400 hover:underline flex items-center gap-1"
              >
                <ExternalLink className="w-3 h-3" />
                تحرير في Google Docs
              </a>
            )}
          </div>

          {isLoadingDetails ? (
            <div className="py-20 text-center text-slate-400 space-y-2">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-400" />
              <p className="text-xs">جاري جلب نص المستند من Google Docs API...</p>
            </div>
          ) : selectedDocDetails ? (
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 max-h-[500px] overflow-y-auto">
              <pre className="text-xs text-slate-200 whitespace-pre-wrap font-mono leading-relaxed">
                {docTextContent}
              </pre>
            </div>
          ) : (
            <div className="py-20 text-center text-slate-500 text-xs space-y-2">
              <FileText className="w-10 h-10 mx-auto text-slate-700 stroke-[1.2]" />
              <p>حدد مستنداً من القائمة الجانبية لقراءة نصوصه وهيكله الداخلي.</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Document Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" />
                إنشاء مستند تقرير جديد
              </h3>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  نوع التقرير المراد إنشاؤه:
                </label>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setDocType('rca')}
                    className={`p-2.5 rounded-xl border text-center transition-colors ${
                      docType === 'rca'
                        ? 'bg-blue-600/30 text-white border-blue-500 font-bold'
                        : 'bg-slate-950 text-slate-400 border-slate-800'
                    }`}
                  >
                    تقرير حادثة RCA
                  </button>
                  <button
                    type="button"
                    onClick={() => setDocType('sop')}
                    className={`p-2.5 rounded-xl border text-center transition-colors ${
                      docType === 'sop'
                        ? 'bg-blue-600/30 text-white border-blue-500 font-bold'
                        : 'bg-slate-950 text-slate-400 border-slate-800'
                    }`}
                  >
                    دليل تشغيلي SOP
                  </button>
                  <button
                    type="button"
                    onClick={() => setDocType('custom')}
                    className={`p-2.5 rounded-xl border text-center transition-colors ${
                      docType === 'custom'
                        ? 'bg-blue-600/30 text-white border-blue-500 font-bold'
                        : 'bg-slate-950 text-slate-400 border-slate-800'
                    }`}
                  >
                    مستند مخصص
                  </button>
                </div>
              </div>

              {docType === 'rca' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    اختر الحادثة المراد إعداد التقرير لها:
                  </label>
                  <select
                    value={selectedIncidentId}
                    onChange={(e) => setSelectedIncidentId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white outline-none focus:border-blue-500"
                  >
                    {incidents.map((inc) => (
                      <option key={inc.id} value={inc.id}>
                        [{inc.code}] {inc.serverName} - {inc.message.slice(0, 40)}...
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {docType === 'custom' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    عنوان المستند:
                  </label>
                  <input
                    type="text"
                    value={docTitleInput}
                    onChange={(e) => setDocTitleInput(e.target.value)}
                    placeholder="مثال: خطة ترقية قواعد البيانات للربع الأول"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white outline-none focus:border-blue-500"
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
                onClick={handleConfirmCreateDoc}
                disabled={isExporting}
                className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-blue-600/30"
              >
                {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                إنشاء المستند
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {confirmationModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30">
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
                className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-lg shadow-blue-600/30 transition-all flex items-center gap-1.5"
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
