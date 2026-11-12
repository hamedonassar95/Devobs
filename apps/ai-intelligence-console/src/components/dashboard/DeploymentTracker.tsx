import React, { useState } from 'react';
import { Deployment, DeploymentStatus, Server } from '../../types/serverDashboard';
import {
  Rocket,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Clock,
  Search,
  Download,
  Plus,
  GitBranch,
  GitCommit,
  User,
} from 'lucide-react';
import { exportDeploymentsToCSV } from '../../utils/dashboardUtils';

interface DeploymentTrackerProps {
  deployments: Deployment[];
  servers: Server[];
  onRedeploy: (deploymentId: string) => void;
  onRollback: (deploymentId: string) => void;
  onAddNewDeployment: (newDep: Omit<Deployment, 'id' | 'timestamp'>) => void;
}

export const DeploymentTracker: React.FC<DeploymentTrackerProps> = ({
  deployments,
  servers,
  onRedeploy,
  onRollback,
  onAddNewDeployment,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // New deployment form state
  const [formData, setFormData] = useState({
    version: 'v2.8.5',
    commitHash: 'a1b2c3d',
    serviceName: 'core-payment-gateway',
    branch: 'main',
    author: 'أحمد السعيد (DevOps Lead)',
    status: 'successful' as DeploymentStatus,
    durationSeconds: 95,
    changeLog: 'تحديثات أمان جديدة وتحسين كفاءة استعلامات قاعدة البيانات.',
    targetServers: ['srv-01', 'srv-02'],
  });

  const handleCreateDeployment = (e: React.FormEvent) => {
    e.preventDefault();
    onAddNewDeployment(formData);
    setFormData({
      version: `v2.8.${deployments.length + 5}`,
      commitHash: Math.random().toString(16).substring(2, 9),
      serviceName: 'core-payment-gateway',
      branch: 'main',
      author: 'مهندس النظم السحابية',
      status: 'successful',
      durationSeconds: 110,
      changeLog: 'إصدار جديد مع تحسينات في الأداء والتوافقية.',
      targetServers: ['srv-01'],
    });
    setIsModalOpen(false);
  };

  const filteredDeployments = deployments.filter((dep) => {
    const matchesSearch =
      dep.version.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dep.serviceName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dep.commitHash.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dep.author.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || dep.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: DeploymentStatus) => {
    switch (status) {
      case 'successful':
        return (
          <span className="text-xs font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-800 px-2.5 py-1 rounded-md flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            ناجح (Success)
          </span>
        );
      case 'failed':
        return (
          <span className="text-xs font-bold text-rose-400 bg-rose-950/80 border border-rose-800 px-2.5 py-1 rounded-md flex items-center gap-1.5">
            <XCircle className="w-3.5 h-3.5" />
            فشل النشر (Failed)
          </span>
        );
      case 'in_progress':
        return (
          <span className="text-xs font-bold text-sky-400 bg-sky-950/80 border border-sky-800 px-2.5 py-1 rounded-md flex items-center gap-1.5 animate-pulse">
            <Clock className="w-3.5 h-3.5" />
            قيد التنفيذ
          </span>
        );
      case 'rolled_back':
        return (
          <span className="text-xs font-bold text-amber-400 bg-amber-950/80 border border-amber-800 px-2.5 py-1 rounded-md flex items-center gap-1.5">
            <RotateCcw className="w-3.5 h-3.5" />
            تم التراجع (Rolled Back)
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Search and Action Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Search Field */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="البحث بالإصدار، اسم الخدمة، رمز الكوميت، أو اسم المطور..."
              className="w-full pr-10 pl-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => exportDeploymentsToCSV(filteredDeployments)}
              className="px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>تصدير CSV</span>
            </button>

            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>إطلاق نشر جديد</span>
            </button>
          </div>
        </div>

        {/* Status Filters */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-800/80 text-xs">
          <span className="text-slate-400 ml-2 font-medium">حالة النشر:</span>
          {[
            { id: 'all', label: 'الكل' },
            { id: 'successful', label: 'ناجح' },
            { id: 'failed', label: 'فشل' },
            { id: 'rolled_back', label: 'تم التراجع' },
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
      </div>

      {/* Deployments List */}
      <div className="space-y-3">
        {filteredDeployments.map((deployment) => (
          <div
            key={deployment.id}
            className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-bold text-white bg-slate-950 px-2.5 py-0.5 rounded-lg border border-slate-800">
                    {deployment.version}
                  </span>
                  <span className="text-xs font-bold text-indigo-400 font-mono">
                    {deployment.serviceName}
                  </span>
                  {getStatusBadge(deployment.status)}
                </div>

                <p className="text-xs sm:text-sm text-slate-300 pt-1 leading-relaxed">
                  {deployment.changeLog}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
                <button
                  onClick={() => onRedeploy(deployment.id)}
                  title="إعادة تشغيل النشر"
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
                >
                  <Rocket className="w-3.5 h-3.5 text-indigo-400" />
                  <span>إعادة النشر</span>
                </button>

                {deployment.status === 'successful' && (
                  <button
                    onClick={() => onRollback(deployment.id)}
                    title="تراجع عن هذا الإصدار"
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-950/70 hover:bg-rose-900 text-rose-300 border border-rose-800 transition-colors flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>تراجع (Rollback)</span>
                  </button>
                )}
              </div>
            </div>

            {/* Metadata Footer */}
            <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 font-mono">
              <div className="flex flex-wrap items-center gap-4">
                <span className="flex items-center gap-1">
                  <GitBranch className="w-3.5 h-3.5 text-slate-500" />
                  {deployment.branch}
                </span>
                <span className="flex items-center gap-1">
                  <GitCommit className="w-3.5 h-3.5 text-slate-500" />
                  {deployment.commitHash}
                </span>
                <span className="flex items-center gap-1">
                  <User className="w-3.5 h-3.5 text-slate-500" />
                  {deployment.author}
                </span>
              </div>

              <div className="flex items-center gap-3">
                <span>المدة: {deployment.durationSeconds} ثانية</span>
                <span aria-hidden="true">·</span>
                <span>{deployment.timestamp}</span>
              </div>
            </div>
          </div>
        ))}

        {filteredDeployments.length === 0 && (
          <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-2xl text-slate-400">
            <Rocket className="w-10 h-10 mx-auto text-slate-600 mb-3" />
            <p className="text-base font-bold text-white mb-1">لم يتم العثور على عمليات نشر مطابقة</p>
            <p className="text-xs text-slate-500">جرب تعديل شروط البحث أو الفلاتر المختارة.</p>
          </div>
        )}
      </div>

      {/* New Deployment Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 text-slate-100 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Rocket className="w-5 h-5 text-indigo-500" />
                إطلاق عملية نشر جديدة (New Deployment)
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateDeployment} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    رقم الإصدار (Version):
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.version}
                    onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    رمز الكوميت (Git Hash):
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.commitHash}
                    onChange={(e) => setFormData({ ...formData, commitHash: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  الخدمة المستهدفة (Service Name):
                </label>
                <input
                  type="text"
                  required
                  value={formData.serviceName}
                  onChange={(e) => setFormData({ ...formData, serviceName: e.target.value })}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  سجل التغييرات وموجز التحديث:
                </label>
                <textarea
                  required
                  rows={3}
                  value={formData.changeLog}
                  onChange={(e) => setFormData({ ...formData, changeLog: e.target.value })}
                  placeholder="اكتب التغييرات التي تم تضمينها في هذا الإصدار..."
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md flex items-center gap-1.5"
                >
                  <Rocket className="w-3.5 h-3.5" />
                  <span>بدء النشر الآن</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
