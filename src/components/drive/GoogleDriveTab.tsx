import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  listDriveFiles,
  createDriveFolder,
  uploadDriveFile,
  deleteDriveFile,
  getDriveStorageQuota,
  DriveFile,
  DriveStorageQuota,
} from '../../services/googleDriveService';
import { googleSignIn, logout } from '../../services/googleAuth';
import { Server, Incident, Deployment } from '../../types/serverDashboard';
import {
  Folder,
  FileText,
  FileCode,
  FileSpreadsheet,
  Download,
  Trash2,
  ExternalLink,
  Plus,
  RefreshCw,
  Search,
  Cloud,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  LogOut,
  FolderPlus,
  ShieldCheck,
  Loader2,
} from 'lucide-react';

interface GoogleDriveTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  deployments: Deployment[];
  onAuthSuccess: (user: User, token: string) => void;
  onLogout: () => void;
}

export const GoogleDriveTab: React.FC<GoogleDriveTabProps> = ({
  user,
  token,
  servers,
  incidents,
  deployments,
  onAuthSuccess,
  onLogout,
}) => {
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isSigningIn, setIsSigningIn] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [quota, setQuota] = useState<DriveStorageQuota>({});
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Modals / Confirmation Dialog states
  const [isNewFolderModalOpen, setIsNewFolderModalOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [fileToDelete, setFileToDelete] = useState<DriveFile | null>(null);
  const [isBackupConfirmOpen, setIsBackupConfirmOpen] = useState(false);
  const [backupFormat, setBackupFormat] = useState<'json' | 'csv'>('json');

  const fetchFiles = async () => {
    if (!token) return;
    setLoading(true);
    setStatusMessage(null);
    try {
      const [fetchedFiles, fetchedQuota] = await Promise.all([
        listDriveFiles(token, undefined, searchQuery),
        getDriveStorageQuota(token),
      ]);
      setFiles(fetchedFiles);
      setQuota(fetchedQuota);
    } catch (err: any) {
      console.error('Error listing Drive files:', err);
      setStatusMessage({ text: err.message || 'فشل جلب ملفات Google Drive', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchFiles();
    }
  }, [token]);

  const handleSignIn = async () => {
    setIsSigningIn(true);
    setStatusMessage(null);
    try {
      const result = await googleSignIn();
      if (result) {
        onAuthSuccess(result.user, result.accessToken);
        setStatusMessage({ text: 'تم تسجيل الدخول وربط Google Drive بنجاح!', type: 'success' });
      }
    } catch (err: any) {
      console.error('Sign in error:', err);
      setStatusMessage({ text: err.message || 'تعذر تسجيل الدخول بحساب Google', type: 'error' });
    } finally {
      setIsSigningIn(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    onLogout();
    setFiles([]);
    setQuota({});
    setStatusMessage({ text: 'تم تسجيل الخروج بنجاح.', type: 'success' });
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !newFolderName.trim()) return;
    try {
      await createDriveFolder(token, newFolderName.trim());
      setNewFolderName('');
      setIsNewFolderModalOpen(false);
      setStatusMessage({ text: 'تم إنشاء المجلد بنجاح في Google Drive!', type: 'success' });
      fetchFiles();
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'فشل إنشاء المجلد', type: 'error' });
    }
  };

  const handleBackupToDrive = async () => {
    if (!token) return;
    try {
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
      let filename = '';
      let content = '';
      let mimeType = '';

      if (backupFormat === 'json') {
        filename = `نسخة_احتياطية_الخوادم_${timestamp}.json`;
        content = JSON.stringify(
          {
            exportedAt: new Date().toISOString(),
            serversCount: servers.length,
            servers,
            incidents,
            deployments,
          },
          null,
          2
        );
        mimeType = 'application/json';
      } else {
        filename = `تقرير_الخوادم_الشامل_${timestamp}.csv`;
        const headers = ['المعرف', 'اسم الخادم', 'عنوان IP', 'النوع', 'المنطقة', 'الحالة', 'CPU %', 'RAM %'];
        const rows = servers.map((s) => [
          s.id,
          `"${s.name}"`,
          s.ip,
          s.type,
          `"${s.region}"`,
          s.status,
          s.cpu,
          s.memory,
        ]);
        content = '\uFEFF' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
        mimeType = 'text/csv;charset=utf-8;';
      }

      await uploadDriveFile(token, filename, content, mimeType);
      setIsBackupConfirmOpen(false);
      setStatusMessage({ text: `تم حفظ ${filename} بنجاح في حسابك على Google Drive!`, type: 'success' });
      fetchFiles();
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'فشل رفع النسخة الاحتياطية إلى Google Drive', type: 'error' });
    }
  };

  const handleDeleteConfirmed = async () => {
    if (!token || !fileToDelete) return;
    try {
      await deleteDriveFile(token, fileToDelete.id);
      setStatusMessage({ text: `تم حذف "${fileToDelete.name}" من Google Drive بنجاح.`, type: 'success' });
      setFileToDelete(null);
      fetchFiles();
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'فشل حذف الملف من Google Drive', type: 'error' });
    }
  };

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes('folder')) {
      return <Folder className="w-5 h-5 text-amber-400" />;
    }
    if (mimeType.includes('json') || mimeType.includes('code')) {
      return <FileCode className="w-5 h-5 text-indigo-400" />;
    }
    if (mimeType.includes('csv') || mimeType.includes('spreadsheet')) {
      return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
    }
    return <FileText className="w-5 h-5 text-slate-400" />;
  };

  const formatFileSize = (bytes?: string) => {
    if (!bytes) return '-';
    const num = parseInt(bytes, 10);
    if (isNaN(num)) return '-';
    if (num < 1024) return `${num} B`;
    if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
    return `${(num / (1024 * 1024)).toFixed(1)} MB`;
  };

  // If not authenticated, show sign-in prompt
  if (!token || !user) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center max-w-2xl mx-auto shadow-xl space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-indigo-950/80 border border-indigo-800/80 flex items-center justify-center mx-auto text-indigo-400">
          <Cloud className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h3 className="text-xl sm:text-2xl font-bold text-white">
            ربط حساب Google Drive للأرشفة والنسخ الاحتياطي
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-lg mx-auto">
            قم بتسجيل الدخول بحساب Google لتمكين المنظومة من حفظ نسخ احتياطية دورية لسجلات الخوادم، تقارير التدقيق، وأرشيف الأخطاء مباشرة إلى حسابك في Google Drive بأمان كامل.
          </p>
        </div>

        {statusMessage && (
          <div
            className={`p-3 rounded-xl text-xs ${
              statusMessage.type === 'success'
                ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
                : 'bg-rose-950/60 text-rose-300 border border-rose-800'
            }`}
          >
            {statusMessage.text}
          </div>
        )}

        <div className="pt-2 flex justify-center">
          {/* Official Sign in with Google Button */}
          <button
            onClick={handleSignIn}
            disabled={isSigningIn}
            className="flex items-center gap-3 px-6 py-3 bg-white hover:bg-slate-50 text-slate-800 rounded-xl font-bold text-sm shadow-md hover:shadow-lg transition-all disabled:opacity-50"
          >
            {isSigningIn ? (
              <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 48 48">
                <path
                  fill="#EA4335"
                  d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
                />
                <path
                  fill="#4285F4"
                  d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
                />
                <path
                  fill="#FBBC05"
                  d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
                />
                <path
                  fill="#34A853"
                  d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
                />
              </svg>
            )}
            <span>تسجيل الدخول باستخدام Google</span>
          </button>
        </div>

        <div className="pt-4 text-[11px] text-slate-500 flex items-center justify-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>يتم الاتصال مباشرة بخدمات Google مع الحفاظ على خصوصية بياناتك</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* User Connected Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {user.photoURL ? (
            <img
              src={user.photoURL}
              alt={user.displayName || 'User'}
              className="w-11 h-11 rounded-full border border-slate-700"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-11 h-11 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-sm">
              {user.displayName?.[0] || 'U'}
            </div>
          )}

          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">
                {user.displayName || 'مستخدم Google Drive'}
              </h3>
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                متصل بـ Drive
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">{user.email}</p>
          </div>
        </div>

        {/* Storage info & logout */}
        <div className="flex items-center gap-3">
          {quota.usage && quota.limit && (
            <div className="text-right text-xs hidden md:block">
              <span className="text-slate-400">سعة التخزين:</span>{' '}
              <span className="text-slate-200 font-mono tabular-nums">
                {formatFileSize(quota.usage)} / {formatFileSize(quota.limit)}
              </span>
            </div>
          )}

          <button
            onClick={handleLogout}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <LogOut className="w-3.5 h-3.5 text-slate-400" />
            <span>تسجيل الخروج</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div
          className={`p-3.5 rounded-xl text-xs flex items-center justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
              : 'bg-rose-950/60 text-rose-300 border border-rose-800'
          }`}
        >
          <span>{statusMessage.text}</span>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Control bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Search in drive */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') fetchFiles();
              }}
              placeholder="البحث في ملفات ومجلدات Google Drive..."
              className="w-full pr-10 pl-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={fetchFiles}
              title="تحديث قائمة الملفات"
              disabled={loading}
              className="p-2.5 text-slate-300 hover:text-white rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>

            <button
              onClick={() => setIsNewFolderModalOpen(true)}
              className="px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <FolderPlus className="w-3.5 h-3.5 text-amber-400" />
              <span>مجلد جديد</span>
            </button>

            <button
              onClick={() => setIsBackupConfirmOpen(true)}
              className="px-4 py-2.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Cloud className="w-4 h-4" />
              <span>أرشفة تقرير السيرفرات لـ Drive</span>
            </button>
          </div>
        </div>
      </div>

      {/* Files List Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>قائمة الملفات في حساب Google Drive ({files.length} عنصر)</span>
          <span>ترتيب حسب الأحدث تعديلاً</span>
        </div>

        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center gap-3 text-slate-400">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            <p className="text-xs">جاري جلب الملفات من Google Drive...</p>
          </div>
        ) : files.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-right text-xs">
              <thead className="bg-slate-950/60 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">اسم الملف / المجلد</th>
                  <th className="py-3 px-4">الحجم</th>
                  <th className="py-3 px-4">آخر تعديل</th>
                  <th className="py-3 px-4 text-left">الإجراءات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {files.map((file) => (
                  <tr
                    key={file.id}
                    className="hover:bg-slate-800/40 transition-colors group text-slate-200"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        {getFileIcon(file.mimeType)}
                        <span className="font-medium text-white truncate max-w-xs sm:max-w-md">
                          {file.name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono tabular-nums">
                      {formatFileSize(file.size)}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono">
                      {file.modifiedTime ? file.modifiedTime.slice(0, 10) : '-'}
                    </td>
                    <td className="py-3 px-4 text-left">
                      <div className="flex items-center justify-end gap-2">
                        {file.webViewLink && (
                          <a
                            href={file.webViewLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 text-slate-400 hover:text-indigo-400 transition-colors"
                            title="فتح في Google Drive"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}

                        <button
                          onClick={() => setFileToDelete(file)}
                          className="p-1.5 text-slate-400 hover:text-rose-400 transition-colors"
                          title="حذف الملف"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-16 text-slate-400 space-y-2">
            <Cloud className="w-10 h-10 mx-auto text-slate-600" />
            <p className="text-sm font-bold text-white">لا توجد ملفات حالياً</p>
            <p className="text-xs text-slate-500">
              يمكنك استخدام زر "أرشفة تقرير السيرفرات لـ Drive" أعلاه لرفع أول نسخة احتياطية.
            </p>
          </div>
        )}
      </div>

      {/* Confirmation Dialog: Backup to Drive */}
      {isBackupConfirmOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-slate-100 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                <Cloud className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">تأكيد الأرشفة إلى Google Drive</h4>
                <p className="text-xs text-slate-400">حفظ نسخة احتياطية لمنظومة الخوادم</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              سيتم إنشاء ملف نسخة احتياطية يحتوي على حالة {servers.length} خوادم، {incidents.length} حوادث مسجلة، و{deployments.length} عمليات نشر، وحفظه مباشرة في حسابك على Google Drive.
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                صيغة الملف المرغوبة:
              </label>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => setBackupFormat('json')}
                  className={`p-2.5 rounded-xl border text-center transition-colors font-semibold ${
                    backupFormat === 'json'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-slate-950 text-slate-400 border-slate-800'
                  }`}
                >
                  نسخة شاملة (JSON)
                </button>
                <button
                  type="button"
                  onClick={() => setBackupFormat('csv')}
                  className={`p-2.5 rounded-xl border text-center transition-colors font-semibold ${
                    backupFormat === 'csv'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-slate-950 text-slate-400 border-slate-800'
                  }`}
                >
                  جدول بيانات (CSV)
                </button>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsBackupConfirmOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                إلغاء
              </button>
              <button
                type="button"
                onClick={handleBackupToDrive}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md flex items-center gap-1.5"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>تأكيد والرفع الآن</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog: Delete File (Mandatory for destructive operations) */}
      {fileToDelete && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-slate-100 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-rose-600/20 text-rose-400 border border-rose-500/30">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">تأكيد حذف الملف</h4>
                <p className="text-xs text-slate-400">عملية حذف من Google Drive</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3.5 rounded-xl border border-slate-800">
              هل أنت متأكد من رغبتك في حذف الملف التالي نهائياً من Google Drive؟
              <span className="block font-bold text-rose-300 mt-1 font-mono break-all">
                "{fileToDelete.name}"
              </span>
            </p>

            <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setFileToDelete(null)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                إلغاء التراجع
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirmed}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-rose-600 hover:bg-rose-500 text-white shadow-md flex items-center gap-1.5"
              >
                <Trash2 className="w-4 h-4" />
                <span>نعم، احذف الملف</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Folder Modal */}
      {isNewFolderModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-6 text-slate-100 shadow-2xl space-y-4">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <FolderPlus className="w-4 h-4 text-amber-400" />
              إنشاء مجلد جديد في Google Drive
            </h4>

            <form onSubmit={handleCreateFolder} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">اسم المجلد:</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ServerOps_Backups"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsNewFolderModalOpen(false)}
                  className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md"
                >
                  إنشاء المجلد
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
