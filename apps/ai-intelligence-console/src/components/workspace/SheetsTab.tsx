import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  Table,
  Plus,
  RefreshCw,
  ExternalLink,
  Download,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FileSpreadsheet,
  Server as ServerIcon,
  ShieldAlert,
  Eye,
  Check,
  X,
  Layers,
} from 'lucide-react';
import {
  listGoogleSpreadsheets,
  getSpreadsheetDetails,
  readSpreadsheetValues,
  exportServerInventoryToNewSheet,
  exportIncidentsToNewSheet,
  SpreadsheetFileItem,
  SheetMetadata,
} from '../../services/googleSheetsService';
import { googleSignIn } from '../../services/googleAuth';
import { Server, Incident } from '../../types/serverDashboard';

interface SheetsTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  onAuthSuccess: (user: User, token: string) => void;
}

export function SheetsTab({ user, token, servers, incidents, onAuthSuccess }: SheetsTabProps) {
  const [spreadsheets, setSpreadsheets] = useState<SpreadsheetFileItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inspector state
  const [selectedSheetMeta, setSelectedSheetMeta] = useState<SheetMetadata | null>(null);
  const [selectedSheetTab, setSelectedSheetTab] = useState<string>('');
  const [sheetRows, setSheetRows] = useState<any[][]>([]);
  const [isLoadingRows, setIsLoadingRows] = useState(false);

  // Export action state
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccessMsg, setExportSuccessMsg] = useState<string | null>(null);

  // Confirmation Modal
  const [confirmationModal, setConfirmationModal] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    description: '',
    onConfirm: () => {},
  });

  const loadSpreadsheets = async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const files = await listGoogleSpreadsheets(token);
      setSpreadsheets(files);
    } catch (err: any) {
      console.error('Failed to load spreadsheets:', err);
      setError(err.message || 'فشل في تحميل جداول Google Sheets');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadSpreadsheets();
    }
  }, [token]);

  // Inspect a spreadsheet
  const handleInspectSpreadsheet = async (item: SpreadsheetFileItem) => {
    if (!token) return;
    setIsLoadingRows(true);
    try {
      const meta = await getSpreadsheetDetails(token, item.id);
      setSelectedSheetMeta(meta);

      const firstTab = meta.sheets?.[0]?.properties?.title || 'Sheet1';
      setSelectedSheetTab(firstTab);

      const values = await readSpreadsheetValues(token, item.id, `${firstTab}!A1:Z50`);
      setSheetRows(values);
    } catch (err: any) {
      console.error('Inspect spreadsheet error:', err);
      alert(`تعذر جلب محتويات الجدول: ${err.message}`);
    } finally {
      setIsLoadingRows(false);
    }
  };

  // Switch tab in inspected sheet
  const handleSwitchTab = async (tabName: string) => {
    if (!token || !selectedSheetMeta) return;
    setSelectedSheetTab(tabName);
    setIsLoadingRows(true);
    try {
      const values = await readSpreadsheetValues(
        token,
        selectedSheetMeta.spreadsheetId,
        `${tabName}!A1:Z50`
      );
      setSheetRows(values);
    } catch (err: any) {
      console.error('Tab switch error:', err);
    } finally {
      setIsLoadingRows(false);
    }
  };

  // Export Servers to Sheets with confirmation
  const handleExportServers = () => {
    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد تصدير الخوادم إلى Google Sheets',
      description: `سيتم إنشاء جدول Google Sheets جديد في حسابك وتصدير بيانات ${servers.length} خادم بجميع المؤشرات اللحظية (CPU، الذاكرة، القرص، زمن التشغيل). هل تود المتابعة؟`,
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        setIsExporting(true);
        setExportSuccessMsg(null);
        try {
          const res = await exportServerInventoryToNewSheet(token!, servers);
          setExportSuccessMsg(`تم بنجاح تصدير قائمة الخوادم إلى جدول جديد!`);
          await loadSpreadsheets();
          if (res.spreadsheetUrl) {
            window.open(res.spreadsheetUrl, '_blank');
          }
        } catch (err: any) {
          alert(`فشل في التصدير: ${err.message}`);
        } finally {
          setIsExporting(false);
        }
      },
    });
  };

  // Export Incidents to Sheets with confirmation
  const handleExportIncidents = () => {
    setConfirmationModal({
      isOpen: true,
      title: 'تأكيد تصدير سجل الأخطاء إلى Google Sheets',
      description: `سيتم إنشاء جدول Google Sheets جديد وتصدير ${incidents.length} حادثة مسجلة في النظام. هل تود المتابعة؟`,
      onConfirm: async () => {
        setConfirmationModal((prev) => ({ ...prev, isOpen: false }));
        setIsExporting(true);
        setExportSuccessMsg(null);
        try {
          const res = await exportIncidentsToNewSheet(token!, incidents);
          setExportSuccessMsg(`تم تصدير سجل الحوادث بنجاح!`);
          await loadSpreadsheets();
          if (res.spreadsheetUrl) {
            window.open(res.spreadsheetUrl, '_blank');
          }
        } catch (err: any) {
          alert(`فشل في التصدير: ${err.message}`);
        } finally {
          setIsExporting(false);
        }
      },
    });
  };

  if (!user || !token) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center max-w-xl mx-auto my-8 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4">
          <FileSpreadsheet className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">ربط Google Sheets</h3>
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          قم بتسجيل الدخول بحساب Google لتصدير تقارير الخوادم وسجلات الأعطال وعمليات النشر مباشرة إلى جداول Google Sheets السحابية، واستعراضها وتحليلها لحظياً.
        </p>

        <button
          onClick={async () => {
            try {
              const res = await googleSignIn();
              if (res) onAuthSuccess(res.user, res.accessToken);
            } catch (e: any) {
              alert('فشل في تسجيل الدخول: ' + e.message);
            }
          }}
          className="px-6 py-3 bg-white text-slate-900 hover:bg-slate-100 rounded-xl font-bold text-sm shadow-lg transition-all inline-flex items-center gap-2"
        >
          <span>تسجيل الدخول باستخدام Google</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              جداول بيانات Google Sheets
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-medium">
                Google Sheets v4 API
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              تصدير قوائم الخوادم، سجلات الأعطال، وتتبع التقارير الهندسية في جداول سحابية حية
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={loadSpreadsheets}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="تحديث قائمة الجداول"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleExportServers}
            disabled={isExporting}
            className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/30 transition-all"
          >
            {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ServerIcon className="w-4 h-4" />}
            <span>تصدير الخوادم إلى Sheets</span>
          </button>

          <button
            onClick={handleExportIncidents}
            disabled={isExporting}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl font-bold text-xs flex items-center gap-2 transition-all"
          >
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <span>تصدير الحوادث إلى Sheets</span>
          </button>
        </div>
      </div>

      {exportSuccessMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {exportSuccessMsg}
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Main Content: Left Spreadsheets List + Right Sheet Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Files List */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center justify-between pb-1">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <Table className="w-4 h-4 text-emerald-400" />
              الجداول المتوفرة ({spreadsheets.length})
            </h4>
          </div>

          {isLoading ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-400 mx-auto mb-2" />
              <p className="text-sm text-slate-400">جاري قراءة الجداول من Google Drive...</p>
            </div>
          ) : spreadsheets.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center space-y-3">
              <FileSpreadsheet className="w-10 h-10 text-slate-600 mx-auto stroke-[1.2]" />
              <p className="text-sm font-bold text-white">لا توجد جداول بيانات</p>
              <p className="text-xs text-slate-500">
                انقر على "تصدير الخوادم إلى Sheets" لإنشاء أول جدول بيانات سحابي.
              </p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[580px] overflow-y-auto">
              {spreadsheets.map((item) => (
                <div
                  key={item.id}
                  className={`p-3.5 rounded-xl border transition-all flex items-center justify-between gap-3 ${
                    selectedSheetMeta?.spreadsheetId === item.id
                      ? 'bg-emerald-950/30 border-emerald-500/50 shadow'
                      : 'bg-slate-900 hover:bg-slate-800/80 border-slate-800'
                  }`}
                >
                  <div
                    className="flex items-center gap-2.5 cursor-pointer min-w-0"
                    onClick={() => handleInspectSpreadsheet(item)}
                  >
                    <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                      <FileSpreadsheet className="w-4 h-4" />
                    </div>
                    <div className="truncate">
                      <h5 className="text-xs font-bold text-white hover:text-emerald-400 truncate">
                        {item.name}
                      </h5>
                      <p className="text-[10px] text-slate-500 font-mono">
                        {item.modifiedTime ? new Date(item.modifiedTime).toLocaleDateString('ar-EG') : ''}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => handleInspectSpreadsheet(item)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                      title="عرض البيانات"
                    >
                      <Eye className="w-3.5 h-3.5 text-emerald-400" />
                    </button>

                    {item.webViewLink && (
                      <a
                        href={item.webViewLink}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                        title="فتح في Google Sheets"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Spreadsheet Table Viewer */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
          <div className="border-b border-slate-800 pb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <Table className="w-4 h-4 text-emerald-400" />
                {selectedSheetMeta?.properties?.title || 'معاينة جدول البيانات'}
              </h4>
              {selectedSheetMeta?.spreadsheetUrl && (
                <a
                  href={selectedSheetMeta.spreadsheetUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1 mt-0.5"
                >
                  <ExternalLink className="w-3 h-3" />
                  فتح في نافذة مستقلة
                </a>
              )}
            </div>

            {/* Sheets Tabs Selector */}
            {selectedSheetMeta?.sheets && selectedSheetMeta.sheets.length > 0 && (
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                {selectedSheetMeta.sheets.map((s) => {
                  const title = s.properties.title;
                  return (
                    <button
                      key={s.properties.sheetId}
                      onClick={() => handleSwitchTab(title)}
                      className={`px-2.5 py-1 rounded font-medium transition-colors ${
                        selectedSheetTab === title
                          ? 'bg-emerald-600 text-white'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {title}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {isLoadingRows ? (
            <div className="py-20 text-center text-slate-400 space-y-2">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-emerald-400" />
              <p className="text-xs">جاري جلب صفوف وقيم الجدول من Google Sheets...</p>
            </div>
          ) : selectedSheetMeta && sheetRows.length > 0 ? (
            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-right text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-950/80 text-slate-300 border-b border-slate-800 sticky top-0">
                    <th className="p-2.5 font-mono text-[11px] text-slate-500 w-8">#</th>
                    {sheetRows[0]?.map((col: any, idx: number) => (
                      <th key={idx} className="p-2.5 font-bold whitespace-nowrap">
                        {String(col)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                  {sheetRows.slice(1).map((row: any[], rIdx: number) => (
                    <tr key={rIdx} className="hover:bg-slate-800/40 text-slate-300">
                      <td className="p-2.5 text-slate-500 font-mono text-[10px]">{rIdx + 1}</td>
                      {row.map((cell: any, cIdx: number) => (
                        <td key={cIdx} className="p-2.5 whitespace-nowrap">
                          {String(cell ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : selectedSheetMeta ? (
            <div className="py-16 text-center text-slate-500 text-xs">
              هذا الجدول فارغ حالياً أو لا يحتوي على صفوف في النطاق المحدد.
            </div>
          ) : (
            <div className="py-20 text-center text-slate-500 text-xs space-y-2">
              <FileSpreadsheet className="w-10 h-10 mx-auto text-slate-700 stroke-[1.2]" />
              <p>اختر جدولاً من القائمة الجانبية لمعاينة خلاياه وبياناته اللحظية.</p>
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmationModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">{confirmationModal.title}</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {confirmationModal.description}
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setConfirmationModal((prev) => ({ ...prev, isOpen: false }))}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition-colors"
              >
                إلغاء
              </button>
              <button
                onClick={confirmationModal.onConfirm}
                className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg shadow-emerald-600/30 transition-all flex items-center gap-1.5"
              >
                <Check className="w-4 h-4" />
                تأكيد التصدير
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
