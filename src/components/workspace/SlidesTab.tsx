import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  Presentation,
  Plus,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  Eye,
  Check,
  X,
  Sparkles,
  Layers,
  FileCheck,
} from 'lucide-react';
import {
  listGooglePresentations,
  getPresentationDetails,
  createPresentation,
  exportIncidentToSlideDeck,
  exportExecutiveReportToSlideDeck,
  GoogleSlidePresentation,
  SlidePresentationDetails,
} from '../../services/googleSlidesService';
import { googleSignIn } from '../../services/googleAuth';
import { Server, Incident } from '../../types/serverDashboard';

interface SlidesTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  onAuthSuccess: (user: User, token: string) => void;
}

export function SlidesTab({ user, token, servers, incidents, onAuthSuccess }: SlidesTabProps) {
  const [presentations, setPresentations] = useState<GoogleSlidePresentation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inspector state
  const [selectedDeckDetails, setSelectedDeckDetails] = useState<SlidePresentationDetails | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Creation / Export state
  const [isProcessing, setIsProcessing] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Create Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [deckTitleInput, setDeckTitleInput] = useState('');
  const [deckType, setDeckType] = useState<'incident' | 'executive' | 'blank'>('incident');
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

  const fetchPresentations = async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const list = await listGooglePresentations(token);
      setPresentations(list);
    } catch (err: any) {
      console.error('Error fetching Google Slides:', err);
      setError(err.message || 'فشل جلب عروض التقديم من Google Slides');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchPresentations();
    }
  }, [token]);

  const handleInspectDeck = async (deckId: string) => {
    if (!token) return;
    setIsLoadingDetails(true);
    setSelectedDeckDetails(null);
    try {
      const details = await getPresentationDetails(token, deckId);
      setSelectedDeckDetails(details);
    } catch (err: any) {
      console.error('Failed to load presentation details:', err);
      setError('تعذر تحميل تفاصيل شرائح العرض التقديمي.');
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const handleConnectGoogle = async () => {
    try {
      setError(null);
      const res = await googleSignIn();
      if (res) {
        onAuthSuccess(res.user, res.accessToken);
      }
    } catch (err: any) {
      setError('فشل تسجيل الدخول أو إعطاء أذونات Google Slides: ' + err.message);
    }
  };

  const executeExportExecutiveDeck = async () => {
    if (!token) return;
    setIsProcessing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const result = await exportExecutiveReportToSlideDeck(token, servers, incidents);
      setSuccessMsg(`تم توليد العرض التقديمي التنفيذي بنجاح!`);
      await fetchPresentations();
      if (result.presentationId) {
        handleInspectDeck(result.presentationId);
      }
    } catch (err: any) {
      setError('فشل توليد عرض القيادة التنفيذية: ' + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const executeExportIncidentDeck = async (incident: Incident) => {
    if (!token) return;
    setIsProcessing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const targetServer = servers.find((s) => s.id === incident.serverId);
      const result = await exportIncidentToSlideDeck(token, incident, targetServer);
      setSuccessMsg(`تم توليد عرض تقرير الحادثة "${incident.code}" بنجاح!`);
      await fetchPresentations();
      if (result.presentationId) {
        handleInspectDeck(result.presentationId);
      }
    } catch (err: any) {
      setError('فشل توليد شرائح الحادثة: ' + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const executeCreateBlankDeck = async (title: string) => {
    if (!token) return;
    setIsProcessing(true);
    setError(null);
    try {
      const result = await createPresentation(token, title);
      setSuccessMsg(`تم إنشاء العرض التقديمي "${title}" بنجاح!`);
      await fetchPresentations();
      if (result.presentationId) {
        handleInspectDeck(result.presentationId);
      }
    } catch (err: any) {
      setError('فشل إنشاء العرض التقديمي: ' + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  // Trigger confirmation modal for Executive Deck
  const promptExecutiveDeckExport = () => {
    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد إنشاء عرض تقديمي تنفيذي (Google Slides)',
      description: `سيقوم النظام بإنشاء ملف عرض تقديمي جديد في Google Slides يحتوي على مؤشرات جهوزية ${servers.length} خادم، وإحصائيات الحوادث وتوزيع الموارد. هل ترغب في المتابعة؟`,
      onConfirm: () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        executeExportExecutiveDeck();
      },
    });
  };

  // Trigger confirmation modal for Incident Deck
  const promptIncidentDeckExport = (inc: Incident) => {
    setConfirmationModal({
      isOpen: true,
      title: `تأكيد توليد شرائح حادثة SRE: ${inc.code}`,
      description: `سيتم إنشاء عرض تقديمي متكامل للحادثة "${inc.message}" يشمل تحليل السبب الجذري والآثار المترتبة وإجراءات التعافي في حساب Google Slides الخاص بك.`,
      onConfirm: () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        executeExportIncidentDeck(inc);
      },
    });
  };

  // Handle Create Modal submit
  const handleModalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreateModalOpen(false);

    if (deckType === 'executive') {
      promptExecutiveDeckExport();
    } else if (deckType === 'incident') {
      const targetInc = incidents.find((i) => i.id === selectedIncidentId) || incidents[0];
      if (!targetInc) {
        setError('يرجى تحديد حادثة لإنشاء عرض تقديمي خاص بها.');
        return;
      }
      promptIncidentDeckExport(targetInc);
    } else {
      const title = deckTitleInput.trim() || 'عرض تقديمي جديد لمنظومة DevOps';
      setConfirmationModal({
        isOpen: true,
        title: 'تأكيد إنشاء عرض تقديمي جديد',
        description: `سيتم إنشاء ملف Google Slides بعنوان "${title}".`,
        onConfirm: () => {
          setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
          executeCreateBlankDeck(title);
        },
      });
    }
  };

  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] p-8 text-center bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-4 text-amber-400">
          <Presentation className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">ربط Google Slides™ بالمنظومة السحابية</h2>
        <p className="text-slate-400 max-w-lg mb-6 text-sm leading-relaxed">
          قم بتسجيل الدخول بحساب Google Workspace لتمكين توليد عروض الشرائح التفاعلية لتقارير الحوادث، واجتماعات SRE الأسبوعية، وعروض الجاهزية التشغيلية للقيادة.
        </p>
        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm max-w-md flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <button
          onClick={handleConnectGoogle}
          className="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-medium rounded-xl shadow-lg shadow-amber-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <Presentation className="w-5 h-5" />
          <span>تسجيل الدخول وربط Google Slides</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-slate-900/70 border border-slate-800 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-inner">
            <Presentation className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white">عروض Google Slides™ الهندسية</h2>
              <span className="px-2 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                Workspace مفعّل
              </span>
            </div>
            <p className="text-sm text-slate-400">
              توليد عروض الشرائح وتقارير الحوادث وعروض الجاهزية التنفيذية بضغطة زر واحدة مع تأكيد تفاعلي
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={fetchPresentations}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm transition-all border border-slate-700 disabled:opacity-50"
            title="تحديث قائمة العروض"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-amber-400' : ''}`} />
            <span>تحديث</span>
          </button>

          <button
            onClick={promptExecutiveDeckExport}
            disabled={isProcessing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-medium shadow-md shadow-emerald-600/20 transition-all border border-emerald-500/30 disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>عرض القيادة التنفيذية</span>
          </button>

          <button
            onClick={() => {
              setDeckTitleInput('');
              setDeckType('incident');
              if (incidents.length > 0) setSelectedIncidentId(incidents[0].id);
              setIsCreateModalOpen(true);
            }}
            disabled={isProcessing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white text-sm font-medium shadow-md shadow-amber-600/20 transition-all border border-amber-500/30 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            <span>توليد شرائح جديدة</span>
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

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Presentations List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-amber-400" />
              <span>عروض Google Slides المسجلة ({presentations.length})</span>
            </h3>
            <span className="text-xs text-slate-400">انقر على أي عرض لعرض محتواه وتفاصيل شرائحه</span>
          </div>

          {isLoading ? (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 rounded-2xl border border-slate-800">
              <Loader2 className="w-8 h-8 animate-spin text-amber-400 mb-3" />
              <p className="text-sm text-slate-400">جاري الاتصال بـ Google Slides وجلب العروض...</p>
            </div>
          ) : presentations.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 rounded-2xl border border-dashed border-slate-800 text-center">
              <Presentation className="w-12 h-12 text-slate-600 mb-3" />
              <h4 className="text-base font-medium text-slate-300 mb-1">لا توجد عروض تقديمية في حسابك بعد</h4>
              <p className="text-sm text-slate-500 max-w-sm mb-4">
                ابدأ بتوليد عرض تنفيذي أو تقرير شرائح لحادثة SRE وسيتم إدراجه هنا مباشرة.
              </p>
              <button
                onClick={promptExecutiveDeckExport}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-amber-400 text-sm rounded-xl border border-slate-700 transition-colors"
              >
                توليد عرض تنفيذي تجريبي
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {presentations.map((deck) => {
                const isSelected = selectedDeckDetails?.presentationId === deck.id;
                return (
                  <div
                    key={deck.id}
                    onClick={() => handleInspectDeck(deck.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                      isSelected
                        ? 'bg-amber-950/20 border-amber-500/50 shadow-lg shadow-amber-950/30 ring-1 ring-amber-500/30'
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80'
                    }`}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            <Presentation className="w-5 h-5" />
                          </div>
                          <div>
                            <h4 className="font-semibold text-slate-100 text-sm line-clamp-1">{deck.name}</h4>
                            <p className="text-xs text-slate-500">
                              {deck.modifiedTime ? new Date(deck.modifiedTime).toLocaleDateString('ar-EG') : 'حديث'}
                            </p>
                          </div>
                        </div>
                        {isSelected && (
                          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
                        )}
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleInspectDeck(deck.id);
                        }}
                        className="text-amber-400 hover:text-amber-300 flex items-center gap-1 font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>معاينة الشرائح</span>
                      </button>

                      {deck.webViewLink && (
                        <a
                          href={deck.webViewLink}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-slate-400 hover:text-slate-200 flex items-center gap-1 bg-slate-800/60 px-2.5 py-1 rounded-md border border-slate-700/60"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span>فتح في Slides</span>
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Quick Incident Export Section */}
          <div className="p-5 bg-slate-900/50 border border-slate-800 rounded-2xl mt-6">
            <h4 className="font-semibold text-slate-200 text-sm mb-3 flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-emerald-400" />
              <span>توليد شرائح فورية للحوادث المسجلة ({incidents.length})</span>
            </h4>
            {incidents.length === 0 ? (
              <p className="text-xs text-slate-500">لا توجد حوادث مسجلة حالياً لتوليد شرائح لها.</p>
            ) : (
              <div className="space-y-2">
                {incidents.slice(0, 3).map((inc) => (
                  <div
                    key={inc.id}
                    className="p-3 bg-slate-800/40 border border-slate-800 rounded-xl flex items-center justify-between gap-4"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            inc.severity === 'critical'
                              ? 'bg-rose-500'
                              : inc.severity === 'warning'
                              ? 'bg-amber-500'
                              : 'bg-blue-500'
                          }`}
                        />
                        <h5 className="text-sm font-medium text-slate-200 truncate">[{inc.code}] {inc.message}</h5>
                      </div>
                      <p className="text-xs text-slate-500 truncate mt-0.5">{inc.stackTrace || inc.message}</p>
                    </div>
                    <button
                      onClick={() => promptIncidentDeckExport(inc)}
                      disabled={isProcessing}
                      className="px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs font-medium border border-amber-500/30 whitespace-nowrap transition-colors"
                    >
                      توليد العرض
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Deck Inspector & Slide Preview */}
        <div className="space-y-4">
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl min-h-[480px] flex flex-col">
            <h3 className="font-semibold text-slate-200 text-sm pb-3 border-b border-slate-800 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-amber-400" />
                <span>معاينة العرض التقديمي</span>
              </span>
              {selectedDeckDetails && (
                <span className="text-xs text-slate-400">
                  {selectedDeckDetails.slides?.length || 0} شريحة
                </span>
              )}
            </h3>

            {isLoadingDetails ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <Loader2 className="w-7 h-7 animate-spin text-amber-400 mb-2" />
                <p className="text-xs text-slate-400">جاري قراءة بنية الشرائح...</p>
              </div>
            ) : selectedDeckDetails ? (
              <div className="flex-1 flex flex-col justify-between pt-4 space-y-4">
                <div>
                  <h4 className="text-base font-bold text-white mb-2 leading-snug">
                    {selectedDeckDetails.title}
                  </h4>
                  <div className="flex items-center gap-2 text-xs text-slate-400 mb-4">
                    <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                      ID: {selectedDeckDetails.presentationId.slice(0, 14)}...
                    </span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                      جاهز للعرض
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    <p className="text-xs font-medium text-slate-300">محتويات الشرائح المنشأة:</p>
                    {selectedDeckDetails.slides?.map((slide, idx) => (
                      <div
                        key={slide.objectId || idx}
                        className="p-3 bg-slate-800/60 rounded-xl border border-slate-700/60 text-xs text-slate-300 flex items-start gap-2.5"
                      >
                        <div className="w-5 h-5 rounded bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">
                          {idx + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-slate-200">
                            {idx === 0
                              ? 'شريحة العنوان والملخص'
                              : idx === 1
                              ? 'شريحة التحليل والسبب الجذري'
                              : idx === 2
                              ? 'شريحة الإجراءات الوقائية وخطة العمل'
                              : `شريحة ${idx + 1}`}
                          </p>
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            عناصر الشريحة: {slide.pageElements?.length || 0} عنصر نصوص وتخطيط
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-800">
                  <a
                    href={`https://docs.google.com/presentation/d/${selectedDeckDetails.presentationId}/edit`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition-all shadow-md shadow-amber-600/20"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>فتح وتعديل العرض في Google Slides</span>
                  </a>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
                <Presentation className="w-10 h-10 mb-2 opacity-30 text-amber-400" />
                <p className="text-xs">حدد أي عرض تقديمي من القائمة لعرض تفاصيل شرائحه وروابط التعديل الحية.</p>
              </div>
            )}
          </div>

          {/* SRE Integration Notice */}
          <div className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl flex items-start gap-3 text-xs text-slate-400">
            <ShieldCheck className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-slate-300">أمان وحوكمة Google Workspace</p>
              <p className="mt-0.5 leading-relaxed text-slate-400">
                تتم كافة العمليات عبر واجهات Google Slides API الرسمية مع التأكيد الصريح قبل أي تعديل على حسابك، لضمان أعلى معايير أمان البيانات التشغيلية.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Creation Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full shadow-2xl animate-scaleUp">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <div className="flex items-center gap-2 text-white font-bold text-lg">
                <Presentation className="w-5 h-5 text-amber-400" />
                <span>إنشاء عرض شرائح جديد في Google Slides</span>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleModalSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">نوع العرض التقديمي</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setDeckType('incident')}
                    className={`py-2 px-3 rounded-xl text-xs font-medium border text-center transition-all ${
                      deckType === 'incident'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    تقرير حادثة SRE
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeckType('executive')}
                    className={`py-2 px-3 rounded-xl text-xs font-medium border text-center transition-all ${
                      deckType === 'executive'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    عرض تنفيذي شامل
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeckType('blank')}
                    className={`py-2 px-3 rounded-xl text-xs font-medium border text-center transition-all ${
                      deckType === 'blank'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    عرض مخصص فارغ
                  </button>
                </div>
              </div>

              {deckType === 'incident' && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">اختر الحادثة المستهدفة</label>
                  <select
                    value={selectedIncidentId}
                    onChange={(e) => setSelectedIncidentId(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  >
                    {incidents.map((inc) => (
                      <option key={inc.id} value={inc.id}>
                        [{inc.code}] {inc.message}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {deckType === 'blank' && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">عنوان العرض التقديمي</label>
                  <input
                    type="text"
                    required
                    value={deckTitleInput}
                    onChange={(e) => setDeckTitleInput(e.target.value)}
                    placeholder="مثال: خطة التوسع والتوزيع السحابي للربع الثالث"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500 placeholder-slate-500"
                  />
                </div>
              )}

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
                  className="px-5 py-2 rounded-xl text-xs font-medium bg-amber-600 hover:bg-amber-500 text-white transition-all shadow-md shadow-amber-600/20"
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
            <div className="flex items-center gap-3 text-amber-400 mb-3">
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
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
                className="px-5 py-2 rounded-xl text-xs font-medium bg-amber-600 hover:bg-amber-500 text-white flex items-center gap-1.5 transition-all shadow-md shadow-amber-600/20"
              >
                <Check className="w-4 h-4" />
                <span>تأكيد وإنشاء الشرائح</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
