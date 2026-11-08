import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  listChatSpaces,
  sendChatMessage,
  ChatSpace,
} from '../../services/chatService';
import { googleSignIn } from '../../services/googleAuth';
import { Server, Incident, Deployment } from '../../types/serverDashboard';
import {
  MessageSquare,
  Send,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Users,
  ShieldCheck,
  Loader2,
  Info,
  Rocket,
  ShieldAlert,
} from 'lucide-react';

interface ChatTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  deployments: Deployment[];
  onAuthSuccess: (user: User, token: string) => void;
}

export const ChatTab: React.FC<ChatTabProps> = ({
  user,
  token,
  servers,
  incidents,
  deployments,
  onAuthSuccess,
}) => {
  const [spaces, setSpaces] = useState<ChatSpace[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSpace, setSelectedSpace] = useState<string>('');
  const [messageText, setMessageText] = useState('');
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' | 'warning' } | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [consoleHelpUrl, setConsoleHelpUrl] = useState<string | null>(null);

  // Confirmation Modal state (Mandatory for sending chat messages)
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);

  const fetchSpaces = async () => {
    if (!token) return;
    setLoading(true);
    setStatusMessage(null);
    setConsoleHelpUrl(null);
    try {
      const fetchedSpaces = await listChatSpaces(token);
      setSpaces(fetchedSpaces);
      if (fetchedSpaces.length > 0 && !selectedSpace) {
        setSelectedSpace(fetchedSpaces[0].name);
      }
    } catch (err: any) {
      console.warn('Google Chat space listing notice:', err);
      const msg = err.message || 'تعذر جلب غرف Google Chat';
      if (msg.includes('Google Chat app not found') || msg.includes('console.cloud.google.com')) {
        setConsoleHelpUrl(
          'https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat?project=warm-aegis-350823'
        );
        setStatusMessage({
          text: 'ملاحظة تشغيلية: يتطلب Google Chat API تفعيل واجهة التطبيق في Google Cloud Console واستخدام حساب Google Workspace مؤسسي.',
          type: 'warning',
        });
      } else if (msg.includes('Google Workspace')) {
        setStatusMessage({
          text: msg,
          type: 'warning',
        });
      } else {
        setStatusMessage({ text: msg, type: 'error' });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchSpaces();
    }
  }, [token]);

  const handleSignIn = async () => {
    try {
      const result = await googleSignIn();
      if (result) {
        onAuthSuccess(result.user, result.accessToken);
        setStatusMessage({ text: 'تم ربط Google Chat بنجاح!', type: 'success' });
      }
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'تعذر تسجيل الدخول', type: 'error' });
    }
  };

  const handlePrepareIncidentAlert = (incident: Incident) => {
    setMessageText(
      `🚨 [SERVEROPS ALERT - ${incident.severity.toUpperCase()}]
عطل تشغيلي في الخادم: *${incident.serverName}*
كود الخطأ: \`${incident.code}\`
التوقيت: ${incident.timestamp}
الرسالة: ${incident.message}
رابط لوحة التحكم: متابعة فورية لحل المشكلة`
    );
  };

  const handlePrepareDeploymentAlert = (dep: Deployment) => {
    setMessageText(
      `🚀 [CI/CD DEPLOYMENT UPDATE]
تم تنفيذ نشر جديد للإصدار: *${dep.version}*
الخدمة: \`${dep.serviceName}\` (${dep.branch})
الحالة: ${dep.status === 'successful' ? '✅ ناجح' : '❌ فشل'}
المسؤول: ${dep.author}
سجل التغيير: ${dep.changeLog}`
    );
  };

  const handleSendMessageConfirmed = async () => {
    if (!token || !selectedSpace || !messageText.trim()) return;
    setIsSending(true);
    try {
      await sendChatMessage(token, selectedSpace, messageText.trim());
      setIsConfirmModalOpen(false);
      setMessageText('');
      setStatusMessage({
        text: 'تم إرسال التنبيه بنجاح إلى غرفة Google Chat!',
        type: 'success',
      });
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'فشل إرسال الرسالة إلى Google Chat', type: 'error' });
    } finally {
      setIsSending(false);
    }
  };

  if (!token || !user) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center max-w-2xl mx-auto shadow-xl space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-emerald-950/80 border border-emerald-800/80 flex items-center justify-center mx-auto text-emerald-400">
          <MessageSquare className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h3 className="text-xl sm:text-2xl font-bold text-white">
            ربط Google Chat لقنوات الطوارئ وغرف العمليات
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-lg mx-auto">
            قم بتسجيل الدخول لتمكين إرسال التنبيهات اللحظية وإشعارات النشر إلى غرف المحادثة (Spaces) الخاصة بفريق DevOps في Google Chat.
          </p>
        </div>

        <div className="pt-2 flex justify-center">
          <button
            onClick={handleSignIn}
            className="flex items-center gap-3 px-6 py-3 bg-white hover:bg-slate-50 text-slate-800 rounded-xl font-bold text-sm shadow-md hover:shadow-lg transition-all"
          >
            <MessageSquare className="w-5 h-5 text-emerald-600" />
            <span>تسجيل الدخول وربط Google Chat</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Info Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-emerald-950/80 border border-emerald-800/80 flex items-center justify-center text-emerald-400">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">
                تنبيهات غرف العمليات (Google Chat Spaces)
              </h3>
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Google Chat مفعل
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              الحساب المرتبط: {user.email}
            </p>
          </div>
        </div>

        <button
          onClick={fetchSpaces}
          disabled={loading}
          className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>تحديث الغرف والمساحات</span>
        </button>
      </div>

      {statusMessage && (
        <div
          className={`p-4 rounded-xl text-xs space-y-2 ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
              : statusMessage.type === 'warning'
              ? 'bg-amber-950/60 text-amber-300 border border-amber-800'
              : 'bg-rose-950/60 text-rose-300 border border-rose-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="leading-relaxed">{statusMessage.text}</span>
            <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white mr-2">
              ✕
            </button>
          </div>
          {consoleHelpUrl && (
            <div className="pt-2 border-t border-amber-900/60 flex items-center gap-2">
              <span className="text-[11px] text-amber-200">صفحة إعداد تطبيق Chat في Google Cloud:</span>
              <a
                href={consoleHelpUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] underline text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-mono"
              >
                <span>فتح صفحة الإعداد</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}
        </div>
      )}

      {/* Main Grid: Spaces & Compose Dispatch */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left / Compose Alert Form */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h4 className="text-base font-bold text-white flex items-center gap-2">
              <Send className="w-4 h-4 text-emerald-400" />
              إرسال تنبيه أو رسالة لغرفة المحادثة
            </h4>
            <span className="text-xs text-slate-400">DevOps Chat Dispatch</span>
          </div>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">
                اختر غرفة المحادثة (Space):
              </label>
              {spaces.length > 0 ? (
                <select
                  value={selectedSpace}
                  onChange={(e) => setSelectedSpace(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
                >
                  {spaces.map((sp) => (
                    <option key={sp.name} value={sp.name}>
                      {sp.displayName || sp.name} ({sp.type || 'SPACE'})
                    </option>
                  ))}
                </select>
              ) : (
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-slate-400 text-xs">
                  لا توجد مساحات محددة حالياً، أو يمكنك إدخال اسم المساحة يدوياً:
                  <input
                    type="text"
                    placeholder="spaces/AAAAAAAAAAA"
                    value={selectedSpace}
                    onChange={(e) => setSelectedSpace(e.target.value)}
                    className="w-full mt-2 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-white font-mono"
                  />
                </div>
              )}
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">نص التنبيه:</label>
              <textarea
                rows={6}
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                placeholder="اكتب التنبيه هنا أو اختر أحد النماذج السريعة بالأسفل..."
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono leading-relaxed"
              />
            </div>

            {/* Quick Templates Buttons */}
            <div>
              <span className="block text-slate-400 font-semibold mb-2">نماذج إشعارات جاهزة:</span>
              <div className="flex flex-wrap items-center gap-2">
                {incidents.length > 0 && (
                  <button
                    type="button"
                    onClick={() => handlePrepareIncidentAlert(incidents[0])}
                    className="px-3 py-1.5 rounded-lg bg-rose-950/70 hover:bg-rose-900 text-rose-300 border border-rose-800 text-[11px] font-semibold transition-colors flex items-center gap-1.5"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>تنبيه أحدث خطأ حرج</span>
                  </button>
                )}

                {deployments.length > 0 && (
                  <button
                    type="button"
                    onClick={() => handlePrepareDeploymentAlert(deployments[0])}
                    className="px-3 py-1.5 rounded-lg bg-indigo-950/70 hover:bg-indigo-900 text-indigo-300 border border-indigo-800 text-[11px] font-semibold transition-colors flex items-center gap-1.5"
                  >
                    <Rocket className="w-3.5 h-3.5" />
                    <span>إشعار آخر نشر CI/CD</span>
                  </button>
                )}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setIsConfirmModalOpen(true)}
                disabled={!selectedSpace || !messageText.trim()}
                className="px-6 py-2.5 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white shadow-md flex items-center gap-2 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>إرسال لغرفة Chat</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right / Information & Prerequisites */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <Info className="w-4 h-4 text-indigo-400" />
              إرشادات استخدام Google Chat API
            </h4>

            <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
                <p className="font-bold text-emerald-400">1. حسابات Google Workspace المؤسسية:</p>
                <p className="text-slate-400 text-[11px]">
                  تتطلب واجهة Google Chat API أن يكون الحساب ضمن مؤسسة Google Workspace (حساب عمل) وليست حسابات @gmail.com الشخصية.
                </p>
              </div>

              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
                <p className="font-bold text-indigo-400">2. إعداد تطبيق Chat في Cloud Console:</p>
                <p className="text-slate-400 text-[11px]">
                  في مشروع Google Cloud (<code>warm-aegis-350823</code>)، قم بتعيين اسم ووصف لتطبيق Chat في صفحة Configuration لتلقي الرسائل وتوزيعها داخل المساحات.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Explicit User Confirmation Dialog (MANDATORY for sending chat messages) */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-slate-100 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
                <MessageSquare className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">تأكيد إرسال رسالة إلى Google Chat</h4>
                <p className="text-xs text-slate-400">إجراء نشر رسالة في غرفة العمليات</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              هل أنت متأكد من رغبتك في إرسال الرسالة التالية إلى المساحة:
              <span className="block font-bold text-emerald-300 mt-1 font-mono">{selectedSpace}</span>
              <span className="block text-slate-400 mt-2 font-mono text-[11px] bg-slate-900 p-2 rounded">
                {messageText.slice(0, 140)}...
              </span>
            </p>

            <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsConfirmModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                إلغاء التراجع
              </button>
              <button
                type="button"
                onClick={handleSendMessageConfirmed}
                disabled={isSending}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white shadow-md flex items-center gap-1.5 disabled:opacity-50"
              >
                {isSending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                <span>تأكيد الإرسال الآن</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
