import React, { useState, useEffect } from 'react';
import { Incident, Server } from '../../types/serverDashboard';
import { Sparkles, Check, Copy, Download, AlertOctagon, Terminal, Loader2, CheckCircle2, Rocket, FolderGit2 } from 'lucide-react';
import { downloadTextFile } from '../../utils/dashboardUtils';

interface AiIncidentModalProps {
  incident: Incident | null;
  server: Server | undefined;
  onClose: () => void;
  onResolveIncident: (incidentId: string) => void;
  onDeployHotfix?: (serviceName: string, changeLog: string) => void;
}

export const AiIncidentModal: React.FC<AiIncidentModalProps> = ({
  incident,
  server,
  onClose,
  onResolveIncident,
  onDeployHotfix,
}) => {
  const [analysis, setAnalysis] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!incident) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    async function fetchAiAnalysis() {
      try {
        const res = await fetch('/api/ai/analyze-incident', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident,
            server,
          }),
        });

        if (!res.ok) {
          throw new Error(`خطأ في استجابة الخادم: ${res.status}`);
        }

        const data = await res.json();
        if (isMounted) {
          setAnalysis(data.analysis || 'لم يتم استلام تحليل من النموذج.');
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          console.error('Failed to fetch AI analysis:', err);
          setError(err.message || 'حدث خطأ أثناء الاتصال بنموذج Gemini');
          setLoading(false);
        }
      }
    }

    fetchAiAnalysis();

    return () => {
      isMounted = false;
    };
  }, [incident, server]);

  if (!incident) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(analysis);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadReport = () => {
    const filename = `تقرير_تحليل_حادثة_${incident.code}_${new Date().toISOString().slice(0, 10)}.md`;
    downloadTextFile(filename, `# تقرير تحليل الحادثة بالذكاء الاصطناعي (Gemini 3.8 Flash)\n\nكود الخطأ: ${incident.code}\nالخادم: ${incident.serverName}\nالتاريخ: ${incident.timestamp}\n\n${analysis}`);
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
                تحليل السبب الجذري (AI Root Cause Analysis)
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

          {/* Loading state */}
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs font-semibold text-slate-300">
                يقوم مهندس الذكاء الاصطناعي (Gemini 3.8 Flash) بفحص السجل والذاكرة والمؤشرات...
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

            <button
              onClick={() => {
                const issueMd = `### [${incident.code}] ${incident.message}\n**Server:** ${incident.serverName}\n**Severity:** ${incident.severity}\n**Time:** ${incident.timestamp}\n\n#### Root Cause Analysis:\n${analysis}`;
                navigator.clipboard.writeText(issueMd);
                alert('تم نسخ نموذج GitHub Issue إلى الحافظة بنجاح!');
              }}
              disabled={loading || !!error}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>نسخ كـ GitHub Issue</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {!incident.resolved && (
              <>
                {onDeployHotfix && (
                  <button
                    onClick={() => {
                      onDeployHotfix(
                        incident.serverName,
                        `[Hotfix SRE] Fix ${incident.code}: Root cause mitigated via Gemini recommendations.`
                      );
                      handleApplyFixAndResolve();
                    }}
                    className="px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-md shadow-indigo-600/30"
                  >
                    <Rocket className="w-4 h-4 text-cyan-300" />
                    <span>نشر تصحيح فوري (Deploy Hotfix CI/CD)</span>
                  </button>
                )}

                <button
                  onClick={handleApplyFixAndResolve}
                  className="px-3.5 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>اعتماد الحل وإغلاق</span>
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
