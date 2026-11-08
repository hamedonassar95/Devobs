import React, { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import { Server, Incident, Deployment, IncidentSeverity } from './types/serverDashboard';
import {
  INITIAL_SERVERS,
  INITIAL_INCIDENTS,
  INITIAL_DEPLOYMENTS,
  INITIAL_METRICS_24H,
} from './data/mockServerData';
import { DashboardHeader, DashboardTab } from './components/dashboard/DashboardHeader';
import { ServerOverviewCards } from './components/dashboard/ServerOverviewCards';
import { InteractiveMetricsChart } from './components/dashboard/InteractiveMetricsChart';
import { ServerGrid } from './components/dashboard/ServerGrid';
import { ErrorLogViewer } from './components/dashboard/ErrorLogViewer';
import { DeploymentTracker } from './components/dashboard/DeploymentTracker';
import { GoogleDriveTab } from './components/drive/GoogleDriveTab';
import { GmailTab } from './components/workspace/GmailTab';
import { ChatTab } from './components/workspace/ChatTab';
import { AiIncidentModal } from './components/dashboard/AiIncidentModal';
import { AiAuditModal } from './components/dashboard/AiAuditModal';
import { exportServersToCSV, exportIncidentsToCSV, exportDeploymentsToCSV } from './utils/dashboardUtils';
import { initAuth, googleSignIn } from './services/googleAuth';
import {
  subscribeToServers,
  saveServerToFirestore,
  deleteServerFromFirestore,
  subscribeToIncidents,
  saveIncidentToFirestore,
  subscribeToDeployments,
  saveDeploymentToFirestore,
  seedFirestoreIfEmpty,
} from './services/firebaseFirestore';
import { ServerRoom3D } from './components/three/ServerRoom3D';
import { CyberDefenseGame } from './components/game/CyberDefenseGame';
import { GeminiChatbot } from './components/chat/GeminiChatbot';
import { AiMediaStudio } from './components/studio/AiMediaStudio';
import { FormsTab } from './components/workspace/FormsTab';
import { SheetsTab } from './components/workspace/SheetsTab';
import { DocsTab } from './components/workspace/DocsTab';
import { SlidesTab } from './components/workspace/SlidesTab';
import { TasksTab } from './components/workspace/TasksTab';
import { CalendarTab } from './components/workspace/CalendarTab';
import { KeepTab } from './components/workspace/KeepTab';
import { GitHubTab } from './components/github/GitHubTab';
import {
  Server as ServerIcon,
  ShieldAlert,
  Rocket,
  Download,
  Sparkles,
  Cloud,
  Mail,
  MessageSquare,
  Database,
  CheckCircle2,
  Box,
  Bot,
  Video,
  FileText,
  FileSpreadsheet,
  Presentation,
  CheckSquare,
  Gamepad2,
  BookOpen,
  Calendar as CalendarIcon,
  FolderGit2,
} from 'lucide-react';

export default function App() {
  // Theme state (Dark mode default for High-End Dark Tech)
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme');
      return stored ? stored === 'dark' : true;
    }
    return true;
  });

  // Tab navigation
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');

  // Google Auth State
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // Cloud Database Sync Status
  const [isCloudDbReady, setIsCloudDbReady] = useState(false);

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

  // Live Toast Notifications
  const [toasts, setToasts] = useState<
    { id: string; message: string; type: 'success' | 'info' | 'warning' | 'error' }[]
  >([]);

  const addToast = (message: string, type: 'success' | 'info' | 'warning' | 'error' = 'info') => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  // Initialize Firebase Auth listener
  useEffect(() => {
    const unsubscribe = initAuth(
      (currentUser, currentToken) => {
        setUser(currentUser);
        setToken(currentToken);
      },
      () => {
        setUser(null);
        setToken(null);
      }
    );
    return () => unsubscribe();
  }, []);

  // Initialize Firestore Real-time Subscriptions & Seeding
  useEffect(() => {
    seedFirestoreIfEmpty(INITIAL_SERVERS, INITIAL_INCIDENTS, INITIAL_DEPLOYMENTS)
      .then(() => setIsCloudDbReady(true))
      .catch(() => setIsCloudDbReady(true));

    const unsubServers = subscribeToServers((remoteServers) => {
      setServers(remoteServers);
    });

    const unsubIncidents = subscribeToIncidents((remoteIncidents) => {
      setIncidents(remoteIncidents);
    });

    const unsubDeployments = subscribeToDeployments((remoteDeployments) => {
      setDeployments(remoteDeployments);
    });

    return () => {
      unsubServers();
      unsubIncidents();
      unsubDeployments();
    };
  }, []);

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

  // Handle Google Sign in from header
  const handleSignInClick = async () => {
    try {
      const result = await googleSignIn();
      if (result) {
        setUser(result.user);
        setToken(result.accessToken);
      }
    } catch (err) {
      console.error('Sign in error:', err);
    }
  };

  // Server Actions
  const handleRestartServer = (serverId: string) => {
    let updatedServer: Server | null = null;
    setServers((prev) =>
      prev.map((s) => {
        if (s.id === serverId) {
          updatedServer = {
            ...s,
            status: 'healthy',
            cpu: Math.floor(Math.random() * 25) + 20,
            memory: Math.floor(Math.random() * 30) + 40,
            lastPing: 'الآن',
          };
          return updatedServer;
        }
        return s;
      })
    );

    if (updatedServer) {
      saveServerToFirestore(updatedServer);
    }

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
      saveIncidentToFirestore(newInc);
      addToast(`⚡ تمت إعادة تشغيل الخادم ${targetServer.name} واستعادة المؤشرات الطبيعية`, 'success');
    }
  };

  const handleToggleMaintenance = (serverId: string) => {
    let updatedServer: Server | null = null;
    setServers((prev) =>
      prev.map((s) => {
        if (s.id === serverId) {
          const nextStatus = s.status === 'maintenance' ? 'healthy' : 'maintenance';
          updatedServer = { ...s, status: nextStatus };
          addToast(`🛡️ تم تحويل الخادم ${s.name} إلى وضع [${nextStatus === 'maintenance' ? 'الصيانة' : 'العمل الطبيعي'}]`, 'info');
          return updatedServer;
        }
        return s;
      })
    );

    if (updatedServer) {
      saveServerToFirestore(updatedServer);
    }
  };

  const handleDeleteServer = (serverId: string) => {
    const srv = servers.find((s) => s.id === serverId);
    setServers((prev) => prev.filter((s) => s.id !== serverId));
    deleteServerFromFirestore(serverId);
    if (srv) addToast(`🗑️ تم حذف الخادم ${srv.name} من قاعدة البيانات السحابية`, 'info');
  };

  const handleAddServer = (newServerData: Omit<Server, 'id' | 'uptimeDays' | 'lastPing'>) => {
    const newServer: Server = {
      ...newServerData,
      id: `srv-${Date.now().toString().slice(-4)}`,
      uptimeDays: 0,
      lastPing: 'منذ ثانية',
    };
    setServers((prev) => [newServer, ...prev]);
    saveServerToFirestore(newServer);
    addToast(`🚀 تم تسجيل وتدشين الخادم الجديد [${newServer.name}] بنجاح`, 'success');
  };

  // Incident Actions
  const handleResolveIncident = (incidentId: string) => {
    let resolvedItem: Incident | null = null;
    setIncidents((prev) =>
      prev.map((inc) => {
        if (inc.id === incidentId) {
          resolvedItem = {
            ...inc,
            resolved: true,
            resolvedAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
          };
          addToast(`✅ تم حل وإغلاق الحادثة [${inc.code}] بنجاح`, 'success');
          return resolvedItem;
        }
        return inc;
      })
    );

    if (resolvedItem) {
      saveIncidentToFirestore(resolvedItem);
    }
  };

  const handleSimulateIncident = (scenario?: { code: string; severity: IncidentSeverity; message: string; stack: string; serverId?: string }) => {
    if (servers.length === 0) return;
    const pickedServer = scenario?.serverId
      ? servers.find((s) => s.id === scenario.serverId) || servers[0]
      : servers[Math.floor(Math.random() * servers.length)];

    const mockErrors = [
      {
        code: 'ERR_HIGH_CPU_SPIKE',
        severity: 'warning' as const,
        message: `ارتفاع حاد في استهلاك المعالج تجاوز 92% على ${pickedServer.name} بسبب معالجة دفعات متزامنة.`,
        stack: `PID 14088 node [worker-thread] consuming 94% CPU.\nGarbage collector frequency tripled in the last 60 seconds.`,
      },
      {
        code: 'ERR_HTTP_502_BAD_GATEWAY',
        severity: 'critical' as const,
        message: `توقف مفاجئ في استجابة خدمة البروكسي الداخلية على الخادم ${pickedServer.name}.`,
        stack: `connect() failed (111: Connection refused) while connecting to upstream.\nworker process 3108 exited on signal 11 (SIGSEGV).`,
      },
      {
        code: 'WARN_DISK_SPACE_THRESHOLD',
        severity: 'warning' as const,
        message: `المساحة المتبقية على قرص /var/log أقل من 12% على ${pickedServer.name}.`,
        stack: `Filesystem /dev/nvme0n1p1 mounted on /var/log capacity at 88.4%.\nLogrotate schedule queue pending.`,
      },
    ];

    const picked = scenario || mockErrors[Math.floor(Math.random() * mockErrors.length)];

    const newIncident: Incident = {
      id: `inc-${Date.now()}`,
      serverId: pickedServer.id,
      serverName: pickedServer.name,
      severity: picked.severity,
      code: picked.code,
      message: picked.message,
      stackTrace: picked.stack,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      resolved: false,
    };

    setIncidents((prev) => [newIncident, ...prev]);
    saveIncidentToFirestore(newIncident);

    // Update server status accordingly
    let affectedServer: Server | null = null;
    setServers((prev) =>
      prev.map((s) => {
        if (s.id === pickedServer.id) {
          affectedServer = {
            ...s,
            status: picked.severity === 'critical' ? 'critical' : 'warning',
            cpu: picked.severity === 'critical' ? 96 : 86,
          };
          return affectedServer;
        }
        return s;
      })
    );

    if (affectedServer) {
      saveServerToFirestore(affectedServer);
    }

    addToast(`⚠️ [Chaos Test]: تم حقن الحادثة [${picked.code}] على الخادم ${pickedServer.name}`, 'warning');
  };

  // Automated Hotfix CI/CD Deployment
  const handleDeployHotfix = (serviceName: string, changeLog: string) => {
    const newDep: Deployment = {
      id: `dep-${Date.now().toString().slice(-4)}`,
      version: `v2.5.${Math.floor(Math.random() * 8) + 1}-hotfix`,
      commitHash: Math.random().toString(16).substring(2, 9),
      serviceName,
      branch: 'hotfix/sre-auto-remediation',
      author: 'SRE-Copilot',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      status: 'successful',
      durationSeconds: 16,
      changeLog,
      targetServers: servers.filter((s) => s.name === serviceName).map((s) => s.id),
    };
    setDeployments((prev) => [newDep, ...prev]);
    saveDeploymentToFirestore(newDep);
    addToast(`🚀 تم نشر التصحيح البرمجي (${newDep.version}) بنجاح عبر مسار CI/CD!`, 'success');
  };

  // Deployment Actions
  const handleRedeploy = (deploymentId: string) => {
    let deployingItem: Deployment | null = null;
    setDeployments((prev) =>
      prev.map((d) => {
        if (d.id === deploymentId) {
          deployingItem = {
            ...d,
            status: 'in_progress',
          };
          return deployingItem;
        }
        return d;
      })
    );

    if (deployingItem) {
      saveDeploymentToFirestore(deployingItem);
    }

    setTimeout(() => {
      let completedItem: Deployment | null = null;
      setDeployments((prev) =>
        prev.map((d) => {
          if (d.id === deploymentId) {
            completedItem = {
              ...d,
              status: 'successful',
              timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
            };
            return completedItem;
          }
          return d;
        })
      );
      if (completedItem) {
        saveDeploymentToFirestore(completedItem);
      }
    }, 2000);
  };

  const handleRollback = (deploymentId: string) => {
    let rolledItem: Deployment | null = null;
    setDeployments((prev) =>
      prev.map((d) => {
        if (d.id === deploymentId) {
          rolledItem = {
            ...d,
            status: 'rolled_back',
            changeLog: `[تراجع تلقائي] تم التراجع عن هذا الإصدار للنسخة السابقة المستقرة.`,
          };
          return rolledItem;
        }
        return d;
      })
    );

    if (rolledItem) {
      saveDeploymentToFirestore(rolledItem);
    }
  };

  const handleAddNewDeployment = (newDepData: Omit<Deployment, 'id' | 'timestamp'>) => {
    const newDep: Deployment = {
      ...newDepData,
      id: `dep-${Date.now().toString().slice(-4)}`,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
    };
    setDeployments((prev) => [newDep, ...prev]);
    saveDeploymentToFirestore(newDep);
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
      INITIAL_SERVERS.forEach((s) => saveServerToFirestore(s));
      INITIAL_INCIDENTS.forEach((i) => saveIncidentToFirestore(i));
      INITIAL_DEPLOYMENTS.forEach((d) => saveDeploymentToFirestore(d));
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
        user={user}
        onSignInClick={handleSignInClick}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8">
        {/* Top Context Subheader */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-indigo-400 mb-1">
              <span>مركز التحكم الموحد</span>
              <span aria-hidden="true">·</span>
              <span>DevOps & Infrastructure Console</span>
              <span aria-hidden="true">·</span>
              <span className="text-emerald-400 flex items-center gap-1 font-mono">
                <Database className="w-3 h-3" />
                قاعدة بيانات سحابية متصلة (my-apps-hamedo)
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-white">
              {activeTab === 'overview' && 'لوحة قيادة الخوادم والأنظمة'}
              {activeTab === 'github' && 'مركز تطوير وعمليات GitHub (GitHub DevOps & CI/CD Hub)'}
              {activeTab === '3d_room' && 'غرفة الخوادم التفاعلية ثلاثية الأبعاد (Three.js)'}
              {activeTab === 'cyber_game' && 'لعبة الدفاع السيبراني التفاعلية ثلاثية الأبعاد (Cyber Shield 3D)'}
              {activeTab === 'gemini_chat' && 'المساعد الذكي للأنظمة والعمليات (Gemini Copilot)'}
              {activeTab === 'media_studio' && 'استوديو وسائط الذكاء الاصطناعي (فيديو، صور، موسيقى)'}
              {activeTab === 'servers' && 'إدارة وحالة كل خادم'}
              {activeTab === 'incidents' && 'سجل الأخطاء والحوادث التشغيلية'}
              {activeTab === 'deployments' && 'سجل آخر عمليات النشر البرمجي'}
              {activeTab === 'drive' && 'الأرشيف السحابي والنسخ الاحتياطي (Google Drive)'}
              {activeTab === 'gmail' && 'تنبيهات البريد الإلكتروني (Gmail)'}
              {activeTab === 'chat' && 'قنوات وغرف العمليات (Google Chat)'}
              {activeTab === 'forms' && 'استبيانات ونماذج العمليات (Google Forms)'}
              {activeTab === 'sheets' && 'جداول وتحليلات البيانات (Google Sheets)'}
              {activeTab === 'slides' && 'عروض الشرائح وتقارير SRE التقديمية (Google Slides)'}
              {activeTab === 'tasks' && 'إدارة مهام وتشغيل النظم (Google Tasks)'}
              {activeTab === 'calendar' && 'إدارة المواعيد وصيانة الأنظمة وغرف الطوارئ (Google Calendar)'}
              {activeTab === 'docs' && 'وثائق وتقارير العمليات (Google Docs)'}
              {activeTab === 'keep' && 'سجلات وكتيبات الطوارئ (Runbooks & Notes)'}
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setActiveTab('github')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600/30 text-indigo-300 hover:bg-indigo-600 hover:text-white border border-indigo-500/50 transition-all flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
            >
              <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
              <span>GitHub Hub</span>
            </button>

            <button
              onClick={() => setActiveTab('3d_room')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-cyan-600/20 text-cyan-300 hover:bg-cyan-600/30 border border-cyan-500/40 transition-colors flex items-center gap-1.5"
            >
              <Box className="w-3.5 h-3.5 text-cyan-400" />
              <span>غرفة 3D</span>
            </button>

            <button
              onClick={() => setActiveTab('cyber_game')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 border border-cyan-400/50 transition-colors flex items-center gap-1.5 shadow-md shadow-cyan-500/10"
            >
              <Gamepad2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>لعبة الدفاع 3D</span>
            </button>

            <button
              onClick={() => setActiveTab('gemini_chat')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/40 transition-colors flex items-center gap-1.5"
            >
              <Bot className="w-3.5 h-3.5 text-indigo-400" />
              <span>مساعد Gemini</span>
            </button>

            <button
              onClick={() => setActiveTab('media_studio')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-purple-600/20 text-purple-300 hover:bg-purple-600/30 border border-purple-500/40 transition-colors flex items-center gap-1.5"
            >
              <Video className="w-3.5 h-3.5 text-purple-400" />
              <span>استوديو AI</span>
            </button>

            <button
              onClick={() => setActiveTab('docs')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-blue-600/20 text-blue-300 hover:bg-blue-600/30 border border-blue-500/40 transition-colors flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>Docs</span>
            </button>

            <button
              onClick={() => setActiveTab('sheets')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/40 transition-colors flex items-center gap-1.5"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              <span>Sheets</span>
            </button>

            <button
              onClick={() => setActiveTab('slides')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-amber-600/20 text-amber-300 hover:bg-amber-600/30 border border-amber-500/40 transition-colors flex items-center gap-1.5"
            >
              <Presentation className="w-3.5 h-3.5 text-amber-400" />
              <span>Slides</span>
            </button>

            <button
              onClick={() => setActiveTab('tasks')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-sky-600/20 text-sky-300 hover:bg-sky-600/30 border border-sky-500/40 transition-colors flex items-center gap-1.5"
            >
              <CheckSquare className="w-3.5 h-3.5 text-sky-400" />
              <span>Tasks</span>
            </button>

            <button
              onClick={() => setActiveTab('calendar')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/40 transition-colors flex items-center gap-1.5"
            >
              <CalendarIcon className="w-3.5 h-3.5 text-indigo-400" />
              <span>Calendar</span>
            </button>

            <button
              onClick={() => setActiveTab('forms')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-purple-600/20 text-purple-300 hover:bg-purple-600/30 border border-purple-500/40 transition-colors flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5 text-purple-400" />
              <span>Forms</span>
            </button>

            <button
              onClick={() => setActiveTab('keep')}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-amber-600/20 text-amber-300 hover:bg-amber-600/30 border border-amber-500/40 transition-colors flex items-center gap-1.5"
            >
              <BookOpen className="w-3.5 h-3.5 text-amber-400" />
              <span>Keep</span>
            </button>
            <button
              onClick={() => setIsAuditModalOpen(true)}
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/40 transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>فحص شامل بـ Gemini 3.8</span>
            </button>

            <button
              onClick={() => setActiveTab('gmail')}
              className="px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors flex items-center gap-1.5"
            >
              <Mail className="w-3.5 h-3.5 text-rose-400" />
              <span>Gmail</span>
            </button>

            <button
              onClick={() => setActiveTab('chat')}
              className="px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors flex items-center gap-1.5"
            >
              <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
              <span>Chat</span>
            </button>

            <button
              onClick={handleExportAll}
              className="px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5 text-slate-400" />
              <span>تصدير CSV</span>
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

            {/* Quick Action Feature Banners: 3D Server Room, Gemini AI, and GitHub DevOps Hub */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gradient-to-br from-slate-900 to-slate-950 p-4.5 rounded-2xl border border-cyan-500/30 flex flex-col justify-between gap-3 shadow-lg shadow-cyan-950/20">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                      <Box className="w-4 h-4" />
                    </span>
                    <h4 className="text-sm font-bold text-white">غرفة 3D (Three.js)</h4>
                  </div>
                  <p className="text-xs text-slate-400">
                    محاكاة واقعية لكبائن الخوادم وتدفق حزم البيانات ثلاثية الأبعاد
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab('3d_room')}
                  className="w-full py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs transition-colors shadow-md shadow-cyan-600/30"
                >
                  استعراض 3D
                </button>
              </div>

              <div className="bg-gradient-to-br from-slate-900 to-slate-950 p-4.5 rounded-2xl border border-indigo-500/30 flex flex-col justify-between gap-3 shadow-lg shadow-indigo-950/20">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                      <FolderGit2 className="w-4 h-4" />
                    </span>
                    <h4 className="text-sm font-bold text-white">مركز GitHub & CI/CD</h4>
                  </div>
                  <p className="text-xs text-slate-400">
                    أتمتة مسارات Actions، أوامر الرفع، وإصدارات Gemini الذكية
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab('github')}
                  className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-colors shadow-md shadow-indigo-600/30"
                >
                  فتح GitHub Hub
                </button>
              </div>

              <div className="bg-gradient-to-br from-slate-900 to-slate-950 p-4.5 rounded-2xl border border-purple-500/30 flex flex-col justify-between gap-3 shadow-lg shadow-purple-950/20">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-purple-500/20 text-purple-400 border border-purple-500/30">
                      <Bot className="w-4 h-4" />
                    </span>
                    <h4 className="text-sm font-bold text-white">مساعد DevOps الذكي</h4>
                  </div>
                  <p className="text-xs text-slate-400">
                    محادثة لحظية مع تفريغ صوتي، وتدعيم البحث عبر Google Search
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab('gemini_chat')}
                  className="w-full py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs transition-colors shadow-md shadow-purple-600/30"
                >
                  بدء المحادثة
                </button>
              </div>
            </div>

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

        {/* Tab GitHub DevOps & CI/CD Hub */}
        {activeTab === 'github' && (
          <GitHubTab
            servers={servers}
            incidents={incidents}
            deployments={deployments}
          />
        )}

        {/* Tab 3D Room: Virtual Cyber Server Center */}
        {activeTab === '3d_room' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Box className="w-5 h-5 text-cyan-400" />
                  غرفة الخوادم الافتراضية ثلاثية الأبعاد (Three.js 3D Virtual Cyber Room)
                </h3>
                <p className="text-xs text-slate-400">
                  محاكاة واقعية بتقنية PBR وإضاءة الاستوديو مع تفاعل كامل بالنقر على كل خادم ومراقبة حزم البيانات
                </p>
              </div>
            </div>
            <ServerRoom3D servers={servers} />
          </div>
        )}

        {/* Tab 3D Cyber Defense Game (Three.js) */}
        {activeTab === 'cyber_game' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Gamepad2 className="w-5 h-5 text-cyan-400" />
                  لعبة الدفاع السيبراني ثلاثية الأبعاد (Cyber Shield 3D Defense Game)
                </h3>
                <p className="text-xs text-slate-400">
                  لعبة تفاعلية متكاملة مبنية بـ Three.js لحماية مراكز الخوادم من هجمات DDoS والبرمجيات الخبيثة مع تأثيرات صوتية وموجات تصاعدية
                </p>
              </div>
            </div>
            <CyberDefenseGame />
          </div>
        )}

        {/* Tab Gemini Chat: DevOps AI Intelligence Command Center */}
        {activeTab === 'gemini_chat' && (
          <GeminiChatbot
            servers={servers}
            incidents={incidents}
            deployments={deployments}
            onRestartServer={handleRestartServer}
            onToggleMaintenance={handleToggleMaintenance}
            onResolveIncident={handleResolveIncident}
            onRedeploy={handleRedeploy}
            onRollback={handleRollback}
            onSimulateIncident={handleSimulateIncident}
          />
        )}

        {/* Tab Media Studio: Video, Image, and Music Synthesis */}
        {activeTab === 'media_studio' && (
          <AiMediaStudio />
        )}

        {/* Tab 5: Google Drive */}
        {activeTab === 'drive' && (
          <GoogleDriveTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            deployments={deployments}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
            onLogout={() => {
              setUser(null);
              setToken(null);
            }}
          />
        )}

        {/* Tab Google Docs: Official SRE Reports & RCA Post-Mortems */}
        {activeTab === 'docs' && (
          <DocsTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab 6: Gmail */}
        {activeTab === 'gmail' && (
          <GmailTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab 7: Google Chat */}
        {activeTab === 'chat' && (
          <ChatTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            deployments={deployments}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab 8: Google Forms */}
        {activeTab === 'forms' && (
          <FormsTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab 9: Google Sheets */}
        {activeTab === 'sheets' && (
          <SheetsTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab Google Slides: Presentations & Incident Decks */}
        {activeTab === 'slides' && (
          <SlidesTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab Google Tasks: Operations & SRE Tasks */}
        {activeTab === 'tasks' && (
          <TasksTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab Google Calendar: SRE War Rooms, Maintenance & Schedules */}
        {activeTab === 'calendar' && (
          <CalendarTab
            user={user}
            token={token}
            servers={servers}
            incidents={incidents}
            onAuthSuccess={(u, t) => {
              setUser(u);
              setToken(t);
            }}
          />
        )}

        {/* Tab 10: Keep Runbooks & Notes */}
        {activeTab === 'keep' && (
          <KeepTab user={user} token={token} />
        )}
      </main>

      {/* AI Modals */}
      {selectedIncidentForAi && (
        <AiIncidentModal
          incident={selectedIncidentForAi}
          server={targetServerForAi}
          onClose={() => setSelectedIncidentForAi(null)}
          onResolveIncident={handleResolveIncident}
          onDeployHotfix={handleDeployHotfix}
        />
      )}

      {isAuditModalOpen && (
        <AiAuditModal
          servers={servers}
          incidents={incidents}
          deployments={deployments}
          onClose={() => setIsAuditModalOpen(false)}
          token={token}
        />
      )}

      {/* Floating Real-Time DevOps Notification Toasts */}
      <div className="fixed bottom-5 left-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto p-3.5 rounded-2xl border shadow-2xl backdrop-blur-md flex items-center justify-between gap-3 text-xs transition-all animate-in fade-in slide-in-from-bottom-3 duration-300 ${
              t.type === 'success'
                ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200'
                : t.type === 'warning'
                ? 'bg-amber-950/90 border-amber-500/50 text-amber-200'
                : t.type === 'error'
                ? 'bg-rose-950/90 border-rose-500/50 text-rose-200'
                : 'bg-indigo-950/90 border-indigo-500/50 text-indigo-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="shrink-0">{t.message}</span>
            </div>
            <button
              onClick={() => setToasts((prev) => prev.filter((item) => item.id !== t.id))}
              className="text-slate-400 hover:text-white shrink-0 p-1 rounded-lg hover:bg-slate-800/60"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <footer className="py-6 border-t border-slate-800 text-center text-xs text-slate-500 bg-slate-950">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-400">منظومة رصد الخوادم</span>
            <span>·</span>
            <span>قاعدة بيانات سحابية حية (my-apps-hamedo)</span>
          </div>
          <div className="text-slate-400">
            مدعوم بنموذج Google Gemini 3.8 Flash وقاعدة بيانات Firestore السحابية
          </div>
        </div>
      </footer>
    </div>
  );
}
