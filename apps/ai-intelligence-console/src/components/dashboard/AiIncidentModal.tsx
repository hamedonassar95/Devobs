import React, { useState, useEffect, useRef } from 'react';
import { Incident, Server } from '../../types/serverDashboard';
import { Sparkles, Check, Copy, Download, AlertOctagon, Terminal, Loader2, CheckCircle2, FolderGit2 } from 'lucide-react';
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
  const [accessToken, setAccessToken] = useState('');
  const [errorLog, setErrorLog] = useState('');
  const [dataRedacted, setDataRedacted] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    pending.current?.abort();
    setAccessToken('');
    setDataRedacted(false);
    setAnalysis('');
    setError(null);
    setLoading(false);
    setErrorLog(incident ? [incident.code, incident.severity, incident.message, incident.stackTrace].join('\n') : '');
    return () => { pending.current?.abort(); };
  }, [incident]);

  const requestAnalysis = async () => {
    if (!incident || !accessToken.trim() || !dataRedacted || loading) return;
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setError(null);
    setAnalysis('');
    const authorization = `Bearer ${accessToken.trim()}`;
    setAccessToken('');
    try {
      const response = await fetch('/api/ai/analyze-incident', {
        method: 'POST', signal: controller.signal, cache: 'no-store',
        headers: { 'Content-Type': 'application/json', Authorization: authorization },
        body: JSON.stringify({ serverId: incident.serverId, errorLog, dataRedacted: true }),
      });
      if (!response.ok) throw new Error('request_failed');
      const data = await response.json();
      if (!controller.signal.aborted) setAnalysis(data.analysis);
    } catch {
      if (!controller.signal.aborted) setError('التشخيص غير متاح. تحقق من إعداد الخدمة وصلاحية رمز الوصول ونطاقه.');
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  if (!incident) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(analysis);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadReport = () => {
    const filename = `تقرير_تحليل_حادثة_${incident.code}_${new Date().toISOString().slice(0, 10)}.md`;
    downloadTextFile(filename, `# تقرير تحليل الحادثة بالذكاء الاصطناعي (Devobs — تحليل استشاري)\n\nكود الخطأ: ${incident.code}\nالخادم: ${incident.serverName}\nالتاريخ: ${incident.timestamp}\n\n${analysis}`);
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
                تحليل الحادثة الاستشاري (Devobs)
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

          <div className="space-y-3 text-xs">
            <p className="text-slate-400">راجع السجل واحذف الأسرار والبيانات الشخصية قبل الإرسال. فتح النافذة لا يرسل طلبًا.</p>
            <label className="block space-y-1">
              <span>السجل المعد للإرسال</span>
              <textarea value={errorLog} onChange={event => { setErrorLog(event.target.value); setDataRedacted(false); }} disabled={loading}
                className="w-full rounded-lg bg-slate-950 border border-slate-700 p-3 font-mono" rows={5} dir="auto" />
            </label>
            <label className="block space-y-1">
              <span>رمز وصول قصير العمر بصلاحية التشخيص</span>
              <input type="password" value={accessToken} onChange={event => setAccessToken(event.target.value)}
                autoComplete="off" spellCheck={false} disabled={loading}
                className="w-full rounded-lg bg-slate-950 border border-slate-700 p-2" />
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={dataRedacted} onChange={event => setDataRedacted(event.target.checked)} disabled={loading} />
              <span>راجعت السجل وحذفت الأسرار والبيانات الشخصية.</span>
            </label>
            <button type="button" onClick={requestAnalysis}
              disabled={loading || !accessToken.trim() || !errorLog.trim() || !dataRedacted}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white disabled:opacity-50">طلب تحليل استشاري</button>
          </div>

          {/* Loading state */}
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs font-semibold text-slate-300">
                جارٍ إرسال السجل الذي راجعته إلى خدمة Devobs...
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
              disabled={loading || !!error || !analysis}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'تم النسخ!' : 'نسخ التقرير'}</span>
            </button>

            <button
              onClick={handleDownloadReport}
              disabled={loading || !!error || !analysis}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>تنزيل Markdown</span>
            </button>

            <button
              onClick={() => {
                const issueMd = `### [${incident.code}] ${incident.message}\n**Server:** ${incident.serverName}\n**Severity:** ${incident.severity}\n**Time:** ${incident.timestamp}\n\n#### Root Cause Analysis:\n${analysis}`;
                navigator.clipboard.writeText(issueMd);
                alert('تم نسخ نموذج GitHub Issue إلى الحافظة بنجاح!');
              }}
              disabled={loading || !!error || !analysis}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>نسخ كـ GitHub Issue</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {!incident.resolved && (
              <>
                <button
                  onClick={handleApplyFixAndResolve}
                  className="px-3.5 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>تسجيل الحادثة محلولة</span>
                </button>
              </>
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
