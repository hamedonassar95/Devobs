import { Server, Incident, Deployment } from '../types/serverDashboard';

export function downloadTextFile(filename: string, content: string, mimeType = 'text/plain;charset=utf-8;') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportServersToCSV(servers: Server[]) {
  const headers = ['المعرف', 'اسم الخادم', 'عنوان IP', 'النوع', 'المنطقة', 'البيئة', 'الحالة', 'المعالج %', 'الذاكرة %', 'القرص %', 'الشبكة Mbps', 'مدة التشغيل (يوم)', 'نظام التشغيل'];
  const rows = servers.map(s => [
    s.id,
    `"${s.name}"`,
    s.ip,
    s.type,
    `"${s.region}"`,
    s.environment,
    s.status,
    s.cpu,
    s.memory,
    s.disk,
    s.networkMbps,
    s.uptimeDays,
    `"${s.os}"`,
  ]);

  const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  downloadTextFile(`تقرير_الخوادم_${new Date().toISOString().slice(0, 10)}.csv`, csvContent, 'text/csv;charset=utf-8;');
}

export function exportIncidentsToCSV(incidents: Incident[]) {
  const headers = ['المعرف', 'الخادم', 'كود الخطأ', 'مستوى الخطورة', 'الرسالة', 'الحالة', 'تاريخ الحدوث'];
  const rows = incidents.map(i => [
    i.id,
    `"${i.serverName}"`,
    i.code,
    i.severity,
    `"${i.message.replace(/"/g, '""')}"`,
    i.resolved ? 'تم الحل' : 'قيد المتابعة',
    i.timestamp,
  ]);

  const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  downloadTextFile(`سجل_أخطاء_الخوادم_${new Date().toISOString().slice(0, 10)}.csv`, csvContent, 'text/csv;charset=utf-8;');
}

export function exportDeploymentsToCSV(deployments: Deployment[]) {
  const headers = ['المعرف', 'الإصدار', 'الخدمة', 'الفرع', 'المسؤول', 'حالة النشر', 'المدة (ثواني)', 'التاريخ', 'سجل التغييرات'];
  const rows = deployments.map(d => [
    d.id,
    d.version,
    `"${d.serviceName}"`,
    d.branch,
    `"${d.author}"`,
    d.status,
    d.durationSeconds,
    d.timestamp,
    `"${d.changeLog.replace(/"/g, '""')}"`,
  ]);

  const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  downloadTextFile(`سجل_عمليات_النشر_${new Date().toISOString().slice(0, 10)}.csv`, csvContent, 'text/csv;charset=utf-8;');
}
