import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  listGmailMessages,
  sendGmailEmail,
  getGmailProfile,
  GmailMessageSummary,
  GmailProfile,
} from '../../services/gmailService';
import { googleSignIn } from '../../services/googleAuth';
import { Server, Incident } from '../../types/serverDashboard';
import {
  Mail,
  Send,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  Inbox,
  User as UserIcon,
  Clock,
  Sparkles,
  FileText,
  ShieldCheck,
  Loader2,
  AlertOctagon,
} from 'lucide-react';

interface GmailTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  onAuthSuccess: (user: User, token: string) => void;
}

export const GmailTab: React.FC<GmailTabProps> = ({
  user,
  token,
  servers,
  incidents,
  onAuthSuccess,
}) => {
  const [messages, setMessages] = useState<GmailMessageSummary[]>([]);
  const [profile, setProfile] = useState<GmailProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Compose / Alert state
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [recipient, setRecipient] = useState(user?.email || 'devops-team@company.com');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Confirmation Modal state (Mandatory for destructive/email sending operations)
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);

  const fetchInbox = async () => {
    if (!token) return;
    setLoading(true);
    setStatusMessage(null);
    try {
      const [msgs, prof] = await Promise.all([
        listGmailMessages(token, searchQuery, 15),
        getGmailProfile(token),
      ]);
      setMessages(msgs);
      setProfile(prof);
    } catch (err: any) {
      console.error('Error fetching Gmail messages:', err);
      setStatusMessage({ text: err.message || 'فشل جلب رسائل البريد الإلكتروني', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchInbox();
    }
  }, [token]);

  const handleSignIn = async () => {
    try {
      const result = await googleSignIn();
      if (result) {
        onAuthSuccess(result.user, result.accessToken);
        setStatusMessage({ text: 'تم ربط Gmail بنجاح!', type: 'success' });
      }
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'تعذر تسجيل الدخول', type: 'error' });
    }
  };

  const handleOpenIncidentTemplate = (incident: Incident) => {
    const srv = servers.find((s) => s.id === incident.serverId);
    setSubject(`[تنبيه حرج] عطل في الخادم ${incident.serverName} (${incident.code})`);
    setBody(`السادة فريق هندسة النظم والبنية التحتية،

تم رصد حادثة تشغيلية حرجة على منظومة الخوادم:

- اسم الخادم: ${incident.serverName} (${srv?.ip || 'N/A'})
- المنطقة: ${srv?.region || 'N/A'}
- كود الخطأ: ${incident.code}
- مستوى الخطورة: ${incident.severity.toUpperCase()}
- توقيت الحدوث: ${incident.timestamp}
- تفاصيل العطل: ${incident.message}

تتبع الخطأ البرمجي (Stack Trace):
${incident.stackTrace || 'غير متوفر'}

يرجى مراجعة لوحة تحكم ServerOps فوراً لاتخاذ إجراءات المعالجة.`);
    setRecipient(user?.email || 'devops-lead@company.com');
    setIsComposeOpen(true);
  };

  const handleSendEmailConfirmed = async () => {
    if (!token || !recipient.trim() || !subject.trim()) return;
    setIsSending(true);
    try {
      await sendGmailEmail(token, {
        to: recipient.trim(),
        subject: subject.trim(),
        body: body.trim(),
      });
      setIsConfirmModalOpen(false);
      setIsComposeOpen(false);
      setStatusMessage({
        text: `تم إرسال البريد الإلكتروني بنجاح إلى "${recipient}" عبر حسابك في Gmail!`,
        type: 'success',
      });
      fetchInbox();
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'فشل إرسال البريد الإلكتروني', type: 'error' });
    } finally {
      setIsSending(false);
    }
  };

  if (!token || !user) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center max-w-2xl mx-auto shadow-xl space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-rose-950/80 border border-rose-800/80 flex items-center justify-center mx-auto text-rose-400">
          <Mail className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h3 className="text-xl sm:text-2xl font-bold text-white">
            ربط Gmail لتنبيهات الخوادم وإشعار الفريق
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-lg mx-auto">
            قم بتسجيل الدخول بحساب Google لتمكين المنظومة من إرسال تقارير الأعطال وتنبيهات الحوادث الحرجة عبر بريدك الإلكتروني Gmail، ومتابعة رسائل الدعم الفني.
          </p>
        </div>

        <div className="pt-2 flex justify-center">
          <button
            onClick={handleSignIn}
            className="flex items-center gap-3 px-6 py-3 bg-white hover:bg-slate-50 text-slate-800 rounded-xl font-bold text-sm shadow-md hover:shadow-lg transition-all"
          >
            <Mail className="w-5 h-5 text-rose-600" />
            <span>تسجيل الدخول وربط Gmail</span>
          </button>
        </div>
      </div>
    );
  }

  const criticalIncidents = incidents.filter((i) => !i.resolved);

  return (
    <div className="space-y-6">
      {/* Top Profile Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-rose-950/80 border border-rose-800/80 flex items-center justify-center text-rose-400">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">
                صندوق البريد المرتبط: {profile?.emailAddress || user.email}
              </h3>
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Gmail متصل
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              إجمالي الرسائل في الحساب: {profile?.messagesTotal?.toLocaleString() || '-'}
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            setSubject('تنبيه دوري لحالة الخوادم');
            setRecipient(user.email || '');
            setBody(`ملخص حالة الخوادم الحالية:
- عدد الخوادم: ${servers.length}
- خوادم بحالة جيدة: ${servers.filter((s) => s.status === 'healthy').length}
- حوادث مفتوحة: ${incidents.filter((i) => !i.resolved).length}`);
            setIsComposeOpen(true);
          }}
          className="px-4 py-2.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Send className="w-3.5 h-3.5" />
          <span>إنشاء رسالة تنبيه جديدة</span>
        </button>
      </div>

      {statusMessage && (
        <div
          className={`p-3.5 rounded-xl text-xs flex items-center justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
              : 'bg-rose-950/60 text-rose-300 border border-rose-800'
          }`}
        >
          <span>{statusMessage.text}</span>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Quick Incident Email Alerts Dispatch Strip */}
      {criticalIncidents.length > 0 && (
        <div className="bg-slate-900 border border-amber-900/60 bg-amber-950/10 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-bold">
              <AlertTriangle className="w-4 h-4" />
              <span>إرسال تنبيه بريدي فوري عن حوادث مفتوحة ({criticalIncidents.length} حادثة)</span>
            </div>
            <span className="text-[11px] text-slate-400">انقر لإعداد رسالة فورية للفريق</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {criticalIncidents.slice(0, 2).map((inc) => (
              <div
                key={inc.id}
                className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-0.5 truncate">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-rose-400">{inc.code}</span>
                    <span className="text-slate-400 font-mono">@{inc.serverName}</span>
                  </div>
                  <p className="text-slate-300 truncate text-[11px]">{inc.message}</p>
                </div>

                <button
                  onClick={() => handleOpenIncidentTemplate(inc)}
                  className="px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 text-[11px] font-bold transition-colors whitespace-nowrap shrink-0 flex items-center gap-1"
                >
                  <Send className="w-3 h-3" />
                  <span>تنبيه بـ Gmail</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inbox & Search */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Inbox className="w-4 h-4 text-indigo-400" />
            <h4 className="text-sm font-bold text-white">
              صندوق الوارد والرسائل الأخيرة في Gmail ({messages.length})
            </h4>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') fetchInbox();
                }}
                placeholder="بحث في البريد..."
                className="pr-8 pl-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 w-44 sm:w-56"
              />
            </div>

            <button
              onClick={fetchInbox}
              disabled={loading}
              title="تحديث صندوق الوارد"
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center gap-3 text-slate-400">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            <p className="text-xs">جاري جلب الرسائل من Gmail...</p>
          </div>
        ) : messages.length > 0 ? (
          <div className="divide-y divide-slate-800/80">
            {messages.map((msg) => (
              <div key={msg.id} className="p-4 hover:bg-slate-800/40 transition-colors text-xs space-y-1">
                <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                  <span className="font-bold text-slate-300 truncate max-w-xs">{msg.from}</span>
                  <span>{msg.date ? msg.date.slice(0, 16) : ''}</span>
                </div>
                <h5 className="font-bold text-white text-sm leading-tight">{msg.subject}</h5>
                <p className="text-slate-400 line-clamp-2 leading-relaxed">{msg.snippet}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 text-slate-400 space-y-2">
            <Inbox className="w-10 h-10 mx-auto text-slate-600" />
            <p className="text-sm font-bold text-white">لا توجد رسائل مطابقة</p>
            <p className="text-xs text-slate-500">جرب تعديل كلمة البحث أو تحديث الصندوق.</p>
          </div>
        )}
      </div>

      {/* Compose Email Modal */}
      {isComposeOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 text-slate-100 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Mail className="w-4 h-4 text-rose-500" />
                إنشاء وإرسال بريد إلكتروني عبر Gmail
              </h4>
              <button
                onClick={() => setIsComposeOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">إلى (المرسل إليه):</label>
                <input
                  type="email"
                  required
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="engineer@company.com"
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">الموضوع (Subject):</label>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="تنبيه حادثة أو تقرير خادم..."
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">نص الرسالة:</label>
                <textarea
                  rows={6}
                  required
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="اكتب تفاصيل التنبيه أو التقرير هنا..."
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 leading-relaxed font-sans"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsComposeOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                إلغاء
              </button>
              <button
                type="button"
                onClick={() => setIsConfirmModalOpen(true)}
                disabled={!recipient.trim() || !subject.trim()}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-rose-600 hover:bg-rose-500 text-white shadow-md flex items-center gap-1.5 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>إرسال البريد</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Explicit User Confirmation Dialog (MANDATORY for sending emails) */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-slate-100 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-rose-600/20 text-rose-400 border border-rose-500/30">
                <Mail className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">تأكيد إرسال البريد الإلكتروني</h4>
                <p className="text-xs text-slate-400">إجراء إرسال عبر حسابك في Gmail</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              هل أنت متأكد من رغبتك في إرسال البريد التالي نيابة عنك إلى:
              <span className="block font-bold text-rose-300 mt-1 font-mono">{recipient}</span>
              <span className="block text-slate-400 mt-1 font-semibold">بالموضوع: "{subject}"</span>
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
                onClick={handleSendEmailConfirmed}
                disabled={isSending}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-rose-600 hover:bg-rose-500 text-white shadow-md flex items-center gap-1.5 disabled:opacity-50"
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
