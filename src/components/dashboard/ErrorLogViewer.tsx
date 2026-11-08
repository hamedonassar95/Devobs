import React, { useState } from 'react';
import { Incident, IncidentSeverity, Server } from '../../types/serverDashboard';
import {
  AlertOctagon,
  AlertTriangle,
  Info,
  CheckCircle,
  Search,
  Sparkles,
  ChevronDown,
  Download,
  PlusCircle,
  Terminal,
  Flame,
  Zap,
  ShieldAlert,
  Database,
  Cpu,
} from 'lucide-react';
import { exportIncidentsToCSV } from '../../utils/dashboardUtils';

export interface ChaosScenario {
  code: string;
  severity: IncidentSeverity;
  message: string;
  stack: string;
}

interface ErrorLogViewerProps {
  incidents: Incident[];
  servers: Server[];
  onResolveIncident: (incidentId: string) => void;
  onAnalyzeWithAI: (incident: Incident) => void;
  onSimulateIncident: (scenario?: ChaosScenario) => void;
}

export const ErrorLogViewer: React.FC<ErrorLogViewerProps> = ({
  incidents,
  servers,
  onResolveIncident,
  onAnalyzeWithAI,
  onSimulateIncident,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [resolutionFilter, setResolutionFilter] = useState<'all' | 'unresolved' | 'resolved'>('all');
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null);
  const [showChaosMenu, setShowChaosMenu] = useState(false);

  const toggleTrace = (id: string) => {
    setExpandedTraceId((prev) => (prev === id ? null : id));
  };

  const filteredIncidents = incidents.filter((inc) => {
    const matchesSearch =
      inc.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.serverName.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSeverity = severityFilter === 'all' || inc.severity === severityFilter;
    const matchesResolution =
      resolutionFilter === 'all'
        ? true
        : resolutionFilter === 'resolved'
        ? inc.resolved
        : !inc.resolved;

    return matchesSearch && matchesSeverity && matchesResolution;
  });

  const getSeverityBadge = (severity: IncidentSeverity) => {
    switch (severity) {
      case 'critical':
        return (
          <span className="text-xs font-bold text-rose-400 bg-rose-950/80 border border-rose-800 px-2 py-0.5 rounded flex items-center gap-1">
            <AlertOctagon className="w-3.5 h-3.5" />
            حرج (Critical)
          </span>
        );
      case 'warning':
        return (
          <span className="text-xs font-bold text-amber-400 bg-amber-950/80 border border-amber-800 px-2 py-0.5 rounded flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            تحذير (Warning)
          </span>
        );
      case 'info':
        return (
          <span className="text-xs font-bold text-sky-400 bg-sky-950/80 border border-sky-800 px-2 py-0.5 rounded flex items-center gap-1">
            <Info className="w-3.5 h-3.5" />
            معلومة (Info)
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Control bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="البحث في كود الخطأ، الرسالة، أو اسم الخادم..."
              className="w-full pr-10 pl-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => exportIncidentsToCSV(filteredIncidents)}
              className="px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>تصدير CSV</span>
            </button>

            <div className="relative">
              <button
                onClick={() => setShowChaosMenu(!showChaosMenu)}
                className="px-4 py-2.5 text-xs font-bold rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white transition-all flex items-center gap-1.5 shadow-md shadow-rose-950/40"
              >
                <Flame className="w-4 h-4 text-amber-200 animate-pulse" />
                <span>اختبار الفوضى (Chaos Engineering)</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showChaosMenu ? 'rotate-180' : ''}`} />
              </button>

              {showChaosMenu && (
                <div className="absolute left-0 mt-2 w-72 bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl p-2 z-30 space-y-1 text-xs">
                  <div className="px-3 py-2 text-[11px] font-bold text-slate-400 border-b border-slate-800">
                    اختر سيناريو الكارثة التشغيلية لحقنه:
                  </div>

                  <button
                    onClick={() => {
                      onSimulateIncident({
                        code: 'ERR_HTTP_502_BAD_GATEWAY',
                        severity: 'critical',
                        message: 'توقف مفاجئ في استجابة خدمة البروكسي الداخلي Nginx (Worker segfault).',
                        stack: 'connect() failed (111: Connection refused) while connecting to upstream.\nworker process 3108 exited on signal 11.',
                      });
                      setShowChaosMenu(false);
                    }}
                    className="w-full text-right p-2.5 rounded-xl hover:bg-slate-800 text-slate-200 transition-colors flex items-center gap-2"
                  >
                    <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />
                    <div>
                      <div className="font-bold text-white text-[11px]">سقوط الـ Gateway (HTTP 502)</div>
                      <div className="text-[10px] text-slate-400">انقطاع الاتصال بالخوادم الخلفية</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      onSimulateIncident({
                        code: 'ERR_HIGH_CPU_SPIKE',
                        severity: 'critical',
                        message: 'قفزة مفاجئة في استهلاك المعالج تجاوزت 96% بسبب معالجة دفعات متزامنة.',
                        stack: 'PID 14088 node [worker-thread] consuming 96.8% CPU.\nGarbage collector thrashing detected.',
                      });
                      setShowChaosMenu(false);
                    }}
                    className="w-full text-right p-2.5 rounded-xl hover:bg-slate-800 text-slate-200 transition-colors flex items-center gap-2"
                  >
                    <Cpu className="w-4 h-4 text-amber-400 shrink-0" />
                    <div>
                      <div className="font-bold text-white text-[11px]">اختناق المعالج الحرج (CPU &gt; 96%)</div>
                      <div className="text-[10px] text-slate-400">تراكم المهام وتجميد الـ Event Loop</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      onSimulateIncident({
                        code: 'ERR_DB_DEADLOCK_TIMEOUT',
                        severity: 'critical',
                        message: 'استنفاد مجمع اتصالات قاعدة البيانات (Connection Pool Exhaustion) وحدوث Deadlock.',
                        stack: 'KnexTimeoutError: Knex: Timeout acquiring a connection. The pool is probably full.\nTransaction locked on row #94082.',
                      });
                      setShowChaosMenu(false);
                    }}
                    className="w-full text-right p-2.5 rounded-xl hover:bg-slate-800 text-slate-200 transition-colors flex items-center gap-2"
                  >
                    <Database className="w-4 h-4 text-purple-400 shrink-0" />
                    <div>
                      <div className="font-bold text-white text-[11px]">اختناق قاعدة البيانات (Deadlock)</div>
                      <div className="text-[10px] text-slate-400">استنفاد اتصالات PostgreSQL / MySQL</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      onSimulateIncident({
                        code: 'SEC_DDOS_PACKET_STORM',
                        severity: 'critical',
                        message: 'رصد هجوم حزم مكثف (SYN Flood Attack) تجاوز 120,000 طلب بالثانية على المنفذ 443.',
                        stack: 'Firewall rate-limiter threshold exceeded.\nIngress packet drop rate at 42.8%.',
                      });
                      setShowChaosMenu(false);
                    }}
                    className="w-full text-right p-2.5 rounded-xl hover:bg-slate-800 text-slate-200 transition-colors flex items-center gap-2"
                  >
                    <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
                    <div>
                      <div className="font-bold text-white text-[11px]">هجوم سيبراني (DDoS SYN Flood)</div>
                      <div className="text-[10px] text-slate-400">تدفق هائل للحزم الخبيثة</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      onSimulateIncident();
                      setShowChaosMenu(false);
                    }}
                    className="w-full text-right p-2 rounded-xl hover:bg-slate-800 text-indigo-400 transition-colors font-semibold text-[11px] text-center border-t border-slate-800 mt-1 pt-2"
                  >
                    🎲 محاكاة عطل عشوائي تلقائي
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Filter Badges */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-800/80">
          {/* Severity */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-400 ml-2 font-medium">مستوى الخطورة:</span>
            {[
              { id: 'all', label: 'الكل' },
              { id: 'critical', label: 'حرج' },
              { id: 'warning', label: 'تحذير' },
              { id: 'info', label: 'معلومات' },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setSeverityFilter(st.id)}
                className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                  severityFilter === st.id
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'text-slate-400 hover:text-white bg-slate-950 border border-slate-800'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          {/* Resolution */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-400 ml-2 font-medium">حالة المعالجة:</span>
            {[
              { id: 'all', label: 'كافة الحوادث' },
              { id: 'unresolved', label: 'قيد المتابعة (مفتوح)' },
              { id: 'resolved', label: 'تم الحل' },
            ].map((res) => (
              <button
                key={res.id}
                onClick={() => setResolutionFilter(res.id as any)}
                className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                  resolutionFilter === res.id
                    ? 'bg-slate-700 text-white font-bold'
                    : 'text-slate-400 hover:text-white bg-slate-950 border border-slate-800'
                }`}
              >
                {res.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Incidents List */}
      <div className="space-y-3">
        {filteredIncidents.map((incident) => {
          const isExpanded = expandedTraceId === incident.id;
          return (
            <div
              key={incident.id}
              className={`bg-slate-900 border rounded-2xl p-5 transition-all shadow-sm ${
                incident.resolved
                  ? 'border-slate-800/80 opacity-75'
                  : incident.severity === 'critical'
                  ? 'border-rose-900/60 bg-rose-950/10'
                  : incident.severity === 'warning'
                  ? 'border-amber-900/60 bg-amber-950/10'
                  : 'border-slate-800'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {getSeverityBadge(incident.severity)}
                    <span className="font-mono text-xs font-bold text-white bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      {incident.code}
                    </span>
                    <span className="text-xs text-indigo-400 font-mono">
                      @{incident.serverName}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-100 pt-1 leading-relaxed">
                    {incident.message}
                  </h4>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
                  {/* AI Analysis button */}
                  <button
                    onClick={() => onAnalyzeWithAI(incident)}
                    className="px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>تحليل بـ Gemini</span>
                  </button>

                  {/* Mark as resolved */}
                  {!incident.resolved ? (
                    <button
                      onClick={() => onResolveIncident(incident.id)}
                      className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 transition-colors flex items-center gap-1"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>حل المشكلة</span>
                    </button>
                  ) : (
                    <span className="text-xs text-emerald-400 font-medium px-2 py-1 bg-emerald-950/40 rounded border border-emerald-900">
                      تم الحل ({incident.resolvedAt?.slice(11, 16) || 'مؤرشف'})
                    </span>
                  )}
                </div>
              </div>

              {/* Timestamp & Stack Trace toggle */}
              <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 font-mono">
                <span>توقيت الحادثة: {incident.timestamp}</span>

                {incident.stackTrace && (
                  <button
                    onClick={() => toggleTrace(incident.id)}
                    className="text-xs text-slate-300 hover:text-white flex items-center gap-1 transition-colors"
                  >
                    <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{isExpanded ? 'إخفاء تتبع الخطأ (Stack Trace)' : 'عرض تتبع الخطأ (Stack Trace)'}</span>
                    <ChevronDown
                      className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    />
                  </button>
                )}
              </div>

              {/* Stack Trace details */}
              {isExpanded && incident.stackTrace && (
                <div className="mt-3 p-3 bg-slate-950 rounded-xl border border-slate-800 font-mono text-[11px] text-rose-300 leading-relaxed overflow-x-auto whitespace-pre-wrap">
                  {incident.stackTrace}
                </div>
              )}
            </div>
          );
        })}

        {filteredIncidents.length === 0 && (
          <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl text-slate-400">
            <CheckCircle className="w-10 h-10 mx-auto text-emerald-500 mb-3" />
            <p className="text-base font-bold text-white mb-1">لا توجد حوادث مسجلة مطابقة</p>
            <p className="text-xs text-slate-500">البنية التحتية مستقرة تماماً ولا تظهر أي أخطاء حرجة.</p>
          </div>
        )}
      </div>
    </div>
  );
};
