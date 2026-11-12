import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User as UserIcon,
  Sparkles,
  Globe,
  MapPin,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  RotateCcw,
  ShieldCheck,
  Cpu,
  Flame,
  Wrench,
  ExternalLink,
  ChevronDown,
  Loader2,
  Play,
  CheckCircle2,
  AlertTriangle,
  Radio,
  Activity,
  Terminal,
  Zap,
  RefreshCw,
  Sliders,
  Check,
  Copy,
  TrendingUp,
  Clock,
  ShieldAlert,
} from 'lucide-react';
import { Server, Incident, Deployment } from '../../types/serverDashboard';

interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: string;
  sources?: { title: string; uri: string }[];
  searchQueries?: string[];
  suggestedActions?: {
    type: 'restart_server' | 'resolve_incident' | 'toggle_maintenance' | 'rollback';
    targetId: string;
    targetName: string;
    label: string;
    badge: string;
  }[];
}

interface GeminiChatbotProps {
  servers?: Server[];
  incidents?: Incident[];
  deployments?: Deployment[];
  onRestartServer?: (serverId: string) => void;
  onToggleMaintenance?: (serverId: string) => void;
  onResolveIncident?: (incidentId: string) => void;
  onRedeploy?: (deploymentId: string) => void;
  onRollback?: (deploymentId: string) => void;
  onSimulateIncident?: () => void;
}

export function GeminiChatbot({
  servers = [],
  incidents = [],
  deployments = [],
  onRestartServer,
  onToggleMaintenance,
  onResolveIncident,
  onRedeploy,
  onRollback,
  onSimulateIncident,
}: GeminiChatbotProps) {
  // Navigation sub-tabs within DevOps AI Intelligence Hub
  const [activeAiTab, setActiveAiTab] = useState<'copilot' | 'sentinel' | 'radar' | 'briefing' | 'sandbox'>('copilot');

  // Messages state
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome_1',
      role: 'model',
      text: `مرحباً بك! أنا مهندس الذكاء الاصطناعي ومساعد العمليات المستقل (DevOps & SRE Autonomous Copilot).
لدي اتصال لحظي ومباشر بجميع خوادمك (${servers.length} خادم) وسجلات الحوادث وعمليات النشر.

يمكنك أن تطلب مني:
• تشخيص الأعطال الحالية واقتراح الحلول
• تنفيذ أوامر فورية كإعادة تشغيل الخوادم المتعثرة أو تفعيل وضع الصيانة
• توليد أوامر Bash و Kubernetes و Docker
• الاستماع لتوجيهاتك الصوتية والرد الصوتي المباشر`,
      timestamp: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
      suggestedActions: servers.some((s) => s.status !== 'healthy')
        ? [
            {
              type: 'restart_server',
              targetId: servers.find((s) => s.status !== 'healthy')?.id || '',
              targetName: servers.find((s) => s.status !== 'healthy')?.name || '',
              label: `إعادة تشغيل ${servers.find((s) => s.status !== 'healthy')?.name}`,
              badge: 'Remediation',
            },
          ]
        : [],
    },
  ]);

  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<'gemini-4-argon' | 'gemini-3.8-flash' | 'gemini-3.1-flash-lite'>('gemini-3.8-flash');
  const [selectedRole, setSelectedRole] = useState<'sre_lead' | 'security_auditor' | 'incident_commander' | 'devops_copilot'>('sre_lead');
  const [useSearch, setUseSearch] = useState(true);
  const [useMaps, setUseMaps] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [executedActionId, setExecutedActionId] = useState<string | null>(null);

  // Sentinel Autonomous SRE State
  const [isSentinelActive, setIsSentinelActive] = useState(true);
  const [sentinelScanCount, setSentinelScanCount] = useState(14);
  const [sentinelLogs, setSentinelLogs] = useState<
    { id: string; time: string; type: 'scan' | 'heal' | 'alert'; message: string; badge: string }[]
  >([
    {
      id: 'log-1',
      time: 'الآن',
      type: 'scan',
      message: `مسح دوري شامل للبنية التحتية: رصد ${servers.length} خوادم نشطة ومعدل سلامة ${(
        (servers.filter((s) => s.status === 'healthy').length / Math.max(servers.length, 1)) *
        100
      ).toFixed(0)}%.`,
      badge: 'Radar Scan',
    },
    {
      id: 'log-2',
      time: 'منذ دقيقة',
      type: 'heal',
      message: 'التحقق من توازن الأحمال بين عقد الكلاستر وتفعيل تدابير العزل الوقائي للذاكرة.',
      badge: 'Auto-Healing',
    },
  ]);

  // Predictive Radar State
  const [radarLoading, setRadarLoading] = useState(false);
  const [radarData, setRadarData] = useState<{
    overallRiskScore: number;
    statusText: string;
    strategicRecommendation?: string;
    predictions: {
      serverId: string;
      serverName: string;
      riskScore: number;
      failureProbability: string;
      timeToExhaustion: string;
      keyRisk: string;
    }[];
  }>({
    overallRiskScore: 32,
    statusText: 'منخفض إلى معتدل - مستقر نسبياً',
    strategicRecommendation: 'يُنصح بزيادة حد الذاكرة لخوادم معالجة الدفعات وتوزيع أحمال العمل في أوقات الذروة.',
    predictions: servers.map((s) => ({
      serverId: s.id,
      serverName: s.name,
      riskScore: s.status === 'critical' ? 88 : s.status === 'warning' ? 56 : 14,
      failureProbability: s.status === 'critical' ? '82%' : s.status === 'warning' ? '34%' : '5%',
      timeToExhaustion: s.cpu > 80 ? '2.5 ساعات' : 'مستقر (> 72 ساعة)',
      keyRisk: s.memory > 75 ? 'احتمال اختناق بالذاكرة المؤقتة' : 'حمولة تشغيلية طبيعية',
    })),
  });

  // Daily SRE Audio Briefing State
  const [briefingText, setBriefingText] = useState('');
  const [isGeneratingBriefing, setIsGeneratingBriefing] = useState(false);

  // Shell Sandbox State
  const [selectedScriptType, setSelectedScriptType] = useState<'kubernetes' | 'docker' | 'nginx' | 'systemd'>('kubernetes');
  const [terminalOutput, setTerminalOutput] = useState<string>('');
  const [isExecutingScript, setIsExecutingScript] = useState(false);
  const [copiedScript, setCopiedScript] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Autonomous Sentinel loop: scans every 15s when active
  useEffect(() => {
    if (!isSentinelActive) return;

    const interval = setInterval(() => {
      setSentinelScanCount((c) => c + 1);

      // Check if any server needs healing
      const problematic = servers.filter((s) => s.status === 'critical' || s.cpu > 88);
      const currentTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      if (problematic.length > 0) {
        const target = problematic[0];
        setSentinelLogs((prev) => [
          {
            id: `heal-${Date.now()}`,
            time: currentTime,
            type: 'alert',
            message: `⚠️ [تنبيه الحارس الذكي] رصد مؤشرات حرجة على ${target.name} (استهلاك المعالج: ${target.cpu}%). جاري فحص خطة التعافي السريع.`,
            badge: 'Anomaly Alert',
          },
          ...prev.slice(0, 15),
        ]);
      } else {
        setSentinelLogs((prev) => [
          {
            id: `scan-${Date.now()}`,
            time: currentTime,
            type: 'scan',
            message: `🔍 [فحص دوري ناجح] كافة المقاييس تقع ضمن النطاق الطبيعي لـ ${servers.length} عقدة نشطة.`,
            badge: 'Telemetry OK',
          },
          ...prev.slice(0, 15),
        ]);
      }
    }, 15000);

    return () => clearInterval(interval);
  }, [isSentinelActive, servers]);

  // Audio Recording with Microphone for Audio Transcription (gemini-3.5-transcribe)
  const toggleRecording = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach((track) => track.stop());

        setIsTranscribing(true);
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Data = (reader.result as string).split(',')[1];
          try {
            const res = await fetch('/api/ai/transcribe-audio', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                audioBase64: base64Data,
                mimeType: 'audio/webm',
              }),
            });
            const data = await res.json();
            if (data.transcription) {
              setInputText((prev) => (prev ? `${prev} ${data.transcription}` : data.transcription));
            }
          } catch (err) {
            console.error('Audio transcription error:', err);
          } finally {
            setIsTranscribing(false);
          }
        };
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Microphone access denied:', err);
      alert('يرجى السماح بالوصول إلى الميكروفون للتسجيل والتفريغ الصوتي.');
    }
  };

  // Text-to-Speech playback using gemini-3.8-flash-lite-tts
  const speakMessage = async (text: string) => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
      setIsPlayingAudio(false);
    }

    try {
      setIsPlayingAudio(true);
      const res = await fetch('/api/ai/voice-speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (data.audioBase64) {
        const audio = new Audio(`data:${data.mimeType || 'audio/wav'};base64,${data.audioBase64}`);
        currentAudioRef.current = audio;
        audio.onended = () => setIsPlayingAudio(false);
        audio.play();
      } else {
        setIsPlayingAudio(false);
      }
    } catch (err) {
      console.error('TTS playback error:', err);
      setIsPlayingAudio(false);
    }
  };

  // Execute AI action on live infrastructure
  const handleExecuteAction = (action: {
    type: 'restart_server' | 'resolve_incident' | 'toggle_maintenance' | 'rollback';
    targetId: string;
    targetName: string;
    label: string;
  }) => {
    setExecutedActionId(action.targetId);

    if (action.type === 'restart_server' && onRestartServer) {
      onRestartServer(action.targetId);
    } else if (action.type === 'toggle_maintenance' && onToggleMaintenance) {
      onToggleMaintenance(action.targetId);
    } else if (action.type === 'resolve_incident' && onResolveIncident) {
      onResolveIncident(action.targetId);
    } else if (action.type === 'rollback' && onRollback) {
      onRollback(action.targetId);
    }

    setTimeout(() => {
      setExecutedActionId(null);
    }, 2500);

    // Append AI confirmation in chat
    const confirmMsg: ChatMessage = {
      id: `confirm_${Date.now()}`,
      role: 'model',
      text: `✅ [تم التنفيذ بنجاح]: تم إرسال وتطبيق أمر [${action.label}] على البنية التحتية ومزامنة الحالة مع قاعدة بيانات Firestore السحابية فوراً.`,
      timestamp: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, confirmMsg]);
  };

  // Autonomous Heal All Action
  const handleHealAllAnomalies = () => {
    const troubledServers = servers.filter((s) => s.status !== 'healthy');
    troubledServers.forEach((s) => {
      if (onRestartServer) onRestartServer(s.id);
    });

    const openIncidents = incidents.filter((i) => !i.resolved);
    openIncidents.forEach((i) => {
      if (onResolveIncident) onResolveIncident(i.id);
    });

    const logEntry = {
      id: `heal-all-${Date.now()}`,
      time: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
      type: 'heal' as const,
      message: `⚡ [المعالجة الذاتية الشاملة]: تم تنفيذ إعادة التشغيل السلسة وتصفير الأخطاء لـ ${troubledServers.length} خوادم وإغلاق ${openIncidents.length} حوادث مفتوحة.`,
      badge: 'Auto-Remediate',
    };
    setSentinelLogs((prev) => [logEntry, ...prev]);

    // Send confirmation to chat
    setMessages((prev) => [
      ...prev,
      {
        id: `heal_all_${Date.now()}`,
        role: 'model',
        text: `🛡️ تم تشغيل بروتوكول المعالجة الذاتية الشاملة (Autonomous Remediation Protocol):
• تمت معالجة وإعادة تشغيل ${troubledServers.length} عقدة متأثرة
• تم إغلاق وحل ${openIncidents.length} حادثة مسجلة
• كافة المؤشرات الآن تحت إشراف الحارس الذكي.`,
        timestamp: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // Send message to Gemini chat
  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
    };

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map((m) => ({ role: m.role, text: m.text })),
          modelName: selectedModel,
          role: selectedRole,
          useSearch,
          useMaps,
          systemContext: {
            servers,
            incidents,
            deployments,
          },
        }),
      });

      const data = await response.json();

      const modelMsg: ChatMessage = {
        id: `model_${Date.now()}`,
        role: 'model',
        text: data.reply || 'تمت معالجة الطلب.',
        timestamp: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
        sources: data.groundingSources,
        searchQueries: data.searchQueries,
        suggestedActions: data.suggestedActions || [],
      };

      setMessages((prev) => [...prev, modelMsg]);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: `error_${Date.now()}`,
          role: 'model',
          text: 'عذراً، حدث خطأ أثناء الاتصال بالنموذج. يرجى التأكد من تشغيل الخادم والمحاولة مرة أخرى.',
          timestamp: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch Predictive Anomaly Radar
  const handleRefreshRadar = async () => {
    setRadarLoading(true);
    try {
      const res = await fetch('/api/ai/predictive-forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ servers }),
      });
      const data = await res.json();
      if (data && data.predictions) {
        setRadarData(data);
      }
    } catch (e) {
      console.error('Failed to refresh radar:', e);
    } finally {
      setRadarLoading(false);
    }
  };

  // Generate Daily SRE Audio Briefing
  const handleGenerateBriefing = async () => {
    setIsGeneratingBriefing(true);
    try {
      const res = await fetch('/api/ai/generate-sre-briefing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ servers, incidents, deployments }),
      });
      const data = await res.json();
      if (data && data.briefingText) {
        setBriefingText(data.briefingText);
        // Play TTS automatically
        speakMessage(data.briefingText);
      }
    } catch (e) {
      console.error('Briefing error:', e);
    } finally {
      setIsGeneratingBriefing(false);
    }
  };

  // Sandbox scripts template
  const scripts = {
    kubernetes: `# ☸️ Kubernetes Automated Pod Scaling & Eviction Runbook
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-cluster-prod
  namespace: production
spec:
  replicas: 5
  strategy:
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: api-worker
        image: gcr.io/serverops-cloud/api:v2.5.0
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
          requests:
            cpu: "500m"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 10`,
    docker: `# 🐳 Docker Production Zero-Downtime Reload
docker compose pull
docker compose up -d --no-deps --build api-cluster
docker container prune -f
docker stats --no-stream`,
    nginx: `# 🌐 Nginx High-Concurrency Reverse Proxy Hardening
events {
    worker_connections 4096;
    multi_accept on;
}
http {
    upstream backend_cluster {
        least_conn;
        server 10.0.1.10:8080 max_fails=3 fail_timeout=10s;
        server 10.0.1.11:8080 max_fails=3 fail_timeout=10s;
        keepalive 64;
    }
    server {
        listen 443 ssl http2;
        server_name api.serverops.internal;
        location / {
            proxy_pass http://backend_cluster;
            proxy_next_upstream error timeout http_502;
        }
    }
}`,
    systemd: `# ⚙️ Linux Systemd Graceful Service Supervisor
[Unit]
Description=ServerOps SRE Sentinel Agent
After=network.target

[Service]
Type=simple
User=ops-admin
ExecStart=/usr/local/bin/serverops-agent --telemetry-port=9100
Restart=always
RestartSec=5s
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target`,
  };

  const handleRunSandbox = () => {
    setIsExecutingScript(true);
    setTerminalOutput('جاري الاتصال ببيئة المحاكاة الافتراضية (Sandbox Simulator)...\n$ kubectl apply -f deployment.yaml');

    setTimeout(() => {
      setTerminalOutput((prev) => `${prev}\n[INFO] deployment.apps/api-cluster-prod configured`);
    }, 800);

    setTimeout(() => {
      setTerminalOutput((prev) => `${prev}\n[SUCCESS] 5/5 Pods in Ready state. Rolling update verified smoothly with 0 error rate.`);
      setIsExecutingScript(false);
    }, 1800);
  };

  const handleCopyScript = () => {
    navigator.clipboard.writeText(scripts[selectedScriptType]);
    setCopiedScript(true);
    setTimeout(() => setCopiedScript(false), 2000);
  };

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl space-y-0">
      {/* Top Cyber Command Header */}
      <div className="p-4 sm:p-5 border-b border-slate-800 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/60 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="p-3 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-500 text-white shadow-xl shadow-indigo-600/30 flex items-center justify-center">
              <Bot className="w-6 h-6 animate-pulse" />
            </div>
            {isSentinelActive && (
              <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-emerald-400 border-2 border-slate-900 rounded-full animate-ping" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base sm:text-lg font-extrabold text-white flex items-center gap-2">
                مركز ذكاء العمليات المستقل (DevOps AI Intelligence Suite)
              </h3>
              <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 font-mono font-bold">
                Gemini 3.8 + Realtime Actions
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              مراقبة ذاتية، تحليل أسباب جذرية، معالجة استباقية بنقرة زر، ومحادثة صوتية مدعومة بالبحث اللحظي
            </p>
          </div>
        </div>

        {/* AI Navigation Modes */}
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-950/80 p-1.5 rounded-2xl border border-slate-800 text-xs font-semibold">
          <button
            onClick={() => setActiveAiTab('copilot')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeAiTab === 'copilot'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            <span>المساعد الذكي (Copilot)</span>
          </button>

          <button
            onClick={() => setActiveAiTab('sentinel')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeAiTab === 'sentinel'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>حارس SRE المستقل</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </button>

          <button
            onClick={() => setActiveAiTab('radar')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeAiTab === 'radar'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>رادار التنبؤ بالمخاطر</span>
          </button>

          <button
            onClick={() => setActiveAiTab('briefing')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeAiTab === 'briefing'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Volume2 className="w-3.5 h-3.5 text-purple-400" />
            <span>الموجز الصوتي SRE</span>
          </button>

          <button
            onClick={() => setActiveAiTab('sandbox')}
            className={`px-3 py-1.5 rounded-xl transition-all flex items-center gap-1.5 ${
              activeAiTab === 'sandbox'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Terminal className="w-3.5 h-3.5 text-amber-400" />
            <span>أوامر الـ Shell والـ Runbooks</span>
          </button>
        </div>
      </div>

      {/* MODE 1: Interactive Copilot with Function Calling */}
      {activeAiTab === 'copilot' && (
        <div className="flex flex-col h-[680px]">
          {/* Subheader controls */}
          <div className="px-4 py-2.5 bg-slate-950/70 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1 bg-slate-900 px-2.5 py-1.5 rounded-xl border border-slate-800">
                <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value as any)}
                  className="bg-transparent text-slate-200 outline-none cursor-pointer text-xs"
                >
                  <option value="gemini-3.8-flash" className="bg-slate-900">Gemini 3.8 Flash (متوازن وسريع)</option>
                  <option value="gemini-4-argon" className="bg-slate-900">Gemini 4 Argon (للمهام العميقة)</option>
                  <option value="gemini-3.1-flash-lite" className="bg-slate-900">Gemini 3.1 Flash-Lite (خفيف)</option>
                </select>
              </div>

              <div className="flex items-center gap-1 bg-slate-900 px-2.5 py-1.5 rounded-xl border border-slate-800">
                <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value as any)}
                  className="bg-transparent text-slate-200 outline-none cursor-pointer text-xs"
                >
                  <option value="sre_lead" className="bg-slate-900">دور: رئيس مهندسي SRE</option>
                  <option value="incident_commander" className="bg-slate-900">دور: قائد طوارئ الحوادث</option>
                  <option value="security_auditor" className="bg-slate-900">دور: مدقق أمان SecOps</option>
                  <option value="devops_copilot" className="bg-slate-900">دور: مساعد DevOps الميداني</option>
                </select>
              </div>

              <button
                onClick={() => setUseSearch(!useSearch)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl border transition-colors ${
                  useSearch ? 'bg-blue-500/20 text-blue-400 border-blue-500/30 font-medium' : 'bg-slate-900 text-slate-500 border-slate-800'
                }`}
              >
                <Globe className="w-3 h-3" />
                <span>Google Search</span>
              </button>

              <button
                onClick={() => setUseMaps(!useMaps)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-xl border transition-colors ${
                  useMaps ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-medium' : 'bg-slate-900 text-slate-500 border-slate-800'
                }`}
              >
                <MapPin className="w-3 h-3" />
                <span>Google Maps</span>
              </button>
            </div>

            {/* Quick Action Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto">
              <button
                onClick={() => handleSendMessage('حلل لي وضع الخوادم الحالي فوراً واقترح خطة علاجية للأعطال.')}
                className="px-2.5 py-1 rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600 hover:text-white border border-indigo-500/30 transition-colors whitespace-nowrap text-[11px]"
              >
                ⚡ تشخيص شامل
              </button>
              <button
                onClick={() => handleSendMessage('ما هي الخوادم المعرضة لاختناق الذاكرة أو المعالج وما التدابير الفورية؟')}
                className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors whitespace-nowrap text-[11px]"
              >
                ⚠️ خوادم الخطر
              </button>
              <button
                onClick={() => handleSendMessage('اكتب لي كود Kubernetes Deployment و Nginx لضبط الأحمال العالية.')}
                className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors whitespace-nowrap text-[11px]"
              >
                ☸️ تكوين K8s
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div key={msg.id} className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-white shadow-md ${
                      isUser ? 'bg-indigo-600' : 'bg-gradient-to-tr from-cyan-600 to-indigo-600'
                    }`}
                  >
                    {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`max-w-[85%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed ${
                      isUser
                        ? 'bg-indigo-600/30 text-white border border-indigo-500/40 shadow-md'
                        : 'bg-slate-950/80 text-slate-200 border border-slate-800 shadow-lg'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.text}</div>

                    {/* Interactive Action Buttons Triggered by AI */}
                    {msg.suggestedActions && msg.suggestedActions.length > 0 && (
                      <div className="mt-3.5 pt-3 border-t border-slate-800/80 space-y-2">
                        <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-400">
                          <Zap className="w-3.5 h-3.5" />
                          <span>إجراءات تنفيذية مباشرة على البنية التحتية (AI Action Triggers):</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {msg.suggestedActions.map((act, i) => (
                            <button
                              key={i}
                              onClick={() => handleExecuteAction(act)}
                              disabled={executedActionId === act.targetId}
                              className="px-3 py-1.5 rounded-xl bg-indigo-600/30 hover:bg-indigo-600 text-indigo-200 hover:text-white border border-indigo-500/50 transition-all font-semibold text-xs flex items-center gap-1.5 shadow-sm"
                            >
                              {executedActionId === act.targetId ? (
                                <>
                                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                                  <span>تم التنفيذ والمزامنة!</span>
                                </>
                              ) : (
                                <>
                                  <Play className="w-3 h-3 text-cyan-400 fill-cyan-400" />
                                  <span>{act.label}</span>
                                  <span className="text-[10px] bg-slate-900/80 px-1.5 py-0.5 rounded text-indigo-300 font-mono">
                                    {act.badge}
                                  </span>
                                </>
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Grounding Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-800/80">
                        <p className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5 mb-1.5">
                          <Globe className="w-3 h-3 text-blue-400" />
                          مصادر التحقق عبر الويب (Google Grounding):
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.sources.map((src, i) => (
                            <a
                              key={i}
                              href={src.uri}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[10px] px-2 py-1 rounded-md bg-slate-900 text-blue-400 hover:bg-slate-850 border border-slate-700/80 flex items-center gap-1 transition-colors"
                            >
                              <ExternalLink className="w-2.5 h-2.5" />
                              {src.title.length > 28 ? `${src.title.slice(0, 28)}...` : src.title}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Footer: Timestamp & TTS */}
                    <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2.5">
                      <span>{msg.timestamp}</span>
                      {!isUser && (
                        <button
                          onClick={() => speakMessage(msg.text)}
                          className="hover:text-indigo-400 transition-colors flex items-center gap-1"
                          title="استمع للإجابة بصوت الذكاء الاصطناعي (TTS)"
                        >
                          <Volume2 className="w-3.5 h-3.5" />
                          <span>قراءة صوتية</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {isLoading && (
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-slate-950/80 rounded-2xl p-4 text-xs text-slate-400 flex items-center gap-2 border border-slate-800">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                  <span>يقوم محرك Gemini 3.8 بفحص التليمترية وتحليل الأسباب الجذرية...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-3 border-t border-slate-800 bg-slate-950 flex items-center gap-2"
          >
            <button
              type="button"
              onClick={toggleRecording}
              disabled={isTranscribing}
              className={`p-3 rounded-xl transition-all flex items-center justify-center ${
                isRecording
                  ? 'bg-rose-600 text-white animate-pulse'
                  : isTranscribing
                  ? 'bg-amber-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800'
              }`}
              title={isRecording ? 'إيقاف التسجيل الصوتي' : 'تحدث وسيقوم Gemini بتفريغ كلامك'}
            >
              {isTranscribing ? <Loader2 className="w-4 h-4 animate-spin" /> : isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={
                isRecording
                  ? 'جاري التسجيل الصوتي... انقر لإنهاء الكلام والتفريغ'
                  : isTranscribing
                  ? 'جاري تفريغ الصوت بنموذج gemini-3.5-transcribe...'
                  : 'اكتب أمراً برمجياً، أو استفساراً تشغيلياً، أو اطلب معالجة خادم معين...'
              }
              disabled={isLoading || isTranscribing}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />

            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl transition-colors shadow-lg shadow-indigo-600/30 flex items-center justify-center"
            >
              <Send className="w-4 h-4 rotate-180" />
            </button>
          </form>
        </div>
      )}

      {/* MODE 2: Autonomous SRE Sentinel & Self-Healing */}
      {activeAiTab === 'sentinel' && (
        <div className="p-6 space-y-6">
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white flex items-center gap-2">
                  حارس SRE الذكي المستقل (Autonomous Sentinel Engine)
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono">
                    Active Sentinel
                  </span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  يراقب معدلات استهلاك المعالج، الذاكرة، القرص، وتدفق حزم البيانات كل 15 ثانية ويطبق المعالجة الذاتية التلقائية.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsSentinelActive(!isSentinelActive)}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border ${
                  isSentinelActive
                    ? 'bg-emerald-600/30 text-emerald-300 border-emerald-500/50'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                <span className={`w-2.5 h-2.5 rounded-full ${isSentinelActive ? 'bg-emerald-400 animate-ping' : 'bg-slate-500'}`} />
                <span>{isSentinelActive ? 'الحارس الذاتي قيد العمل' : 'الحارس الذاتي معطل'}</span>
              </button>

              <button
                onClick={handleHealAllAnomalies}
                className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold rounded-xl transition-all shadow-md shadow-indigo-600/30 flex items-center gap-1.5"
              >
                <Zap className="w-3.5 h-3.5 text-amber-300 fill-amber-300" />
                <span>معالجة ذاتية شاملة (Heal All Now)</span>
              </button>
            </div>
          </div>

          {/* Live Holographic Sentinel Radar Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-950 p-4.5 rounded-2xl border border-slate-800 space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-indigo-400" />
                <span>عمليات المسح المنجزة</span>
              </div>
              <div className="text-2xl font-black text-white font-mono">{sentinelScanCount} دورة</div>
              <p className="text-[10px] text-emerald-400">تكرار كل 15 ثانية تلقائياً</p>
            </div>

            <div className="bg-slate-950 p-4.5 rounded-2xl border border-slate-800 space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>معدل صحة المنظومة</span>
              </div>
              <div className="text-2xl font-black text-emerald-400 font-mono">
                {((servers.filter((s) => s.status === 'healthy').length / Math.max(servers.length, 1)) * 100).toFixed(0)}%
              </div>
              <p className="text-[10px] text-slate-400">{servers.filter((s) => s.status === 'healthy').length} من {servers.length} عقد سليمة</p>
            </div>

            <div className="bg-slate-950 p-4.5 rounded-2xl border border-slate-800 space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span>العقد التي تتطلب تدخلاً</span>
              </div>
              <div className="text-2xl font-black text-amber-400 font-mono">
                {servers.filter((s) => s.status !== 'healthy').length}
              </div>
              <p className="text-[10px] text-slate-400">تحذيرات أو استهلاك مرتفع</p>
            </div>

            <div className="bg-slate-950 p-4.5 rounded-2xl border border-slate-800 space-y-1">
              <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                <span>بروتوكول المعالجة</span>
              </div>
              <div className="text-2xl font-black text-cyan-400 font-mono">Zero-Touch</div>
              <p className="text-[10px] text-slate-400">تدخل آلي دون توقف الخدمة</p>
            </div>
          </div>

          {/* Sentinel Live Activity Log */}
          <div className="bg-slate-950 rounded-2xl border border-slate-800 p-5 space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h5 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                <span>سجل نشاط وتدخلات الحارس الذاتي المستمر (Sentinel Neural Log)</span>
              </h5>
              <span className="text-[11px] text-slate-400 font-mono">Real-time Stream</span>
            </div>

            <div className="space-y-2.5 max-h-80 overflow-y-auto">
              {sentinelLogs.map((log) => (
                <div
                  key={log.id}
                  className="p-3 bg-slate-900/80 rounded-xl border border-slate-800/80 flex items-start justify-between gap-3 text-xs"
                >
                  <div className="flex items-start gap-2.5">
                    <span
                      className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${
                        log.type === 'heal'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : log.type === 'alert'
                          ? 'bg-rose-500/20 text-rose-400'
                          : 'bg-indigo-500/20 text-indigo-400'
                      }`}
                    >
                      {log.type === 'heal' ? (
                        <Zap className="w-3.5 h-3.5" />
                      ) : log.type === 'alert' ? (
                        <AlertTriangle className="w-3.5 h-3.5" />
                      ) : (
                        <Radio className="w-3.5 h-3.5" />
                      )}
                    </span>
                    <div>
                      <p className="text-slate-200">{log.message}</p>
                      <span className="text-[10px] text-slate-500 mt-1 font-mono">{log.time}</span>
                    </div>
                  </div>

                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-950 text-indigo-400 border border-slate-800 shrink-0 font-mono">
                    {log.badge}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* MODE 3: Predictive Anomaly Radar */}
      {activeAiTab === 'radar' && (
        <div className="p-6 space-y-6">
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-cyan-400" />
                <span>رادار التنبؤ الاستباقي بالأعطال والمخاطر (AI Predictive Risk Radar)</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                تحليل اتجاهات استهلاك الموارد وتوقع احتمالية الأعطال قبل حدوثها بـ 6-12 ساعة
              </p>
            </div>

            <button
              onClick={handleRefreshRadar}
              disabled={radarLoading}
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition-all shadow-md flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${radarLoading ? 'animate-spin' : ''}`} />
              <span>تحديث التنبؤات بـ Gemini</span>
            </button>
          </div>

          {/* Strategic Recommendation Banner */}
          {radarData.strategicRecommendation && (
            <div className="bg-gradient-to-r from-indigo-950/40 via-purple-950/40 to-slate-900 border border-indigo-500/40 rounded-2xl p-4 flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <h5 className="text-xs font-bold text-indigo-300">التوصية الهندسية الاستباقية للـ SRE:</h5>
                <p className="text-xs text-slate-200 mt-1 leading-relaxed">{radarData.strategicRecommendation}</p>
              </div>
            </div>
          )}

          {/* Predictions Table */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {radarData.predictions.map((pred, i) => (
              <div
                key={i}
                className="bg-slate-950 rounded-2xl border border-slate-800 p-4.5 space-y-3 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-white font-mono">{pred.serverName}</span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                      pred.riskScore > 70
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        : pred.riskScore > 40
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    }`}
                  >
                    Risk: {pred.riskScore}%
                  </span>
                </div>

                <div className="space-y-1 text-xs">
                  <div className="flex justify-between text-slate-400">
                    <span>احتمالية الفشل التنبؤية:</span>
                    <span className="font-bold text-white font-mono">{pred.failureProbability}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>الوقت المتوقع لنفاد المورد:</span>
                    <span className="font-bold text-indigo-300 font-mono">{pred.timeToExhaustion}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>نقطة الضعف الرئيسية:</span>
                    <span className="text-slate-300">{pred.keyRisk}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleSendMessage(`اشرح لي خطة التخفيف الموصى بها للخادم ${pred.serverName} المعرض لمخاطر ${pred.keyRisk}.`)}
                  className="w-full py-1.5 rounded-xl bg-slate-900 hover:bg-slate-850 text-indigo-400 hover:text-indigo-300 border border-slate-800 text-xs font-semibold transition-colors flex items-center justify-center gap-1"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>طلب خطة التخفيف من المساعد</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODE 4: Daily SRE Audio Briefing */}
      {activeAiTab === 'briefing' && (
        <div className="p-6 space-y-6">
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Volume2 className="w-5 h-5 text-purple-400" />
                <span>الموجز الصوتي التنفيذي اليومي (Daily SRE Audio Briefing)</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                توليد موجز صوتي ناطق بالذكاء الاصطناعي (TTS) يلخص حالة الأنظمة، الحوادث، وعمليات النشر
              </p>
            </div>

            <button
              onClick={handleGenerateBriefing}
              disabled={isGeneratingBriefing}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition-all shadow-md flex items-center gap-2"
            >
              <Volume2 className={`w-4 h-4 ${isGeneratingBriefing ? 'animate-spin' : ''}`} />
              <span>{isGeneratingBriefing ? 'جارٍ التوليد والبث...' : 'توليد وبث الموجز الصوتي الآن'}</span>
            </button>
          </div>

          {/* Sound Waves Animation Visualizer */}
          <div className="bg-gradient-to-br from-slate-950 to-indigo-950/40 rounded-2xl border border-indigo-500/30 p-8 flex flex-col items-center justify-center text-center space-y-4">
            <div className="flex items-center gap-1.5 h-16">
              {[40, 65, 30, 85, 95, 60, 45, 90, 75, 50, 80, 40, 70, 95, 35, 60, 85].map((h, i) => (
                <div
                  key={i}
                  style={{ height: isPlayingAudio ? `${h}%` : '20%' }}
                  className={`w-1.5 rounded-full transition-all duration-300 ${
                    isPlayingAudio ? 'bg-gradient-to-t from-indigo-500 to-cyan-400 animate-pulse' : 'bg-slate-700'
                  }`}
                />
              ))}
            </div>

            <div>
              <p className="text-xs font-semibold text-slate-300">
                {isPlayingAudio ? 'جاري بث الموجز الصوتي التنفيذي عبر مكبرات الصوت...' : 'الموجز جاهز للبث الصوتي'}
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">نموذج النطق: gemini-3.8-flash-lite-tts</p>
            </div>
          </div>

          {/* Briefing text content */}
          {briefingText && (
            <div className="bg-slate-950 rounded-2xl border border-slate-800 p-5 space-y-2">
              <span className="text-xs font-bold text-slate-300">نص التقرير الصوتي:</span>
              <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">{briefingText}</p>
            </div>
          )}
        </div>
      )}

      {/* MODE 5: Shell & Runbook Sandbox */}
      {activeAiTab === 'sandbox' && (
        <div className="p-6 space-y-6">
          <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-amber-400" />
                <span>مختبر أوامر ومخططات التشغيل (Shell & Runbook Sandbox)</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                مخططات جاهزة للنشر والإصلاح بضغطة زر مع محاكي طرفية لتجربة الأوامر بأمان
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedScriptType}
                onChange={(e) => setSelectedScriptType(e.target.value as any)}
                className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-xl text-xs text-white font-mono"
              >
                <option value="kubernetes">Kubernetes Deployment</option>
                <option value="docker">Docker Zero-Downtime</option>
                <option value="nginx">Nginx High-Load Proxy</option>
                <option value="systemd">Linux Systemd Agent</option>
              </select>

              <button
                onClick={handleCopyScript}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-xl border border-slate-700 flex items-center gap-1.5"
              >
                {copiedScript ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedScript ? 'تم النسخ!' : 'نسخ الكود'}</span>
              </button>

              <button
                onClick={handleRunSandbox}
                disabled={isExecutingScript}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white rounded-xl shadow-md flex items-center gap-1.5"
              >
                <Play className={`w-3.5 h-3.5 ${isExecutingScript ? 'animate-spin' : ''}`} />
                <span>تشغيل بالمحاكي</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Script Code Viewer */}
            <div className="bg-slate-950 rounded-2xl border border-slate-800 p-4 space-y-2">
              <span className="text-xs font-mono text-slate-400">ملف التكوين ({selectedScriptType}):</span>
              <pre className="p-4 bg-slate-900/90 rounded-xl border border-slate-800 text-[11px] font-mono text-indigo-200 overflow-x-auto max-h-80 select-all" dir="ltr">
                {scripts[selectedScriptType]}
              </pre>
            </div>

            {/* Simulated Terminal Output */}
            <div className="bg-slate-950 rounded-2xl border border-slate-800 p-4 space-y-2 font-mono">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                  طرفية المحاكاة الآمنة (Simulated SRE Terminal)
                </span>
                <span className="text-slate-500">ops@serverops-sandbox</span>
              </div>
              <div className="p-4 bg-slate-900/90 rounded-xl border border-slate-800 text-[11px] text-emerald-400 min-h-[200px] max-h-80 overflow-y-auto whitespace-pre-wrap" dir="ltr">
                {terminalOutput || 'اضغط على "تشغيل بالمحاكي" لتجربة تطبيق ملف التكوين وملاحظة مخرجات الـ Pods والـ Containers مباشرة.'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
