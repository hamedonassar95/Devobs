import React, { useState, useEffect } from 'react';
import { Server, Incident, Deployment } from './types/serverDashboard';
import {
  INITIAL_SERVERS,
  INITIAL_INCIDENTS,
  INITIAL_DEPLOYMENTS,
  INITIAL_METRICS_24H,
} from './data/mockServerData';
import { DashboardHeader } from './components/dashboard/DashboardHeader';
import { ServerOverviewCards } from './components/dashboard/ServerOverviewCards';
import { InteractiveMetricsChart } from './components/dashboard/InteractiveMetricsChart';
import { ServerGrid } from './components/dashboard/ServerGrid';
import { ErrorLogViewer } from './components/dashboard/ErrorLogViewer';
import { DeploymentTracker } from './components/dashboard/DeploymentTracker';
import { AiIncidentModal } from './components/dashboard/AiIncidentModal';
import { AiAuditModal } from './components/dashboard/AiAuditModal';
import { exportServersToCSV, exportIncidentsToCSV, exportDeploymentsToCSV } from './utils/dashboardUtils';
import {
  Server as ServerIcon,
  ShieldAlert,
  Rocket,
  Activity,
  Download,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

export default function App() {
  // Theme state (Dark mode default for High-End Dark Tech)
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme');
      return stored ? stored === 'dark' : true; // Default to dark mode for high-end tech feel
    }
    return true;
  });

  // Tab navigation
  const [activeTab, setActiveTab] = useState<'overview' | 'servers' | 'incidents' | 'deployments'>('overview');

  // LocalStorage state persistence
  const [servers, setServers] = useState<Server[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('serverops_servers');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error('Failed to parse saved servers:', e);
        }
      }
    }
    return INITIAL_SERVERS;
  });

  const [incidents, setIncidents] = useState<Incident[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('serverops_incidents');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error('Failed to parse saved incidents:', e);
        }
      }
    }
    return INITIAL_INCIDENTS;
  });

  const [deployments, setDeployments] = useState<Deployment[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('serverops_deployments');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          console.error('Failed to parse saved deployments:', e);
        }
      }
    }
    return INITIAL_DEPLOYMENTS;
  });

  // Modals state
  const [selectedIncidentForAi, setSelectedIncidentForAi] = useState<Incident | null>(null);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);

  // Sync theme
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  // Sync state to LocalStorage
  useEffect(() => {
    localStorage.setItem('serverops_servers', JSON.stringify(servers));
  }, [servers]);

  useEffect(() => {
    localStorage.setItem('serverops_incidents', JSON.stringify(incidents));
  }, [incidents]);

  useEffect(() => {
    localStorage.setItem('serverops_deployments', JSON.stringify(deployments));
  }, [deployments]);

  // Server Actions
  const handleRestartServer = (serverId: string) => {
    setServers((prev) =>
      prev.map((s) => {
        if (s.id === serverId) {
          return {
            ...s,
            status: 'healthy',
            cpu: Math.floor(Math.random() * 25) + 20,
            memory: Math.floor(Math.random() * 30) + 40,
            lastPing: 'الآن',
          };
        }
        return s;
      })
    );

    const targetServer = servers.find((s) => s.id === serverId);
    if (targetServer) {
      const newInc: Incident = {
        id: `inc-${Date.now()}`,
        serverId: targetServer.id,
        serverName: targetServer.name,
        severity: 'info',
        code: 'SYS_REBOOT_SUCCESS',
        message: `تمت إعادة تشغيل الخادم ${targetServer.name} يدوياً بنجاح واستعادة الحالة الطبيعية.`,
        stackTrace: `Manual restart dispatched via web console.\nSystem daemon re-initialized all worker sockets.`,
        timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
        resolved: true,
        resolvedAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
      };
      setIncidents((prev) => [newInc, ...prev]);
    }
  };

  const handleToggleMaintenance = (serverId: string) => {
    setServers((prev) =>
      prev.map((s) => {
        if (s.id === serverId) {
          const nextStatus = s.status === 'maintenance' ? 'healthy' : 'maintenance';
          return { ...s, status: nextStatus };
        }
        return s;
      })
    );
  };

  const handleDeleteServer = (serverId: string) => {
    setServers((prev) => prev.filter((s) => s.id !== serverId));
  };

  const handleAddServer = (newServerData: Omit<Server, 'id' | 'uptimeDays' | 'lastPing'>) => {
    const newServer: Server = {
      ...newServerData,
      id: `srv-${Date.now().toString().slice(-4)}`,
      uptimeDays: 0,
      lastPing: 'منذ ثانية',
    };
    setServers((prev) => [newServer, ...prev]);
  };

  // Incident Actions
  const handleResolveIncident = (incidentId: string) => {
    setIncidents((prev) =>
      prev.map((inc) => {
        if (inc.id === incidentId) {
          return {
            ...inc,
            resolved: true,
            resolvedAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
          };
        }
        return inc;
      })
    );
  };

  const handleSimulateIncident = () => {
    if (servers.length === 0) return;
    const randomServer = servers[Math.floor(Math.random() * servers.length)];
    const mockErrors = [
      {
        code: 'ERR_HIGH_CPU_SPIKE',
        severity: 'warning' as const,
        message: `ارتفاع حاد في استهلاك المعالج تجاوز 92% على ${randomServer.name} بسبب معالجة دفعات متزامنة.`,
        stack: `PID 14088 node [worker-thread] consuming 94% CPU.\nGarbage collector frequency tripled in the last 60 seconds.`,
      },
      {
        code: 'ERR_HTTP_502_BAD_GATEWAY',
        severity: 'critical' as const,
        message: `توقف مفاجئ في استجابة خدمة البروكسي الداخلية على الخادم ${randomServer.name}.`,
        stack: `connect() failed (111: Connection refused) while connecting to upstream.\nworker process 3108 exited on signal 11 (SIGSEGV).`,
      },
      {
        code: 'WARN_DISK_SPACE_THRESHOLD',
        severity: 'warning' as const,
        message: `المساحة المتبقية على قرص /var/log أقل من 12% على ${randomServer.name}.`,
        stack: `Filesystem /dev/nvme0n1p1 mounted on /var/log capacity at 88.4%.\nLogrotate schedule queue pending.`,
      },
    ];
    const picked = mockErrors[Math.floor(Math.random() * mockErrors.length)];

    const newIncident: Incident = {
      id: `inc-${Date.now()}`,
      serverId: randomServer.id,
      serverName: randomServer.name,
      severity: picked.severity,
      code: picked.code,
      message: picked.message,
      stackTrace: picked.stack,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      resolved: false,
    };

    setIncidents((prev) => [newIncident, ...prev]);

    // Update server status accordingly
    setServers((prev) =>
      prev.map((s) => {
        if (s.id === randomServer.id) {
          return {
            ...s,
            status: picked.severity === 'critical' ? 'critical' : 'warning',
            cpu: picked.severity === 'critical' ? 95 : 86,
          };
        }
        return s;
      })
    );
  };

  // Deployment Actions
  const handleRedeploy = (deploymentId: string) => {
    setDeployments((prev) =>
      prev.map((d) => {
        if (d.id === deploymentId) {
          return {
            ...d,
            status: 'in_progress',
          };
        }
        return d;
      })
    );

    setTimeout(() => {
      setDeployments((prev) =>
        prev.map((d) => {
          if (d.id === deploymentId) {
            return {
              ...d,
              status: 'successful',
              timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
            };
          }
          return d;
        })
      );
    }, 2000);
  };

  const handleRollback = (deploymentId: string) => {
    setDeployments((prev) =>
      prev.map((d) => {
        if (d.id === deploymentId) {
          return {
            ...d,
            status: 'rolled_back',
            changeLog: `[تراجع تلقائي] تم التراجع عن هذا الإصدار للنسخة السابقة المستقرة.`,
          };
        }
        return d;
      })
    );
  };

  const handleAddNewDeployment = (newDepData: Omit<Deployment, 'id' | 'timestamp'>) => {
    const newDep: Deployment = {
      ...newDepData,
      id: `dep-${Date.now().toString().slice(-4)}`,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
    };
    setDeployments((prev) => [newDep, ...prev]);
  };

  // Reset Data to defaults
  const handleResetData = () => {
    if (window.confirm('هل ترغب في إعادة تعيين كافة البيانات إلى النماذج الافتراضية؟')) {
      setServers(INITIAL_SERVERS);
      setIncidents(INITIAL_INCIDENTS);
      setDeployments(INITIAL_DEPLOYMENTS);
      localStorage.removeItem('serverops_servers');
      localStorage.removeItem('serverops_incidents');
      localStorage.removeItem('serverops_deployments');
    }
  };

  const handleExportAll = () => {
    exportServersToCSV(servers);
    exportIncidentsToCSV(incidents);
    exportDeploymentsToCSV(deployments);
  };

  const targetServerForAi = servers.find((s) => s.id === selectedIncidentForAi?.serverId);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased selection:bg-indigo-600 selection:text-white">
      {/* Header */}
      <DashboardHeader
        isDarkMode={isDarkMode}
        onToggleDarkMode={() => setIsDarkMode((prev) => !prev)}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        onOpenAuditModal={() => setIsAuditModalOpen(true)}
        onResetData={handleResetData}
        onExportAll={handleExportAll}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8">
        {/* Top Context Subheader */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium text-indigo-400 mb-1">
              <span>مركز التحكم الموحد</span>
              <span aria-hidden="true">·</span>
              <span>DevOps & Infrastructure Console</span>
              <span aria-hidden="true">·</span>
              <span className="text-emerald-400">اتصال حي نشط</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-white">
              {activeTab === 'overview' && 'لوحة قيادة الخوادم والأنظمة'}
              {activeTab === 'servers' && 'إدارة وحالة كل خادم'}
              {activeTab === 'incidents' && 'سجل الأخطاء والحوادث التشغيلية'}
              {activeTab === 'deployments' && 'سجل آخر عمليات النشر البرمجي'}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsAuditModalOpen(true)}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/40 transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>فحص شامل بـ Gemini 3.8</span>
            </button>

            <button
              onClick={handleExportAll}
              className="px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5 text-slate-400" />
              <span>تصدير كافة البيانات (CSV)</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* KPI Cards */}
            <ServerOverviewCards
              servers={servers}
              incidents={incidents}
              deployments={deployments}
            />

            {/* Live Metrics Chart */}
            <InteractiveMetricsChart metrics={INITIAL_METRICS_24H} />

            {/* Quick Server Grid preview */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <ServerIcon className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-base font-bold text-white">الخوادم الحالية</h3>
                </div>
                <button
                  onClick={() => setActiveTab('servers')}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                >
                  عرض كافة الخوادم وتفاصيلها ←
                </button>
              </div>

              <ServerGrid
                servers={servers.slice(0, 6)}
                onRestartServer={handleRestartServer}
                onToggleMaintenance={handleToggleMaintenance}
                onDeleteServer={handleDeleteServer}
                onAddServer={handleAddServer}
              />
            </div>

            {/* Split row: Recent Incidents & Deployments */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
              {/* Unresolved Incidents mini-list */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-400" />
                    <h4 className="text-sm font-bold text-white">آخر الأخطاء والحوادث المسجلة</h4>
                  </div>
                  <button
                    onClick={() => setActiveTab('incidents')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                  >
                    السجل الكامل ({incidents.length})
                  </button>
                </div>

                <div className="space-y-3">
                  {incidents.slice(0, 3).map((inc) => (
                    <div
                      key={inc.id}
                      className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              inc.severity === 'critical'
                                ? 'bg-rose-950 text-rose-400 border border-rose-800'
                                : inc.severity === 'warning'
                                ? 'bg-amber-950 text-amber-400 border border-amber-800'
                                : 'bg-sky-950 text-sky-400 border border-sky-800'
                            }`}
                          >
                            {inc.code}
                          </span>
                          <span className="text-slate-400 font-mono text-[11px]">
                            @{inc.serverName}
                          </span>
                        </div>
                        <p className="text-slate-300 line-clamp-1">{inc.message}</p>
                      </div>

                      <button
                        onClick={() => setSelectedIncidentForAi(inc)}
                        className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-indigo-600/30 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/40 transition-colors whitespace-nowrap shrink-0 flex items-center gap-1"
                      >
                        <Sparkles className="w-3 h-3" />
                        <span>تحليل</span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Deployments mini-list */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Rocket className="w-4 h-4 text-violet-400" />
                    <h4 className="text-sm font-bold text-white">آخر عمليات النشر (CI/CD)</h4>
                  </div>
                  <button
                    onClick={() => setActiveTab('deployments')}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                  >
                    عرض الكل ({deployments.length})
                  </button>
                </div>

                <div className="space-y-3">
                  {deployments.slice(0, 3).map((dep) => (
                    <div
                      key={dep.id}
                      className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-white bg-slate-900 px-1.5 py-0.5 rounded border border-slate-700">
                            {dep.version}
                          </span>
                          <span className="text-indigo-400 font-mono">{dep.serviceName}</span>
                        </div>
                        <p className="text-slate-400 line-clamp-1 text-[11px]">{dep.changeLog}</p>
                      </div>

                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-bold whitespace-nowrap shrink-0 ${
                          dep.status === 'successful'
                            ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800'
                            : dep.status === 'failed'
                            ? 'text-rose-400 bg-rose-950/60 border border-rose-800'
                            : 'text-amber-400 bg-amber-950/60 border border-amber-800'
                        }`}
                      >
                        {dep.status === 'successful'
                          ? 'ناجح'
                          : dep.status === 'failed'
                          ? 'فشل'
                          : 'تراجع'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Servers Management */}
        {activeTab === 'servers' && (
          <ServerGrid
            servers={servers}
            onRestartServer={handleRestartServer}
            onToggleMaintenance={handleToggleMaintenance}
            onDeleteServer={handleDeleteServer}
            onAddServer={handleAddServer}
          />
        )}

        {/* Tab 3: Error & Incident Logs */}
        {activeTab === 'incidents' && (
          <ErrorLogViewer
            incidents={incidents}
            servers={servers}
            onResolveIncident={handleResolveIncident}
            onAnalyzeWithAI={(inc) => setSelectedIncidentForAi(inc)}
            onSimulateIncident={handleSimulateIncident}
          />
        )}

        {/* Tab 4: Deployments Tracker */}
        {activeTab === 'deployments' && (
          <DeploymentTracker
            deployments={deployments}
            servers={servers}
            onRedeploy={handleRedeploy}
            onRollback={handleRollback}
            onAddNewDeployment={handleAddNewDeployment}
          />
        )}
      </main>

      {/* AI Modals */}
      {selectedIncidentForAi && (
        <AiIncidentModal
          incident={selectedIncidentForAi}
          server={targetServerForAi}
          onClose={() => setSelectedIncidentForAi(null)}
          onResolveIncident={handleResolveIncident}
        />
      )}

      {isAuditModalOpen && (
        <AiAuditModal
          servers={servers}
          incidents={incidents}
          deployments={deployments}
          onClose={() => setIsAuditModalOpen(false)}
        />
      )}

      {/* Footer */}
      <footer className="py-6 border-t border-slate-800 text-center text-xs text-slate-500 bg-slate-950">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-400">منظومة رصد الخوادم</span>
            <span>·</span>
            <span>بيانات محفوظة تلقائياً في المتصفح</span>
          </div>
          <div className="text-slate-400">
            مدعوم بنموذج Google Gemini 3.8 Flash لتحليل الأخطاء وتدقيق البنية التحتية
          </div>
        </div>
      </footer>
    </div>
  );
}
