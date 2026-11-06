import React, { useState, useEffect } from 'react';
import { Incident, Server } from '../../types/serverDashboard';
import { Sparkles, Check, Copy, Download, Loader2, CheckCircle2 } from 'lucide-react';
import { downloadTextFile } from '../../utils/dashboardUtils';

interface AiIncidentModalProps {
  incident: Incident | null;
  server: Server | undefined;
  onClose: () => void;
  onResolveIncident: (incidentId: string) => void;
}

export const AiIncidentModal: React.FC<AiIncidentModalProps> = ({
  incident,
  server,
  onClose,
  onResolveIncident,
}) => {
  const [analysis, setAnalysis] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [accessToken, setAccessToken] = useState<string>('');
  const [dataRedacted, setDataRedacted] = useState<boolean>(false);
  const secureContext = typeof window !== 'undefined' && window.isSecureContext;

  useEffect(() => {
    setAnalysis('');
    setLoading(false);
    setError(null);
    setAccessToken('');
    setDataRedacted(false);
  }, [incident?.id]);

  if (!incident) return null;

  const handleAnalyzeIncident = async () => {
    if (!dataRedacted) {
      setError('راجع السجل واحذف الأسرار والبيانات الشخصية، ثم أكّد ذلك قبل الإرسال.');
      return;
    }
    if (!accessToken.trim()) {
      setError('أدخل رمز OIDC قصير الصلاحية ومصرّحًا له بالتشخيص.');
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysis('');
    try {
      const res = await fetch('/api/ai/analyze-incident', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken.trim()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          serverId: incident.serverId,
          dataRedacted: true,
          incident: {
            code: incident.code,
            message: incident.message,
            severity: incident.severity,
            stackTrace: incident.stackTrace,
          },
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const messages: Record<string, string> = {
          missing_or_invalid_access_token: 'رمز الدخول غير صالح أو انتهت صلاحيته.',
          invalid_access_token: 'رمز الدخول غير صالح أو انتهت صلاحيته.',
          service_access_denied: 'هذا الحساب غير مخوّل لتشخيص هذه الخدمة.',
          rate_limited: 'تم بلوغ حد الطلبات المؤقت. انتظر قليلًا ثم أعد المحاولة.',
          devobs_integration_not_configured: 'تكامل Devobs لم يُفعّل أو لم تُربط هذه الخدمة بعد.',
          devobs_integration_not_enabled: 'تكامل Devobs غير مفعّل على الخادم.',
          devobs_api_unavailable: 'واجهة Devobs غير متاحة حاليًا.',
          diagnostics_unavailable: 'محرك التشخيص غير متاح حاليًا.',
        };
        throw new Error(messages[data.error] || 'تعذر إكمال التشخيص. تحقق من الإعدادات والصلاحيات.');
      }
      setAnalysis(data.analysis || 'لم يتم استلام تشخيص من Devobs.');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'تعذر الاتصال بواجهة Devobs.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(analysis);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadReport = () => {
    const filename = `تقرير_تحليل_حادثة_${incident.code}_${new Date().toISOString().slice(0, 10)}.md`;
    downloadTextFile(filename, `# تقرير تشخيص الحادثة من Devobs AI\n\nكود الخطأ: ${incident.code}\nالخادم: ${incident.serverName}\nالتاريخ: ${incident.timestamp}\n\n${analysis}`);
  };

  const handleApplyFixAndResolve = () => {
    onResolveIncident(incident.id);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between gap-4 bg-slate-950/70">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/40">
              <Sparkles className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
              تشخيص الحادثة عبر Devobs AI
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                {incident.code} · @{incident.serverName}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {/* Incident context banner */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs space-y-2">
            <div className="flex items-center justify-between text-slate-400 font-mono">
              <span>توقيت الحدوث: {incident.timestamp}</span>
              <span className="text-rose-400 font-bold uppercase">{incident.severity}</span>
            </div>
            <p className="text-slate-200 font-medium">{incident.message}</p>
          </div>

          <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/70 p-4">
            <label className="block space-y-1.5 text-xs">
              <span className="font-semibold text-slate-200">رمز دخول Devobs المؤقت</span>
              <input
                type="password"
                value={accessToken}
                onChange={(event) => setAccessToken(event.target.value)}
                autoComplete="off"
                spellCheck={false}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-slate-100 outline-none focus:border-indigo-500"
                placeholder="OIDC access token"
                aria-label="رمز دخول Devobs المؤقت"
              />
            </label>
            <label className="flex items-start gap-2 text-xs leading-relaxed text-slate-400">
              <input
                type="checkbox"
                checked={dataRedacted}
                onChange={(event) => setDataRedacted(event.target.checked)}
                className="mt-0.5 accent-indigo-500"
              />
              <span>راجعت الرسالة وتتبع الخطأ وحذفت كلمات المرور والمفاتيح والبيانات الشخصية. سيُرسل النص المنقّح إلى Devobs للتشخيص، ولا يُحفظ رمز الدخول في التخزين المحلي.</span>
            </label>
            <button
              type="button"
              onClick={handleAnalyzeIncident}
              disabled={loading || !accessToken.trim() || !dataRedacted || !secureContext}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'جارٍ طلب التشخيص…' : 'إرسال إلى Devobs للتشخيص'}
            </button>
            <p className="text-[11px] text-slate-500">يلزم رمز OIDC قصير الصلاحية يحمل صلاحية devobs.ai.diagnose. أدخله عبر اتصال HTTPS فقط؛ لا ترسله في المحادثة.{!secureContext && ' افتح التطبيق عبر HTTPS أولًا.'}</p>
          </div>

          {/* Loading state */}
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs font-semibold text-slate-300">
                يرسل Devobs السجل المنقّح لمحرك التشخيص...
              </p>
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div className="bg-rose-950/40 border border-rose-900 rounded-xl p-4 text-xs text-rose-300">
              <p className="font-bold mb-1">تعذر استكمال التحليل:</p>
              <p>{error}</p>
            </div>
          )}

          {/* Success state - Analysis Content */}
          {!loading && !error && analysis && (
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 text-xs sm:text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-wrap">
              {analysis}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/70 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={loading || !!error}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'تم النسخ!' : 'نسخ التقرير'}</span>
            </button>

            <button
              onClick={handleDownloadReport}
              disabled={loading || !!error}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>تنزيل Markdown</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {!incident.resolved && (
              <button
                onClick={handleApplyFixAndResolve}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>تم التحقق يدويًا وإغلاق الحادثة</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              إغلاق
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
