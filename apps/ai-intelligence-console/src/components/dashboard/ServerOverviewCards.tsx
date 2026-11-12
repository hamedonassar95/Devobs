import React from 'react';
import { Server, Incident, Deployment } from '../../types/serverDashboard';
import { Server as ServerIcon, CheckCircle2, AlertTriangle, XCircle, Activity, ShieldAlert, Rocket } from 'lucide-react';

interface ServerOverviewCardsProps {
  servers: Server[];
  incidents: Incident[];
  deployments: Deployment[];
  onSelectFilter?: (type: string) => void;
}

export const ServerOverviewCards: React.FC<ServerOverviewCardsProps> = ({
  servers,
  incidents,
  deployments,
}) => {
  const healthyCount = servers.filter((s) => s.status === 'healthy').length;
  const warningCount = servers.filter((s) => s.status === 'warning').length;
  const criticalCount = servers.filter((s) => s.status === 'critical').length;
  const maintenanceCount = servers.filter((s) => s.status === 'maintenance').length;

  const avgCpu = Math.round(
    servers.reduce((acc, s) => acc + s.cpu, 0) / (servers.length || 1)
  );
  const avgMemory = Math.round(
    servers.reduce((acc, s) => acc + s.memory, 0) / (servers.length || 1)
  );

  const unresolvedIncidents = incidents.filter((i) => !i.resolved);
  const latestDeployment = deployments[0];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Card 1: Total Servers */}
      <div className="bg-slate-900 dark:bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-medium text-slate-400">إجمالي الخوادم المسجلة</span>
          <div className="p-2 rounded-lg bg-indigo-950/70 text-indigo-400 border border-indigo-800/60">
            <ServerIcon className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline justify-between">
          <span className="text-3xl font-extrabold text-white font-mono tabular-nums">
            {servers.length}
          </span>
          <span className="text-xs text-emerald-400 font-medium">99.98% جاهزية</span>
        </div>
        <div className="mt-3 text-[11px] text-slate-400 flex items-center gap-2">
          <span>{healthyCount} سليم</span>
          <span aria-hidden="true">·</span>
          <span>{maintenanceCount} صيانة</span>
        </div>
      </div>

      {/* Card 2: Server Health Distribution */}
      <div className="bg-slate-900 dark:bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-medium text-slate-400">حالات الاستقرار والضغط</span>
          <div className="p-2 rounded-lg bg-emerald-950/70 text-emerald-400 border border-emerald-800/60">
            <Activity className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="font-mono tabular-nums text-xl">{healthyCount}</span>
            <span className="text-slate-400 font-normal">سليم</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-amber-400 font-bold">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="font-mono tabular-nums text-xl">{warningCount}</span>
            <span className="text-slate-400 font-normal">ضغط</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-rose-400 font-bold">
            <XCircle className="w-3.5 h-3.5" />
            <span className="font-mono tabular-nums text-xl">{criticalCount}</span>
            <span className="text-slate-400 font-normal">حرج</span>
          </div>
        </div>
        <div className="mt-3 text-[11px] text-slate-400">
          متوسط الحمل: <span className="text-slate-200 font-mono tabular-nums">{avgCpu}% CPU</span> /{' '}
          <span className="text-slate-200 font-mono tabular-nums">{avgMemory}% RAM</span>
        </div>
      </div>

      {/* Card 3: Unresolved Incidents */}
      <div className="bg-slate-900 dark:bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-medium text-slate-400">الحوادث والأخطاء المفتوحة</span>
          <div className="p-2 rounded-lg bg-rose-950/70 text-rose-400 border border-rose-800/60">
            <ShieldAlert className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline justify-between">
          <span className={`text-3xl font-extrabold font-mono tabular-nums ${
            unresolvedIncidents.length > 0 ? 'text-rose-400' : 'text-emerald-400'
          }`}>
            {unresolvedIncidents.length}
          </span>
          <span className="text-xs text-slate-400">
            من إجمالي {incidents.length} حادثة
          </span>
        </div>
        <div className="mt-3 text-[11px] text-slate-400 truncate">
          {unresolvedIncidents.length > 0
            ? `أحدث خطأ: ${unresolvedIncidents[0].code}`
            : 'جميع الخوادم تعمل بدون حوادث نشطة'}
        </div>
      </div>

      {/* Card 4: Last Deployment */}
      <div className="bg-slate-900 dark:bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-medium text-slate-400">آخر عملية نشر (CI/CD)</span>
          <div className="p-2 rounded-lg bg-violet-950/70 text-violet-400 border border-violet-800/60">
            <Rocket className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline justify-between">
          <span className="text-xl font-bold text-white font-mono">
            {latestDeployment ? latestDeployment.version : 'N/A'}
          </span>
          <span
            className={`text-xs font-bold px-2 py-0.5 rounded ${
              latestDeployment?.status === 'successful'
                ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                : latestDeployment?.status === 'failed'
                ? 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
                : 'bg-amber-950/80 text-amber-400 border border-amber-800/60'
            }`}
          >
            {latestDeployment?.status === 'successful'
              ? 'ناجح'
              : latestDeployment?.status === 'failed'
              ? 'فشل'
              : latestDeployment?.status === 'rolled_back'
              ? 'تراجع'
              : 'جاري'}
          </span>
        </div>
        <div className="mt-3 text-[11px] text-slate-400 truncate">
          {latestDeployment?.serviceName} · {latestDeployment?.timestamp.slice(11, 16)}
        </div>
      </div>
    </div>
  );
};
