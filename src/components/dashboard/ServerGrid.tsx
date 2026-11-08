import React, { useState } from 'react';
import { Server, ServerStatus, ServerType, Environment } from '../../types/serverDashboard';
import {
  Search,
  Plus,
  RotateCw,
  Wrench,
  Trash2,
  Copy,
  Check,
  Download,
  Server as ServerIcon,
  HardDrive,
  Cpu,
  Wifi,
  ExternalLink,
} from 'lucide-react';
import { exportServersToCSV } from '../../utils/dashboardUtils';

interface ServerGridProps {
  servers: Server[];
  onRestartServer: (serverId: string) => void;
  onToggleMaintenance: (serverId: string) => void;
  onDeleteServer: (serverId: string) => void;
  onAddServer: (newServer: Omit<Server, 'id' | 'uptimeDays' | 'lastPing'>) => void;
}

export const ServerGrid: React.FC<ServerGridProps> = ({
  servers,
  onRestartServer,
  onToggleMaintenance,
  onDeleteServer,
  onAddServer,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [copiedIp, setCopiedIp] = useState<string | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Form state for new server
  const [formData, setFormData] = useState({
    name: '',
    ip: '',
    type: 'api' as ServerType,
    region: 'me-central2 (الرياض)',
    environment: 'production' as Environment,
    cpu: 25,
    memory: 40,
    disk: 35,
    networkMbps: 350,
    os: 'Ubuntu 24.04 LTS',
    status: 'healthy' as ServerStatus,
  });

  const handleCopyIp = (ip: string) => {
    navigator.clipboard.writeText(ip);
    setCopiedIp(ip);
    setTimeout(() => setCopiedIp(null), 2000);
  };

  const handleCreateServer = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.ip.trim()) return;

    onAddServer(formData);
    setFormData({
      name: '',
      ip: '',
      type: 'api',
      region: 'me-central2 (الرياض)',
      environment: 'production',
      cpu: 25,
      memory: 40,
      disk: 35,
      networkMbps: 350,
      os: 'Ubuntu 24.04 LTS',
      status: 'healthy',
    });
    setIsAddModalOpen(false);
  };

  const filteredServers = servers.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.ip.includes(searchQuery) ||
      s.region.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.os.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || s.status === statusFilter;
    const matchesType = typeFilter === 'all' || s.type === typeFilter;

    return matchesSearch && matchesStatus && matchesType;
  });

  const getStatusBadge = (status: ServerStatus) => {
    switch (status) {
      case 'healthy':
        return (
          <span className="text-xs font-bold text-emerald-400 bg-emerald-950/70 border border-emerald-800/80 px-2.5 py-1 rounded-md flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            سليم (Online)
          </span>
        );
      case 'warning':
        return (
          <span className="text-xs font-bold text-amber-400 bg-amber-950/70 border border-amber-800/80 px-2.5 py-1 rounded-md flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            ضغط عالي (Warning)
          </span>
        );
      case 'critical':
        return (
          <span className="text-xs font-bold text-rose-400 bg-rose-950/70 border border-rose-800/80 px-2.5 py-1 rounded-md flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            عطل حرج (Critical)
          </span>
        );
      case 'maintenance':
        return (
          <span className="text-xs font-bold text-slate-400 bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-md flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            تحت الصيانة
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Search and Filters Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Search Field */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="البحث بالاسم، عنوان IP، المنطقة، أو نظام التشغيل..."
              className="w-full pr-10 pl-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => exportServersToCSV(filteredServers)}
              className="px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>تصدير CSV</span>
            </button>

            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-4 py-2.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>إضافة خادم جديد</span>
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-800/80">
          {/* Status Filters */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-400 ml-2 font-medium">الحالة:</span>
            {[
              { id: 'all', label: 'الكل' },
              { id: 'healthy', label: 'سليم' },
              { id: 'warning', label: 'تحذير' },
              { id: 'critical', label: 'حرج' },
              { id: 'maintenance', label: 'صيانة' },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setStatusFilter(st.id)}
                className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                  statusFilter === st.id
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'text-slate-400 hover:text-white bg-slate-950 border border-slate-800'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          {/* Type Filters */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-400 ml-2 font-medium">النوع:</span>
            {[
              { id: 'all', label: 'الكل' },
              { id: 'api', label: 'API Gateway' },
              { id: 'database', label: 'Database' },
              { id: 'worker', label: 'Worker' },
              { id: 'cache', label: 'Cache' },
              { id: 'storage', label: 'Storage' },
            ].map((tp) => (
              <button
                key={tp.id}
                onClick={() => setTypeFilter(tp.id)}
                className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                  typeFilter === tp.id
                    ? 'bg-slate-700 text-white font-bold'
                    : 'text-slate-400 hover:text-white bg-slate-950 border border-slate-800'
                }`}
              >
                {tp.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Servers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredServers.map((server) => {
          const isIpCopied = copiedIp === server.ip;
          return (
            <div
              key={server.id}
              className={`bg-slate-900 border rounded-2xl p-5 flex flex-col justify-between transition-all shadow-sm ${
                server.status === 'critical'
                  ? 'border-rose-900/60 bg-rose-950/10'
                  : server.status === 'warning'
                  ? 'border-amber-900/60 bg-amber-950/10'
                  : 'border-slate-800'
              }`}
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <h4 className="text-sm font-bold text-white font-mono break-all">
                      {server.name}
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5">{server.region}</p>
                  </div>
                  {getStatusBadge(server.status)}
                </div>

                {/* IP & Specs Bar */}
                <div className="flex items-center justify-between text-xs bg-slate-950/80 rounded-xl px-3 py-2 border border-slate-800 mb-4 font-mono">
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <span>IP: {server.ip}</span>
                    <button
                      onClick={() => handleCopyIp(server.ip)}
                      title="نسخ عنوان IP"
                      className="text-slate-500 hover:text-slate-300"
                    >
                      {isIpCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <span className="text-indigo-400 uppercase font-semibold text-[11px]">
                    {server.type}
                  </span>
                </div>

                {/* Resource Gauges */}
                <div className="space-y-2.5 text-xs mb-4">
                  {/* CPU */}
                  <div>
                    <div className="flex justify-between text-slate-400 mb-1">
                      <span className="flex items-center gap-1">
                        <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                        المعالج (CPU)
                      </span>
                      <span className="font-mono tabular-nums text-slate-200">{server.cpu}%</span>
                    </div>
                    <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          server.cpu > 85 ? 'bg-rose-500' : server.cpu > 70 ? 'bg-amber-500' : 'bg-indigo-500'
                        }`}
                        style={{ width: `${server.cpu}%` }}
                      />
                    </div>
                  </div>

                  {/* RAM */}
                  <div>
                    <div className="flex justify-between text-slate-400 mb-1">
                      <span className="flex items-center gap-1">
                        <ServerIcon className="w-3.5 h-3.5 text-emerald-400" />
                        الذاكرة (RAM)
                      </span>
                      <span className="font-mono tabular-nums text-slate-200">{server.memory}%</span>
                    </div>
                    <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          server.memory > 85 ? 'bg-rose-500' : server.memory > 70 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${server.memory}%` }}
                      />
                    </div>
                  </div>

                  {/* Disk */}
                  <div>
                    <div className="flex justify-between text-slate-400 mb-1">
                      <span className="flex items-center gap-1">
                        <HardDrive className="w-3.5 h-3.5 text-sky-400" />
                        القرص (Storage)
                      </span>
                      <span className="font-mono tabular-nums text-slate-200">{server.disk}%</span>
                    </div>
                    <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          server.disk > 85 ? 'bg-rose-500' : 'bg-sky-500'
                        }`}
                        style={{ width: `${server.disk}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Telemetry info */}
                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 py-2 border-t border-slate-800/80 mb-4 font-mono">
                  <div className="flex items-center gap-1">
                    <Wifi className="w-3 h-3 text-slate-500" />
                    <span>{server.networkMbps} Mbps</span>
                  </div>
                  <div className="text-left text-slate-400">
                    تشغيل: {server.uptimeDays} يوم
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                <button
                  onClick={() => onRestartServer(server.id)}
                  title="إعادة تشغيل الخادم"
                  className="flex-1 py-1.5 px-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center justify-center gap-1"
                >
                  <RotateCw className="w-3.5 h-3.5 text-indigo-400" />
                  <span>إعادة تشغيل</span>
                </button>

                <button
                  onClick={() => onToggleMaintenance(server.id)}
                  title={server.status === 'maintenance' ? 'إنهاء الصيانة' : 'بدء الصيانة'}
                  className={`p-2 rounded-lg border transition-colors ${
                    server.status === 'maintenance'
                      ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border-slate-700'
                  }`}
                >
                  <Wrench className="w-3.5 h-3.5" />
                </button>

                <button
                  onClick={() => onDeleteServer(server.id)}
                  title="حذف الخادم"
                  className="p-2 rounded-lg bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 border border-slate-700 hover:border-rose-800 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredServers.length === 0 && (
        <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl text-slate-400">
          <ServerIcon className="w-10 h-10 mx-auto text-slate-600 mb-3" />
          <p className="text-base font-bold text-white mb-1">لم يتم العثور على خوادم مطابقة</p>
          <p className="text-xs text-slate-500">جرب تعديل شروط البحث أو الفلاتر المختارة.</p>
        </div>
      )}

      {/* Add Server Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 text-slate-100 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-500" />
                إضافة خادم جديد للمنظومة
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateServer} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  اسم الخادم (Hostname):
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. prod-api-edge-03"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs sm:text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    عنوان IP الداخلي:
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="10.240.10.28"
                    value={formData.ip}
                    onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">نوع الخدمة:</label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value as ServerType })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="api">API Gateway</option>
                    <option value="database">Database (SQL/NoSQL)</option>
                    <option value="worker">Background Worker</option>
                    <option value="cache">Redis / Memcached</option>
                    <option value="storage">Storage Cluster</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">المنطقة الجغرافية:</label>
                  <select
                    value={formData.region}
                    onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="me-central2 (الرياض)">me-central2 (الرياض)</option>
                    <option value="me-central1 (دبي)">me-central1 (دبي)</option>
                    <option value="eu-central-1 (فرانكفورت)">eu-central-1 (فرانكفورت)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">البيئة التشغيلية:</label>
                  <select
                    value={formData.environment}
                    onChange={(e) =>
                      setFormData({ ...formData, environment: e.target.value as Environment })
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="production">الإنتاج (Production)</option>
                    <option value="staging">بيئة الاختبار (Staging)</option>
                    <option value="development">التطوير (Dev)</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md"
                >
                  حفظ وتسجيل الخادم
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
