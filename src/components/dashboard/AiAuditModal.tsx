import React, { useState, useEffect } from 'react';
import { Server, Incident, Deployment } from '../../types/serverDashboard';
import { Sparkles, Check, Copy, Download, Loader2, ShieldCheck, Cloud, CheckCircle2 } from 'lucide-react';
import { downloadTextFile } from '../../utils/dashboardUtils';
import { uploadDriveFile } from '../../services/googleDriveService';

interface AiAuditModalProps {
  servers: Server[];
  incidents: Incident[];
  deployments: Deployment[];
  onClose: () => void;
  token?: string | null;
}

export const AiAuditModal: React.FC<AiAuditModalProps> = ({
  servers,
  incidents,
  deployments,
  onClose,
  token,
}) => {
  const [report, setReport] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [savingToDrive, setSavingToDrive] = useState<boolean>(false);
  const [savedToDrive, setSavedToDrive] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    async function fetchAuditReport() {
      try {
        const res = await fetch('/api/ai/generate-audit-report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            servers,
            incidents,
            deployments,
          }),
        });

        if (!res.ok) {
          throw new Error(`خطأ في استجابة الخادم: ${res.status}`);
        }

        const data = await res.json();
        if (isMounted) {
          setReport(data.report || 'لم يتم استلام تقرير.');
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          console.error('Audit report error:', err);
          setError(err.message || 'حدث خطأ أثناء إعداد تقرير التدقيق بالذكاء الاصطناعي');
          setLoading(false);
        }
      }
    }

    fetchAuditReport();

    return () => {
      isMounted = false;
    };
  }, [servers, incidents, deployments]);

  const handleCopy = () => {
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const filename = `تقرير_تدقيق_البنية_التحتية_${new Date().toISOString().slice(0, 10)}.md`;
    downloadTextFile(filename, report);
  };

  const handleSaveToDrive = async () => {
    if (!token || !report) return;
    const confirmed = window.confirm('هل تود حفظ هذا التقرير الشامل في حسابك على Google Drive؟');
    if (!confirmed) return;

    setSavingToDrive(true);
    try {
      const filename = `تقرير_تدقيق_البنية_التحتية_${new Date().toISOString().slice(0, 10)}.md`;
      await uploadDriveFile(token, filename, report, 'text/markdown');
      setSavedToDrive(true);
      setTimeout(() => setSavedToDrive(false), 3000);
    } catch (err: any) {
      alert(`فشل الحفظ في Google Drive: ${err.message}`);
    } finally {
      setSavingToDrive(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between gap-4 bg-slate-950/70">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/40">
              <ShieldCheck className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                تقرير تدقيق البنية التحتية الشامل (SRE Health Audit)
              </h3>
              <p className="text-xs text-slate-400">
                مدعوم بنموذج Gemini 3.8 Flash لتحليل المخاطر واقتراح التوصيات
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

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {loading && (
            <div className="py-16 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs sm:text-sm font-semibold text-slate-300">
                جاري إعداد تقرير التدقيق وتحليل مؤشرات {servers.length} خوادم و{incidents.length} حوادث...
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="bg-rose-950/40 border border-rose-900 rounded-xl p-4 text-xs text-rose-300">
              <p className="font-bold mb-1">تعذر إعداد التقرير:</p>
              <p>{error}</p>
            </div>
          )}

          {!loading && !error && report && (
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 text-xs sm:text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-wrap">
              {report}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/70 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={loading || !!error}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'تم النسخ!' : 'نسخ التقرير'}</span>
            </button>

            <button
              onClick={handleDownload}
              disabled={loading || !!error}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>تنزيل Markdown</span>
            </button>

            {token && (
              <button
                onClick={handleSaveToDrive}
                disabled={loading || !!error || savingToDrive}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-800 transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {savingToDrive ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : savedToDrive ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Cloud className="w-3.5 h-3.5" />
                )}
                <span>{savedToDrive ? 'تم الحفظ في Drive!' : 'حفظ في Google Drive'}</span>
              </button>
            )}
          </div>

          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
          >
            إغلاق
          </button>
        </div>
      </div>
    </div>
  );
};
