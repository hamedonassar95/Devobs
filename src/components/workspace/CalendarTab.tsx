import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import {
  Calendar as CalendarIcon,
  Plus,
  RefreshCw,
  Video,
  Clock,
  MapPin,
  Users,
  Trash2,
  ExternalLink,
  ShieldAlert,
  Wrench,
  AlertTriangle,
  CheckCircle2,
  CalendarDays,
  Search,
  Filter,
} from 'lucide-react';
import { Server, Incident } from '../../types/serverDashboard';
import {
  GoogleCalendarItem,
  GoogleCalendarListEntry,
  listUserCalendars,
  listCalendarEvents,
  createCalendarEvent,
  deleteCalendarEvent,
  scheduleIncidentWarRoom,
  scheduleServerMaintenanceWindow,
} from '../../services/googleCalendarService';
import { googleSignIn } from '../../services/googleAuth';

interface CalendarTabProps {
  user: User | null;
  token: string | null;
  servers: Server[];
  incidents: Incident[];
  onAuthSuccess?: (user: User, token: string) => void;
}

export const CalendarTab: React.FC<CalendarTabProps> = ({
  user,
  token,
  servers,
  incidents,
  onAuthSuccess,
}) => {
  const [calendars, setCalendars] = useState<GoogleCalendarListEntry[]>([]);
  const [selectedCalendarId, setSelectedCalendarId] = useState<string>('primary');
  const [events, setEvents] = useState<GoogleCalendarItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterType, setFilterType] = useState<'all' | 'today' | 'upcoming'>('all');

  // Modals state
  const [isCustomEventModalOpen, setIsCustomEventModalOpen] = useState(false);
  const [isWarRoomModalOpen, setIsWarRoomModalOpen] = useState(false);
  const [isMaintenanceModalOpen, setIsMaintenanceModalOpen] = useState(false);

  // Mandatory Confirmation Dialog State
  const [confirmModalConfig, setConfirmModalConfig] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    details?: string[];
    confirmButtonText: string;
    confirmButtonColor?: 'rose' | 'indigo' | 'emerald';
    onConfirm: () => Promise<void>;
  }>({
    isOpen: false,
    title: '',
    description: '',
    confirmButtonText: 'تأكيد',
    onConfirm: async () => {},
  });

  // Custom Event Form State
  const [customSummary, setCustomSummary] = useState('');
  const [customDescription, setCustomDescription] = useState('');
  const [customLocation, setCustomLocation] = useState('');
  const [customStartDate, setCustomStartDate] = useState(() => {
    const d = new Date();
    d.setMinutes(d.getMinutes() + 30);
    return d.toISOString().slice(0, 16);
  });
  const [customEndDate, setCustomEndDate] = useState(() => {
    const d = new Date();
    d.setMinutes(d.getMinutes() + 90);
    return d.toISOString().slice(0, 16);
  });
  const [customAttendees, setCustomAttendees] = useState('');
  const [customWithMeet, setCustomWithMeet] = useState(true);

  // War Room Form State
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>(incidents[0]?.id || '');
  const [warRoomAttendees, setWarRoomAttendees] = useState('');

  // Maintenance Window Form State
  const [selectedServerId, setSelectedServerId] = useState<string>(servers[0]?.id || '');
  const [maintenanceStartDate, setMaintenanceStartDate] = useState(() => {
    const d = new Date();
    d.setHours(d.getHours() + 4);
    return d.toISOString().slice(0, 16);
  });
  const [maintenanceDuration, setMaintenanceDuration] = useState<number>(2);
  const [maintenanceNotes, setMaintenanceNotes] = useState('');
  const [maintenanceAttendees, setMaintenanceAttendees] = useState('');

  // Load calendars and events
  const loadData = async (currentToken: string, calId = selectedCalendarId) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [calList, eventList] = await Promise.all([
        listUserCalendars(currentToken).catch(() => []),
        listCalendarEvents(currentToken, calId).catch(() => []),
      ]);
      setCalendars(calList);
      setEvents(eventList);
    } catch (err: any) {
      console.error('Error loading calendar data:', err);
      setErrorMessage(err.message || 'حدث خطأ أثناء تحميل بيانات Google Calendar.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadData(token, selectedCalendarId);
    }
  }, [token, selectedCalendarId]);

  const handleSignIn = async () => {
    setIsLoading(true);
    try {
      const result = await googleSignIn();
      if (result && onAuthSuccess) {
        onAuthSuccess(result.user, result.accessToken);
        loadData(result.accessToken, 'primary');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'فشل تسجيل الدخول بـ Google.');
    } finally {
      setIsLoading(false);
    }
  };

  // User Confirmation Handlers for Mutating Operations
  const requestDeleteEvent = (event: GoogleCalendarItem) => {
    setConfirmModalConfig({
      isOpen: true,
      title: 'حذف حدث من تقويم Google',
      description: 'هل أنت متأكد من رغبتك في حذف هذا الحدث نهائياً من تقويمك؟ لن تتمكن من التراجع عن هذه العملية.',
      details: [
        `عنوان الحدث: ${event.summary}`,
        `الموعد: ${event.start.dateTime ? new Date(event.start.dateTime).toLocaleString('ar-SA') : event.start.date || 'غير محدد'}`,
        event.attendees ? `عدد المدعوين: ${event.attendees.length}` : '',
      ].filter(Boolean),
      confirmButtonText: 'نعم، احذف الحدث نهائياً',
      confirmButtonColor: 'rose',
      onConfirm: async () => {
        if (!token) return;
        try {
          await deleteCalendarEvent(token, selectedCalendarId, event.id);
          setEvents((prev) => prev.filter((e) => e.id !== event.id));
          setSuccessMessage(`تم حذف الحدث "${event.summary}" بنجاح.`);
        } catch (err: any) {
          setErrorMessage(err.message || 'فشل حذف الحدث.');
        }
      },
    });
  };

  const handleCreateCustomEventSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customSummary.trim()) {
      setErrorMessage('يرجى إدخال عنوان للحدث.');
      return;
    }

    const attendeeList = customAttendees
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    setConfirmModalConfig({
      isOpen: true,
      title: 'تأكيد إنشاء حدث في تقويم Google',
      description: 'سيتم إضافة هذا الحدث الجديد إلى تقويمك المختار مع إرسال الدعوات للمشاركين:',
      details: [
        `العنوان: ${customSummary}`,
        `البداية: ${new Date(customStartDate).toLocaleString('ar-SA')}`,
        `النهاية: ${new Date(customEndDate).toLocaleString('ar-SA')}`,
        customLocation ? `المكان: ${customLocation}` : '',
        customWithMeet ? 'مرفق رابط Google Meet تلقائي' : '',
        attendeeList.length > 0 ? `المدعوون (${attendeeList.length}): ${attendeeList.join(', ')}` : '',
      ].filter(Boolean),
      confirmButtonText: 'تأكيد وحفظ في التقويم',
      confirmButtonColor: 'indigo',
      onConfirm: async () => {
        if (!token) return;
        try {
          const created = await createCalendarEvent(token, selectedCalendarId, {
            summary: customSummary,
            description: customDescription,
            location: customLocation,
            startDateTime: new Date(customStartDate).toISOString(),
            endDateTime: new Date(customEndDate).toISOString(),
            attendees: attendeeList,
            withGoogleMeet: customWithMeet,
          });
          setEvents((prev) => [created, ...prev]);
          setIsCustomEventModalOpen(false);
          setCustomSummary('');
          setCustomDescription('');
          setSuccessMessage(`تم إنشاء الحدث "${created.summary}" بنجاح في Google Calendar.`);
        } catch (err: any) {
          setErrorMessage(err.message || 'فشل إنشاء الحدث في التقويم.');
        }
      },
    });
  };

  const handleWarRoomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const inc = incidents.find((i) => i.id === selectedIncidentId);
    if (!inc) {
      setErrorMessage('يرجى تحديد الحادثة التشغيلية المستهدفة.');
      return;
    }
    const srv = servers.find((s) => s.id === inc.serverId);
    const attendeeList = warRoomAttendees
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    setConfirmModalConfig({
      isOpen: true,
      title: 'جدولة اجتماع طوارئ SRE War Room',
      description: 'سيتم إنشاء غرفة عمليات فورية ومزامنتها على Google Calendar مع رابط Google Meet وأجندة تفصيلية للحادثة:',
      details: [
        `الحادثة: ${inc.code} - ${inc.message}`,
        `الخادم: ${srv?.name || inc.serverName}`,
        `الموعد المقترح: بعد 15 دقيقة من الآن (مدة 45 دقيقة)`,
        'مرفق رابط Google Meet لغرفة الطوارئ',
        attendeeList.length > 0 ? `المهندسون المشاركون: ${attendeeList.join(', ')}` : '',
      ].filter(Boolean),
      confirmButtonText: 'اعتماد وجدولة غرفة الطوارئ',
      confirmButtonColor: 'rose',
      onConfirm: async () => {
        if (!token) return;
        try {
          const created = await scheduleIncidentWarRoom(
            token,
            selectedCalendarId,
            inc,
            srv,
            attendeeList
          );
          setEvents((prev) => [created, ...prev]);
          setIsWarRoomModalOpen(false);
          setSuccessMessage(`تمت جدولة غرفة عمليات SRE بنجاح ومشاركتها على تقويم Google.`);
        } catch (err: any) {
          setErrorMessage(err.message || 'فشل جدولة غرفة العمليات.');
        }
      },
    });
  };

  const handleMaintenanceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const srv = servers.find((s) => s.id === selectedServerId);
    if (!srv) {
      setErrorMessage('يرجى تحديد الخادم المراد صيانته.');
      return;
    }
    const attendeeList = maintenanceAttendees
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    setConfirmModalConfig({
      isOpen: true,
      title: 'جدولة نافذة صيانة خادم على Google Calendar',
      description: 'سيتم حجز نافذة صيانة رسمية وإبلاغ المناوبين مع إرفاق تعليمات الصيانة:',
      details: [
        `الخادم المستهدف: ${srv.name} (${srv.ip})`,
        `المنطقة: ${srv.region}`,
        `موعد البدء: ${new Date(maintenanceStartDate).toLocaleString('ar-SA')}`,
        `المدة المجدولة: ${maintenanceDuration} ساعة`,
        attendeeList.length > 0 ? `المهندسون المناوبون: ${attendeeList.join(', ')}` : '',
      ].filter(Boolean),
      confirmButtonText: 'تأكيد وحجز نافذة الصيانة',
      confirmButtonColor: 'indigo',
      onConfirm: async () => {
        if (!token) return;
        try {
          const created = await scheduleServerMaintenanceWindow(
            token,
            selectedCalendarId,
            srv,
            new Date(maintenanceStartDate).toISOString(),
            maintenanceDuration,
            maintenanceNotes,
            attendeeList
          );
          setEvents((prev) => [created, ...prev]);
          setIsMaintenanceModalOpen(false);
          setSuccessMessage(`تم حجز نافذة صيانة الخادم ${srv.name} بنجاح في Google Calendar.`);
        } catch (err: any) {
          setErrorMessage(err.message || 'فشل حجز نافذة الصيانة.');
        }
      },
    });
  };

  // Filter events
  const filteredEvents = events.filter((ev) => {
    const matchesSearch =
      !searchQuery ||
      ev.summary?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.location?.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filterType === 'today') {
      const eventDate = ev.start.dateTime ? new Date(ev.start.dateTime) : ev.start.date ? new Date(ev.start.date) : null;
      if (!eventDate) return true;
      const today = new Date();
      return (
        eventDate.getDate() === today.getDate() &&
        eventDate.getMonth() === today.getMonth() &&
        eventDate.getFullYear() === today.getFullYear()
      );
    }

    if (filterType === 'upcoming') {
      const eventDate = ev.start.dateTime ? new Date(ev.start.dateTime) : ev.start.date ? new Date(ev.start.date) : null;
      if (!eventDate) return true;
      return eventDate.getTime() >= Date.now();
    }

    return true;
  });

  // Not authenticated view
  if (!token) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 sm:p-12 text-center max-w-2xl mx-auto shadow-2xl space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center mx-auto shadow-inner">
          <CalendarIcon className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-bold text-white">ربط Google Calendar بالمنظومة</h3>
          <p className="text-sm text-slate-400 leading-relaxed max-w-md mx-auto">
            قم بتسجيل الدخول بحساب Google للوصول إلى تقويمك، جدولة غرف طوارئ SRE التلقائية، وحجز نوافذ صيانة الخوادم وربطها بروابط Google Meet مباشرة بإذنك.
          </p>
        </div>

        <div className="pt-2 flex justify-center">
          <button
            onClick={handleSignIn}
            disabled={isLoading}
            className="gsi-material-button inline-flex items-center justify-center gap-3 px-6 py-3 rounded-xl bg-white text-slate-800 font-semibold text-sm hover:bg-slate-100 transition-all shadow-md active:scale-95 disabled:opacity-50"
          >
            <div className="gsi-material-button-icon">
              <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" className="w-5 h-5 block">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"></path>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"></path>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"></path>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"></path>
                <path fill="none" d="M0 0h48v48H0z"></path>
              </svg>
            </div>
            <span>{isLoading ? 'جاري الاتصال...' : 'تسجيل الدخول بـ Google'}</span>
          </button>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
            {errorMessage}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Messages */}
      {errorMessage && (
        <div className="p-4 rounded-2xl bg-rose-950/70 border border-rose-800/80 text-rose-300 text-xs flex items-center justify-between gap-3 shadow-lg">
          <span>{errorMessage}</span>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-400 hover:text-rose-200 text-sm font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-4 rounded-2xl bg-emerald-950/70 border border-emerald-800/80 text-emerald-300 text-xs flex items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-400 hover:text-emerald-200 text-sm font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Bar: Selector, Quick Actions, Refresh */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
                <CalendarIcon className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Google Calendar SRE Operations</h3>
                <p className="text-[11px] text-slate-400">جدولة وتنسيق صيانة الأنظمة وغرف طوارئ الحوادث</p>
              </div>
            </div>

            {/* Calendar Selector */}
            {calendars.length > 0 && (
              <select
                value={selectedCalendarId}
                onChange={(e) => setSelectedCalendarId(e.target.value)}
                className="bg-slate-950 text-slate-200 text-xs rounded-xl px-3 py-1.5 border border-slate-800 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                {calendars.map((cal) => (
                  <option key={cal.id} value={cal.id}>
                    {cal.summary} {cal.primary ? '(الرئيسي)' : ''}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsWarRoomModalOpen(true)}
              className="px-3 py-1.5 text-xs font-bold rounded-xl bg-rose-600/20 text-rose-300 hover:bg-rose-600/30 border border-rose-500/40 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>جدولة War Room لحادثة</span>
            </button>

            <button
              onClick={() => setIsMaintenanceModalOpen(true)}
              className="px-3 py-1.5 text-xs font-bold rounded-xl bg-amber-600/20 text-amber-300 hover:bg-amber-600/30 border border-amber-500/40 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Wrench className="w-3.5 h-3.5 text-amber-400" />
              <span>حجز نافذة صيانة</span>
            </button>

            <button
              onClick={() => setIsCustomEventModalOpen(true)}
              className="px-3 py-1.5 text-xs font-bold rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 transition-colors flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>حدث مخصص</span>
            </button>

            <button
              onClick={() => token && loadData(token, selectedCalendarId)}
              disabled={isLoading}
              title="تحديث الأحداث"
              className="p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white border border-slate-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="البحث في مواعيد وأحداث التقويم..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 text-slate-200 text-xs rounded-xl pr-9 pl-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500 transition-colors placeholder:text-slate-500"
            />
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 text-[11px] ml-1 flex items-center gap-1">
              <Filter className="w-3 h-3" /> التصفية:
            </span>
            <button
              onClick={() => setFilterType('all')}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                filterType === 'all'
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              الكل ({events.length})
            </button>
            <button
              onClick={() => setFilterType('today')}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                filterType === 'today'
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              اليوم
            </button>
            <button
              onClick={() => setFilterType('upcoming')}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                filterType === 'upcoming'
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              القادمة فقط
            </button>
          </div>
        </div>
      </div>

      {/* Events Grid */}
      {isLoading && events.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-indigo-400" />
          <p className="text-sm">جاري مزامنة الأحداث من Google Calendar...</p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-4">
          <CalendarDays className="w-10 h-10 mx-auto text-slate-600" />
          <div className="space-y-1">
            <h4 className="text-base font-bold text-slate-300">لا توجد أحداث مجدولة</h4>
            <p className="text-xs text-slate-500">
              {searchQuery ? 'لم نجد أي حدث يطابق عبارة البحث الخاصة بك.' : 'يمكنك جدولة حدث جديد، نافذة صيانة خادم، أو غرفة عمليات طوارئ الآن.'}
            </p>
          </div>
          <button
            onClick={() => setIsCustomEventModalOpen(true)}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors inline-flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>إضافة أول حدث للتقويم</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEvents.map((ev) => {
            const isWarRoom = ev.summary?.includes('War Room');
            const isMaintenance = ev.summary?.includes('نافذة صيانة') || ev.summary?.includes('Maintenance');
            const meetUrl =
              ev.hangoutLink ||
              ev.conferenceData?.entryPoints?.find((ep) => ep.entryPointType === 'video')?.uri;

            const startDate = ev.start.dateTime
              ? new Date(ev.start.dateTime)
              : ev.start.date
              ? new Date(ev.start.date)
              : null;
            const endDate = ev.end.dateTime
              ? new Date(ev.end.dateTime)
              : ev.end.date
              ? new Date(ev.end.date)
              : null;

            return (
              <div
                key={ev.id}
                className={`bg-slate-900 border rounded-2xl p-5 shadow-sm flex flex-col justify-between transition-all hover:border-slate-700 ${
                  isWarRoom
                    ? 'border-rose-500/40 bg-gradient-to-br from-rose-950/20 to-slate-900'
                    : isMaintenance
                    ? 'border-amber-500/40 bg-gradient-to-br from-amber-950/20 to-slate-900'
                    : 'border-slate-800'
                }`}
              >
                <div className="space-y-3">
                  {/* Event Type Chip & Action */}
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide flex items-center gap-1 ${
                        isWarRoom
                          ? 'bg-rose-950 text-rose-400 border border-rose-800'
                          : isMaintenance
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-indigo-950 text-indigo-400 border border-indigo-800'
                      }`}
                    >
                      {isWarRoom && <ShieldAlert className="w-3 h-3" />}
                      {isMaintenance && <Wrench className="w-3 h-3" />}
                      {!isWarRoom && !isMaintenance && <CalendarIcon className="w-3 h-3" />}
                      <span>{isWarRoom ? 'SRE War Room' : isMaintenance ? 'صيانة خادم' : 'حدث تقويم'}</span>
                    </span>

                    <button
                      onClick={() => requestDeleteEvent(ev)}
                      title="حذف الحدث نهائياً"
                      className="p-1 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Summary */}
                  <h4 className="text-sm font-bold text-white line-clamp-2 leading-snug">
                    {ev.summary || 'بدون عنوان'}
                  </h4>

                  {/* Date & Time */}
                  <div className="space-y-1 text-xs text-slate-300">
                    <div className="flex items-center gap-2 text-indigo-400 font-mono text-[11px]">
                      <Clock className="w-3.5 h-3.5 shrink-0" />
                      <span>
                        {startDate ? startDate.toLocaleDateString('ar-SA', { weekday: 'short', month: 'short', day: 'numeric' }) : ''}
                        {' · '}
                        {startDate ? startDate.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' }) : ''}
                        {endDate ? ` - ${endDate.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}` : ''}
                      </span>
                    </div>

                    {ev.location && (
                      <div className="flex items-center gap-2 text-slate-400 text-[11px] truncate">
                        <MapPin className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                        <span className="truncate">{ev.location}</span>
                      </div>
                    )}
                  </div>

                  {/* Description preview */}
                  {ev.description && (
                    <p className="text-xs text-slate-400 line-clamp-3 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80 font-mono text-[11px] leading-relaxed whitespace-pre-line">
                      {ev.description}
                    </p>
                  )}

                  {/* Attendees */}
                  {ev.attendees && ev.attendees.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-400 pt-1">
                      <Users className="w-3 h-3 text-slate-500 shrink-0" />
                      <span>{ev.attendees.length} مشارك(ين)</span>
                      <div className="flex -space-x-1 overflow-hidden mr-1">
                        {ev.attendees.slice(0, 3).map((att, idx) => (
                          <span
                            key={idx}
                            title={att.email}
                            className="inline-block w-4 h-4 rounded-full bg-slate-800 border border-slate-700 text-[8px] text-center font-bold text-slate-300"
                          >
                            {att.email[0].toUpperCase()}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer Buttons: Google Meet + Calendar Link */}
                <div className="pt-4 mt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                  {meetUrl ? (
                    <a
                      href={meetUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 rounded-xl bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 text-xs font-bold transition-colors flex items-center gap-1.5"
                    >
                      <Video className="w-3.5 h-3.5 text-emerald-400" />
                      <span>انضمام بـ Meet</span>
                    </a>
                  ) : (
                    <span className="text-[10px] text-slate-600 font-mono">لا يوجد رابط Meet</span>
                  )}

                  {ev.htmlLink && (
                    <a
                      href={ev.htmlLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                    >
                      <span>عرض في التقويم</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* MODAL 1: Custom Event Creation */}
      {isCustomEventModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <CalendarIcon className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">إنشاء حدث جديد على Google Calendar</h3>
              </div>
              <button
                onClick={() => setIsCustomEventModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateCustomEventSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">عنوان الحدث *</label>
                <input
                  type="text"
                  required
                  value={customSummary}
                  onChange={(e) => setCustomSummary(e.target.value)}
                  placeholder="مثال: مراجعة البنية التحتية الأسبوعية"
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">وقت البدء *</label>
                  <input
                    type="datetime-local"
                    required
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">وقت الانتهاء *</label>
                  <input
                    type="datetime-local"
                    required
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">المكان أو المنصة</label>
                <input
                  type="text"
                  value={customLocation}
                  onChange={(e) => setCustomLocation(e.target.value)}
                  placeholder="مثال: غرفة العمليات الافتراضية / مقر الخوادم"
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">عناوين البريد الإلكتروني للمشاركين (مفصولة بفواصل)</label>
                <input
                  type="text"
                  value={customAttendees}
                  onChange={(e) => setCustomAttendees(e.target.value)}
                  placeholder="devops@company.com, sre@company.com"
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">الوصف والملاحظات</label>
                <textarea
                  rows={3}
                  value={customDescription}
                  onChange={(e) => setCustomDescription(e.target.value)}
                  placeholder="أهداف الاجتماع، الخطوات، أو الروابط المرجعية..."
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="meet-checkbox"
                  checked={customWithMeet}
                  onChange={(e) => setCustomWithMeet(e.target.checked)}
                  className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                />
                <label htmlFor="meet-checkbox" className="text-slate-300 cursor-pointer flex items-center gap-1.5">
                  <Video className="w-3.5 h-3.5 text-emerald-400" />
                  <span>توليد رابط فيديو Google Meet تلقائياً</span>
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCustomEventModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition-colors"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-colors shadow-md shadow-indigo-600/20"
                >
                  متابعة وتأكيد الحدث ←
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: War Room Schedule */}
      {isWarRoomModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-rose-400" />
                <h3 className="text-base font-bold text-white">جدولة اجتماع طوارئ SRE War Room</h3>
              </div>
              <button
                onClick={() => setIsWarRoomModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleWarRoomSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">اختر الحادثة التشغيلية المستهدفة *</label>
                <select
                  value={selectedIncidentId}
                  onChange={(e) => setSelectedIncidentId(e.target.value)}
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                >
                  {incidents.map((inc) => (
                    <option key={inc.id} value={inc.id}>
                      [{inc.code}] {inc.message.slice(0, 50)}... ({inc.serverName})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">المهندسون المشاركون في الاستجابة (إيميلات مفصولة بفواصل)</label>
                <input
                  type="text"
                  value={warRoomAttendees}
                  onChange={(e) => setWarRoomAttendees(e.target.value)}
                  placeholder="incident-commander@devops.com, sre-lead@company.com"
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 text-[11px] text-slate-400">
                <div className="text-slate-200 font-bold flex items-center gap-1.5">
                  <Video className="w-3.5 h-3.5 text-emerald-400" />
                  <span>توليد تلقائي لاجتماع Google Meet</span>
                </div>
                <p>
                  سيتم تعيين الموعد تلقائياً بعد 15 دقيقة مع وضع تفاصيل تتبع الخطأ (Stack Trace) ورابط الحادثة وأجندة معالجة الحوادث في نص الدعوة.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsWarRoomModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition-colors"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold transition-colors shadow-md shadow-rose-600/20"
                >
                  متابعة وتأكيد War Room ←
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Maintenance Window Schedule */}
      {isMaintenanceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Wrench className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-white">حجز نافذة صيانة خادم على Google Calendar</h3>
              </div>
              <button
                onClick={() => setIsMaintenanceModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleMaintenanceSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">الخادم المستهدف بالصيانة *</label>
                <select
                  value={selectedServerId}
                  onChange={(e) => setSelectedServerId(e.target.value)}
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                >
                  {servers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.ip}) - {s.region} - {s.status}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">توقيت بدء نافذة الصيانة *</label>
                  <input
                    type="datetime-local"
                    required
                    value={maintenanceStartDate}
                    onChange={(e) => setMaintenanceStartDate(e.target.value)}
                    className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">مدة الصيانة المقدرة (بالساعات) *</label>
                  <input
                    type="number"
                    min="1"
                    max="24"
                    required
                    value={maintenanceDuration}
                    onChange={(e) => setMaintenanceDuration(parseInt(e.target.value) || 1)}
                    className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">ملاحظات وخطوات الصيانة</label>
                <textarea
                  rows={2}
                  value={maintenanceNotes}
                  onChange={(e) => setMaintenanceNotes(e.target.value)}
                  placeholder="مثال: ترقية توزيعة لينكس، ترحيل قواعد البيانات، وفحص مسارات الشبكة..."
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">دعوة مهندسي الصيانة (إيميلات مفصولة بفواصل)</label>
                <input
                  type="text"
                  value={maintenanceAttendees}
                  onChange={(e) => setMaintenanceAttendees(e.target.value)}
                  placeholder="oncall@company.com, infra@company.com"
                  className="w-full bg-slate-950 text-slate-100 rounded-xl px-3 py-2 border border-slate-800 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsMaintenanceModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition-colors"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold transition-colors shadow-md shadow-amber-600/20"
                >
                  متابعة وتأكيد الحجز ←
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MANDATORY CONFIRMATION DIALOG FOR DESTRUCTIVE/MUTATING WORKSPACE ACTIONS */}
      {confirmModalConfig.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center gap-3">
              <div
                className={`w-10 h-10 rounded-2xl flex items-center justify-center ${
                  confirmModalConfig.confirmButtonColor === 'rose'
                    ? 'bg-rose-600/20 text-rose-400 border border-rose-500/30'
                    : 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                }`}
              >
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">{confirmModalConfig.title}</h3>
                <p className="text-xs text-slate-400">تأكيد الإجراء على بيانات Google Calendar</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {confirmModalConfig.description}
            </p>

            {confirmModalConfig.details && confirmModalConfig.details.length > 0 && (
              <div className="p-3.5 bg-slate-950 rounded-2xl border border-slate-800/80 space-y-1.5 text-xs text-slate-300">
                {confirmModalConfig.details.map((detail, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-indigo-400 font-bold">•</span>
                    <span className="font-mono text-[11px]">{detail}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setConfirmModalConfig((prev) => ({ ...prev, isOpen: false }))}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                إلغاء الأمر
              </button>
              <button
                type="button"
                onClick={async () => {
                  const runAction = confirmModalConfig.onConfirm;
                  setConfirmModalConfig((prev) => ({ ...prev, isOpen: false }));
                  await runAction();
                }}
                className={`px-5 py-2 rounded-xl text-white text-xs font-bold transition-all shadow-lg ${
                  confirmModalConfig.confirmButtonColor === 'rose'
                    ? 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/30'
                    : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/30'
                }`}
              >
                {confirmModalConfig.confirmButtonText}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
