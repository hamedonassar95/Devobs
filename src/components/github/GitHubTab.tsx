import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  Copy,
  ExternalLink,
  Sparkles,
  Terminal,
  RefreshCw,
  FolderGit2,
  ShieldAlert,
  Tag,
  AlertCircle,
  FileCode,
  Send,
  Workflow,
  Check,
  Star,
  GitFork,
  Radio,
  Download,
  Key,
  Eye,
  EyeOff,
  UploadCloud,
  AlertTriangle,
} from 'lucide-react';
import { Server, Incident, Deployment } from '../../types/serverDashboard';

interface GitHubTabProps {
  servers: Server[];
  incidents: Incident[];
  deployments: Deployment[];
}

interface WorkflowRun {
  id: string;
  workflowName: string;
  workflowFile: string;
  event: string;
  status: 'completed' | 'in_progress' | 'queued' | 'failed';
  conclusion: 'success' | 'failure' | 'neutral' | null;
  branch: string;
  commitHash: string;
  duration: string;
  startedAt: string;
  steps: { name: string; status: 'completed' | 'running' | 'pending'; duration: string }[];
}

interface GitHubIssue {
  id: number;
  number: number;
  title: string;
  body: string;
  state: 'open' | 'closed';
  labels: { name: string; color: string }[];
  author: string;
  createdAt: string;
  commentsCount: number;
  relatedServerId?: string;
}

interface GitHubPR {
  id: number;
  number: number;
  title: string;
  author: string;
  branch: string;
  targetBranch: string;
  state: 'open' | 'merged' | 'closed';
  ciStatus: 'success' | 'pending' | 'failed';
  additions: number;
  deletions: number;
  createdAt: string;
}

export const GitHubTab: React.FC<GitHubTabProps> = ({ servers, incidents, deployments }) => {
  // Local repository metadata
  const [gitInfo, setGitInfo] = useState<{
    branch: string;
    latestCommit: { hash: string; author: string; email: string; date: string; message: string };
    status: string;
    repoName: string;
    owner: string;
  }>({
    branch: 'main',
    latestCommit: {
      hash: 'c30dcc0',
      author: 'Hamedo Nassar',
      email: 'hamedonassar95@gmail.com',
      date: new Date().toISOString(),
      message: 'feat: initialize Devobs repository with AI intelligence & automated CI/CD',
    },
    status: 'clean',
    repoName: 'Devobs',
    owner: 'hamedonassar95',
  });

  // User input for pushing
  const [customUsername, setCustomUsername] = useState('hamedonassar95');
  const [customRepoName, setCustomRepoName] = useState('Devobs');
  const [personalAccessToken, setPersonalAccessToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [targetPushBranch, setTargetPushBranch] = useState('main');
  const [allowForcePush, setAllowForcePush] = useState(false);
  const [isTestingToken, setIsTestingToken] = useState(false);
  const [tokenTestResult, setTokenTestResult] = useState<{
    success: boolean;
    user?: { login: string; name: string; avatar_url: string };
    repo?: { full_name: string; permissions?: any; default_branch: string };
    canPush?: boolean;
    error?: string;
  } | null>(null);
  const [isPushingLive, setIsPushingLive] = useState(false);
  const [pushResult, setPushResult] = useState<{
    success: boolean;
    message?: string;
    commit?: string;
    branch?: string;
    repoUrl?: string;
    error?: string;
    isNonFastForward?: boolean;
    hint?: string;
  } | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);

  // Sub-tabs in GitHub Hub
  const [activeSubTab, setActiveSubTab] = useState<'workflows' | 'push_wizard' | 'commits' | 'prs' | 'issues' | 'releases' | 'webhooks'>('push_wizard');

  // Workflows state
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([
    {
      id: 'run-101',
      workflowName: 'CI Build & Quality Gate',
      workflowFile: '.github/workflows/ci.yml',
      event: 'push',
      status: 'completed',
      conclusion: 'success',
      branch: 'main',
      commitHash: 'd69579e',
      duration: '42s',
      startedAt: 'منذ 5 دقائق',
      steps: [
        { name: 'Checkout Code', status: 'completed', duration: '3s' },
        { name: 'Setup Node.js 22', status: 'completed', duration: '5s' },
        { name: 'Install Dependencies (npm ci)', status: 'completed', duration: '14s' },
        { name: 'Run Type Check & Lint', status: 'completed', duration: '8s' },
        { name: 'Build Production Bundle', status: 'completed', duration: '12s' },
      ],
    },
    {
      id: 'run-102',
      workflowName: 'CD Automated Deployment & Cloud Delivery',
      workflowFile: '.github/workflows/deploy.yml',
      event: 'workflow_dispatch',
      status: 'completed',
      conclusion: 'success',
      branch: 'main',
      commitHash: 'd69579e',
      duration: '1m 15s',
      startedAt: 'منذ 15 دقيقة',
      steps: [
        { name: 'Checkout Code', status: 'completed', duration: '3s' },
        { name: 'Setup Node.js 22', status: 'completed', duration: '4s' },
        { name: 'Install Dependencies', status: 'completed', duration: '12s' },
        { name: 'Production Build', status: 'completed', duration: '14s' },
        { name: 'Notify SRE Console', status: 'completed', duration: '2s' },
      ],
    },
  ]);

  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchEnv, setDispatchEnv] = useState<'production' | 'staging'>('production');

  // Pull requests state
  const [pullRequests, setPullRequests] = useState<GitHubPR[]>([
    {
      id: 17,
      number: 17,
      title: 'feat: add GitHub DevOps integration & Actions CI/CD workflows',
      author: 'hamedonassar95',
      branch: 'feat/github-integration',
      targetBranch: 'main',
      state: 'open',
      ciStatus: 'success',
      additions: 1250,
      deletions: 45,
      createdAt: 'اليوم',
    },
    {
      id: 16,
      number: 16,
      title: 'feat: Google Workspace Enterprise Integrations & Sync',
      author: 'hamedonassar95',
      branch: 'feat/workspace-integration',
      targetBranch: 'main',
      state: 'merged',
      ciStatus: 'success',
      additions: 3420,
      deletions: 120,
      createdAt: 'أمس',
    },
    {
      id: 15,
      number: 15,
      title: 'feat: Cyber Shield 3D Defense Game against DDoS attacks',
      author: 'hamedonassar95',
      branch: 'feat/cyber-game',
      targetBranch: 'main',
      state: 'merged',
      ciStatus: 'success',
      additions: 1840,
      deletions: 30,
      createdAt: 'منذ يومين',
    },
    {
      id: 14,
      number: 14,
      title: 'feat: Three.js 3D Server Room Virtual Rack Simulator',
      author: 'hamedonassar95',
      branch: 'feat/3d-server-room',
      targetBranch: 'main',
      state: 'merged',
      ciStatus: 'success',
      additions: 2190,
      deletions: 15,
      createdAt: 'منذ 3 أيام',
    },
  ]);

  // Issues state
  const [issues, setIssues] = useState<GitHubIssue[]>([
    {
      id: 42,
      number: 42,
      title: '[INCIDENT-CRITICAL] Gateway Proxy Timeout on API Gateway Cluster',
      body: 'Automated SRE incident conversion from ServerOps console. HTTP 502 Bad Gateway observed on upstream proxy.',
      state: 'open',
      labels: [
        { name: 'incident', color: 'b60205' },
        { name: 'severity:critical', color: 'd93f0b' },
        { name: 'sre', color: '0052cc' },
      ],
      author: 'serverops-bot',
      createdAt: 'اليوم',
      commentsCount: 3,
      relatedServerId: 'srv-001',
    },
    {
      id: 41,
      number: 41,
      title: '[PERF] High Memory Utilization Spike during batch synchronization',
      body: 'Workers thread memory consumption exceeded 88% threshold.',
      state: 'closed',
      labels: [
        { name: 'performance', color: 'fbca04' },
        { name: 'resolved', color: '0e8a16' },
      ],
      author: 'serverops-bot',
      createdAt: 'أمس',
      commentsCount: 5,
      relatedServerId: 'srv-003',
    },
  ]);

  // AI Release Notes state
  const [releaseVersion, setReleaseVersion] = useState('v2.5.0');
  const [releaseNotesText, setReleaseNotesText] = useState('');
  const [isGeneratingReleaseNotes, setIsGeneratingReleaseNotes] = useState(false);

  // Fetch local git info on mount
  useEffect(() => {
    fetch('/api/github/git-info')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.branch) {
          setGitInfo(data);
          if (data.owner) setCustomUsername(data.owner);
          if (data.repoName) setCustomRepoName(data.repoName);
        }
      })
      .catch((err) => console.log('Git info fetch error:', err));
  }, []);

  // Copy helper
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Test PAT connection to GitHub
  const handleTestToken = async () => {
    if (!personalAccessToken.trim()) {
      setTokenTestResult({ success: false, error: 'الرجاء إدخال GitHub Personal Access Token أولاً' });
      return;
    }
    setIsTestingToken(true);
    setTokenTestResult(null);
    try {
      const res = await fetch('/api/github/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: personalAccessToken.trim(),
          owner: customUsername,
          repo: customRepoName,
        }),
      });
      const data = await res.json();
      setTokenTestResult(data);
    } catch (err: any) {
      setTokenTestResult({ success: false, error: err.message || 'فشل الاتصال بالخادم' });
    } finally {
      setIsTestingToken(false);
    }
  };

  // Push directly from server to GitHub
  const handlePushLive = async () => {
    if (!personalAccessToken.trim()) {
      setPushResult({ success: false, error: 'الرجاء إدخال GitHub Personal Access Token لإتمام عملية الرفع' });
      return;
    }
    setIsPushingLive(true);
    setPushResult(null);
    try {
      const res = await fetch('/api/github/sync-and-push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: personalAccessToken.trim(),
          targetBranch: targetPushBranch,
          force: allowForcePush,
          commitMessage: `feat: DevOps AI Intelligence Console sync to ${customUsername}/${customRepoName}`,
        }),
      });
      const data = await res.json();
      setPushResult(data);
      if (data.success) {
        // Refresh local git info
        fetch('/api/github/git-info')
          .then((r) => r.json())
          .then((d) => d && d.branch && setGitInfo(d))
          .catch(() => {});
      }
    } catch (err: any) {
      setPushResult({ success: false, error: err.message || 'فشل تنفيذ عملية الرفع إلى GitHub' });
    } finally {
      setIsPushingLive(false);
    }
  };

  // Trigger manual workflow run
  const handleTriggerWorkflow = () => {
    setIsDispatching(true);
    const newRunId = `run-${Date.now().toString().slice(-4)}`;
    const newRun: WorkflowRun = {
      id: newRunId,
      workflowName: 'CD Automated Deployment & Cloud Delivery',
      workflowFile: '.github/workflows/deploy.yml',
      event: 'workflow_dispatch',
      status: 'in_progress',
      conclusion: null,
      branch: gitInfo.branch,
      commitHash: gitInfo.latestCommit.hash.slice(0, 7),
      duration: 'جارٍ التنفيذ...',
      startedAt: 'الآن',
      steps: [
        { name: 'Checkout Code', status: 'running', duration: '2s' },
        { name: 'Setup Node.js 22', status: 'pending', duration: '-' },
        { name: 'Install Dependencies', status: 'pending', duration: '-' },
        { name: 'Production Build', status: 'pending', duration: '-' },
        { name: 'Notify SRE Console', status: 'pending', duration: '-' },
      ],
    };

    setWorkflows((prev) => [newRun, ...prev]);

    // Simulate step progression
    setTimeout(() => {
      setWorkflows((prev) =>
        prev.map((r) =>
          r.id === newRunId
            ? {
                ...r,
                steps: [
                  { name: 'Checkout Code', status: 'completed', duration: '3s' },
                  { name: 'Setup Node.js 22', status: 'running', duration: '3s' },
                  { name: 'Install Dependencies', status: 'pending', duration: '-' },
                  { name: 'Production Build', status: 'pending', duration: '-' },
                  { name: 'Notify SRE Console', status: 'pending', duration: '-' },
                ],
              }
            : r
        )
      );
    }, 1500);

    setTimeout(() => {
      setWorkflows((prev) =>
        prev.map((r) =>
          r.id === newRunId
            ? {
                ...r,
                status: 'completed',
                conclusion: 'success',
                duration: '48s',
                steps: [
                  { name: 'Checkout Code', status: 'completed', duration: '3s' },
                  { name: 'Setup Node.js 22', status: 'completed', duration: '4s' },
                  { name: 'Install Dependencies', status: 'completed', duration: '18s' },
                  { name: 'Production Build', status: 'completed', duration: '21s' },
                  { name: 'Notify SRE Console', status: 'completed', duration: '2s' },
                ],
              }
            : r
        )
      );
      setIsDispatching(false);
    }, 4500);
  };

  // Convert SRE incident to GitHub Issue
  const handleConvertIncidentToIssue = (incident: Incident) => {
    const newIssueNum = issues.length > 0 ? Math.max(...issues.map((i) => i.number)) + 1 : 1;
    const newIssue: GitHubIssue = {
      id: Date.now(),
      number: newIssueNum,
      title: `[INCIDENT-${incident.severity.toUpperCase()}] ${incident.code}: ${incident.message}`,
      body: `### SRE Incident Report
- **Server:** ${incident.serverName} (\`${incident.serverId}\`)
- **Severity:** ${incident.severity}
- **Timestamp:** ${incident.timestamp}
- **Status:** ${incident.resolved ? 'Resolved' : 'Active / Unresolved'}

#### Stack Trace & Telemetry:
\`\`\`
${incident.stackTrace || 'No stack trace provided'}
\`\`\`

*Reported automatically from ServerOps Enterprise Console.*`,
      state: incident.resolved ? 'closed' : 'open',
      labels: [
        { name: 'incident', color: 'b60205' },
        { name: `severity:${incident.severity}`, color: incident.severity === 'critical' ? 'd93f0b' : 'fbca04' },
        { name: 'sre', color: '0052cc' },
      ],
      author: 'serverops-bot',
      createdAt: 'الآن',
      commentsCount: 0,
      relatedServerId: incident.serverId,
    };

    setIssues((prev) => [newIssue, ...prev]);
    setActiveSubTab('issues');
  };

  // Generate AI Release Notes
  const handleGenerateReleaseNotes = async () => {
    setIsGeneratingReleaseNotes(true);
    try {
      const res = await fetch('/api/github/generate-release-notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          version: releaseVersion,
          deployments,
          incidents,
          repoName: customRepoName,
        }),
      });
      const data = await res.json();
      if (data && data.releaseNotes) {
        setReleaseNotesText(data.releaseNotes);
      }
    } catch (err) {
      console.error('Release notes generation error:', err);
    } finally {
      setIsGeneratingReleaseNotes(false);
    }
  };

  const fullRepoUrl = `https://github.com/${customUsername}/${customRepoName}`;

  return (
    <div className="space-y-6">
      {/* Top Banner: GitHub Repository Overview */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/60 border border-slate-800 rounded-2xl p-5 shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                <FolderGit2 className="w-5 h-5" />
              </span>
              <h3 className="text-lg font-extrabold text-white font-mono flex items-center gap-2">
                <span>{customUsername}</span>
                <span className="text-slate-500">/</span>
                <span className="text-indigo-400">{customRepoName}</span>
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                <span>مستودع Git مهيأ محلياً</span>
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                Public Repository
              </span>
            </div>
            <p className="text-xs text-slate-400">
              منصة إدارة مستودع GitHub، أتمتة مسارات CI/CD، مراجعة طلبات السحب (Pull Requests)، ومزامنة حوادث الخوادم التشغيلية تلقائياً.
            </p>
          </div>

          {/* Quick Metrics Badges */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <div className="px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center gap-1.5 text-slate-300">
              <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
              <span>الفرع: </span>
              <span className="text-indigo-400 font-bold">{gitInfo.branch}</span>
            </div>

            <div className="px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center gap-1.5 text-slate-300">
              <GitCommit className="w-3.5 h-3.5 text-emerald-400" />
              <span>SHA: </span>
              <span className="text-emerald-400 font-bold">{gitInfo.latestCommit.hash.slice(0, 7)}</span>
            </div>

            <div className="px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center gap-1.5 text-amber-300">
              <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
              <span>128 Stars</span>
            </div>

            <div className="px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center gap-1.5 text-sky-300">
              <GitFork className="w-3.5 h-3.5 text-sky-400" />
              <span>24 Forks</span>
            </div>

            <a
              href={fullRepoUrl}
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium flex items-center gap-1.5 transition-colors border border-slate-700"
            >
              <span>فتح على GitHub</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>
        </div>

        {/* GitHub Sub-navigation Tabs */}
        <div className="flex items-center gap-2 mt-5 pt-4 border-t border-slate-800/80 overflow-x-auto text-xs font-medium">
          <button
            onClick={() => setActiveSubTab('push_wizard')}
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeSubTab === 'push_wizard'
                ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>أوامر الرفع لـ GitHub (Push Wizard)</span>
          </button>

          <button
            onClick={() => setActiveSubTab('workflows')}
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeSubTab === 'workflows'
                ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Workflow className="w-3.5 h-3.5" />
            <span>مسارات CI/CD Actions ({workflows.length})</span>
          </button>

          <button
            onClick={() => setActiveSubTab('prs')}
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeSubTab === 'prs'
                ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <GitPullRequest className="w-3.5 h-3.5" />
            <span>طلبات السحب PRs ({pullRequests.length})</span>
          </button>

          <button
            onClick={() => setActiveSubTab('issues')}
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeSubTab === 'issues'
                ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>حوادث ومشاكل GitHub ({issues.length})</span>
          </button>

          <button
            onClick={() => setActiveSubTab('commits')}
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeSubTab === 'commits'
                ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <GitCommit className="w-3.5 h-3.5" />
            <span>شجرة الـ Commits</span>
          </button>

          <button
            onClick={() => setActiveSubTab('releases')}
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeSubTab === 'releases'
                ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Tag className="w-3.5 h-3.5" />
            <span>ملاحظات الإصدار بـ Gemini AI</span>
          </button>

          <button
            onClick={() => setActiveSubTab('webhooks')}
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-colors whitespace-nowrap ${
              activeSubTab === 'webhooks'
                ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>محاكي Webhooks</span>
          </button>
        </div>
      </div>

      {/* SUB-TAB 1: Push to GitHub Command Center */}
      {activeSubTab === 'push_wizard' && (
        <div className="space-y-6">
          {/* Direct 1-Click Server-to-GitHub Push & Connection Panel */}
          <div className="bg-gradient-to-br from-slate-900 via-indigo-950/40 to-slate-900 border-2 border-indigo-500/40 rounded-2xl p-6 shadow-xl space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-indigo-500/20 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-base font-extrabold text-white flex items-center gap-2">
                    <span>الربط المباشر والدفع إلى GitHub من السيرفر</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      Direct One-Click Push
                    </span>
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    اربط المستودع وادفع كامل الشيفرة البرمجية الحالية والتحديثات إلى <span className="text-indigo-400 font-mono font-bold">hamedonassar95/Devobs</span> مباشرة من هنا
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-indigo-300 font-mono bg-indigo-950/70 px-3 py-1.5 rounded-xl border border-indigo-800 flex items-center gap-1.5">
                  <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>https://github.com/hamedonassar95/Devobs</span>
                </span>
              </div>
            </div>

            {/* Instruction Callout */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white flex items-center gap-1.5">
                  <Key className="w-4 h-4 text-amber-400" />
                  <span>متطلبات المصادقة مع GitHub:</span>
                </span>
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo&description=Devobs-AI-Console"
                  target="_blank"
                  rel="noreferrer"
                  className="px-2.5 py-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600 text-indigo-300 hover:text-white font-semibold transition-colors flex items-center gap-1"
                >
                  <span>إنشاء Token جديد على GitHub (بصلاحية repo)</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <p className="text-slate-400 leading-relaxed">
                لكي يتمكن الخادم من الدفع إلى مستودعك الخاص دون الحاجة إلى تشغيل أوامر من جهازك، يحتاج GitHub إلى <strong className="text-slate-200">Personal Access Token (PAT)</strong> يمتلك صلاحية <code className="text-indigo-300 font-mono">repo</code> (أو صلاحية Contents: Read and write).
              </p>
            </div>

            {/* Token Input and Test Connection */}
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-500">
                    <Key className="w-4 h-4" />
                  </div>
                  <input
                    type={showToken ? 'text' : 'password'}
                    value={personalAccessToken}
                    onChange={(e) => setPersonalAccessToken(e.target.value)}
                    placeholder="الصق رمز GitHub Personal Access Token هنا (e.g. ghp_xxxxxxxxxxxxxx)"
                    className="w-full pl-10 pr-9 py-2.5 bg-slate-950 border border-slate-700 focus:border-indigo-500 rounded-xl text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none"
                    dir="ltr"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-500 hover:text-slate-300"
                  >
                    {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                <button
                  onClick={handleTestToken}
                  disabled={isTestingToken || !personalAccessToken.trim()}
                  className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-semibold text-xs rounded-xl border border-slate-700 transition-colors flex items-center justify-center gap-2 whitespace-nowrap"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isTestingToken ? 'animate-spin' : ''}`} />
                  <span>{isTestingToken ? 'جارٍ الفحص...' : 'فحص الاتصال والصلاحية'}</span>
                </button>
              </div>

              {/* Token Test Result Feedback */}
              {tokenTestResult && (
                <div
                  className={`p-3.5 rounded-xl border text-xs flex items-start gap-2.5 ${
                    tokenTestResult.success
                      ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                      : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
                  }`}
                >
                  {tokenTestResult.success ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                  )}
                  <div className="space-y-1">
                    {tokenTestResult.success ? (
                      <div>
                        <div className="font-bold text-white flex items-center gap-2">
                          <span>تم التحقق من الحساب بنجاح: @{tokenTestResult.user?.login}</span>
                          {tokenTestResult.canPush ? (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              صلاحية الرفع (Push) مفعلة
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              قراءة فقط - تأكد من إضافة صلاحية repo
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-emerald-400/80">
                          المستودع المستهدف: {tokenTestResult.repo?.full_name} | الفرع الافتراضي: {tokenTestResult.repo?.default_branch}
                        </p>
                      </div>
                    ) : (
                      <p className="font-medium">{tokenTestResult.error}</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Target Branch and Force Push Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-800/80">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>الفرع المستهدف للرفع (Target Branch):</span>
                  <span className="text-[10px] text-indigo-400 font-mono">HEAD:{targetPushBranch}</span>
                </label>
                <div className="flex gap-2">
                  <select
                    value={targetPushBranch}
                    onChange={(e) => setTargetPushBranch(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                  >
                    <option value="main">main (الفرع الرئيسي المباشر)</option>
                    <option value="feature/devops-ai-intelligence">feature/devops-ai-intelligence (فرع جديد لـ PR)</option>
                    <option value="devops-ai-console">devops-ai-console (فرع مستقل)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2 flex flex-col justify-end">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 select-none">
                  <input
                    type="checkbox"
                    checked={allowForcePush}
                    onChange={(e) => setAllowForcePush(e.target.checked)}
                    className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-950 w-4 h-4"
                  />
                  <span>السماح بالرفع الإجباري (Force Push --force)</span>
                </label>
                <p className="text-[10px] text-slate-400">
                  مفيد إذا كان المستودع البعيد يحتوي على تاريخ غير متزامن مع فرعك المحلي وتريد استبداله بتحديثات هذا المشروع.
                </p>
              </div>
            </div>

            {/* Push Button Trigger */}
            <div className="pt-2">
              <button
                onClick={handlePushLive}
                disabled={isPushingLive || !personalAccessToken.trim()}
                className="w-full py-3 px-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white font-bold text-sm rounded-xl shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center gap-2.5"
              >
                <UploadCloud className={`w-4 h-4 ${isPushingLive ? 'animate-bounce' : ''}`} />
                <span>
                  {isPushingLive
                    ? 'جارٍ رفع الشيفرة البرمجية والتحديثات إلى GitHub...'
                    : `دفع كامل المشروع إلى GitHub (https://github.com/${customUsername}/${customRepoName} @ ${targetPushBranch})`}
                </span>
              </button>
            </div>

            {/* Push Execution Result Banner */}
            {pushResult && (
              <div
                className={`p-4 rounded-xl border text-xs space-y-2 ${
                  pushResult.success
                    ? 'bg-emerald-950/50 border-emerald-500/50 text-emerald-200'
                    : 'bg-rose-950/50 border-rose-500/50 text-rose-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    {pushResult.success ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-rose-400" />
                    )}
                    <span>{pushResult.success ? 'تم الرفع إلى GitHub بنجاح!' : 'فشل عملية الرفع'}</span>
                  </div>

                  {pushResult.success && pushResult.repoUrl && (
                    <a
                      href={pushResult.repoUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors flex items-center gap-1.5"
                    >
                      <span>عرض الكود على GitHub</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>

                <p className="leading-relaxed">{pushResult.message || pushResult.error}</p>

                {pushResult.hint && (
                  <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-amber-300">
                    <strong>تلميح الحل: </strong>
                    {pushResult.hint}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Step 1: Customize your repository target */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-indigo-400" />
                  <span>دليل أوامر Git اليدوية البديلة (Manual CLI Alternative)</span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  أوامر سطر الأوامر لتشغيلها يدوياً على جهازك المحلي في حال أردت الرفع من حاسوبك
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] text-emerald-400 font-mono bg-emerald-950/50 px-2 py-1 rounded border border-emerald-800">
                  Git Initialized (Branch: main)
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  اسم المستخدم أو المؤسسة على GitHub (GitHub Username / Org):
                </label>
                <input
                  type="text"
                  value={customUsername}
                  onChange={(e) => setCustomUsername(e.target.value)}
                  placeholder="e.g. mohammadnassar"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  اسم المستودع المستهدف (Repository Name):
                </label>
                <input
                  type="text"
                  value={customRepoName}
                  onChange={(e) => setCustomRepoName(e.target.value)}
                  placeholder="e.g. serverops-console"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Step 2: Generated Command Blocks */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Method A: Standard Git Commands */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-[11px] font-bold flex items-center justify-center">
                    1
                  </span>
                  <h4 className="text-xs font-bold text-white">طريقة Git القياسية (Standard Git CLI)</h4>
                </div>
                <button
                  onClick={() =>
                    handleCopy(
                      `git remote add origin ${fullRepoUrl}.git\ngit branch -M main\ngit push -u origin main`,
                      'git_block'
                    )
                  }
                  className="px-2.5 py-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600 text-indigo-300 hover:text-white text-[11px] font-semibold transition-colors flex items-center gap-1"
                >
                  {copiedIndex === 'git_block' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedIndex === 'git_block' ? 'تم النسخ!' : 'نسخ الأوامر'}</span>
                </button>
              </div>

              <p className="text-[11px] text-slate-400">
                قم بتشغيل هذه الأوامر في سطر الأوامر (Terminal) داخل مجلد المشروع لربطه بمستودع GitHub ودفع كامل الملفات:
              </p>

              <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 font-mono text-[11px] text-slate-200 space-y-2 select-all overflow-x-auto" dir="ltr">
                <div className="text-slate-500"># 1. ربط المستودع البعيد بالرابط الخاص بك</div>
                <div className="text-indigo-300">git remote add origin {fullRepoUrl}.git</div>
                <div className="text-slate-500 mt-2"># 2. التأكد من اسم الفرع الرئيسي main</div>
                <div className="text-indigo-300">git branch -M main</div>
                <div className="text-slate-500 mt-2"># 3. رفع الشيفرة البرمجية بالكامل إلى GitHub</div>
                <div className="text-emerald-400 font-bold">git push -u origin main</div>
              </div>
            </div>

            {/* Method B: GitHub CLI (gh) */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-violet-600 text-white text-[11px] font-bold flex items-center justify-center">
                    2
                  </span>
                  <h4 className="text-xs font-bold text-white">عبر أداة GitHub الرسمية (GitHub CLI - gh)</h4>
                </div>
                <button
                  onClick={() =>
                    handleCopy(
                      `gh repo create ${customRepoName} --public --source=. --remote=origin --push`,
                      'gh_block'
                    )
                  }
                  className="px-2.5 py-1 rounded-lg bg-violet-600/30 hover:bg-violet-600 text-violet-300 hover:text-white text-[11px] font-semibold transition-colors flex items-center gap-1"
                >
                  {copiedIndex === 'gh_block' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedIndex === 'gh_block' ? 'تم النسخ!' : 'نسخ أمر gh'}</span>
                </button>
              </div>

              <p className="text-[11px] text-slate-400">
                إذا كانت لديك أداة `gh` مثبتة، يمكنك إنشاء المستودع ورفعه مباشرة بأمر واحد ذكي دون فتح المتصفح:
              </p>

              <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 font-mono text-[11px] text-slate-200 space-y-2 select-all overflow-x-auto" dir="ltr">
                <div className="text-slate-500"># ينشئ المستودع على حسابك، يربطه ويرفع الكود فوراً:</div>
                <div className="text-violet-300 font-bold">
                  gh repo create {customRepoName} --public --source=. --remote=origin --push
                </div>
              </div>

              <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
                <span className="font-semibold text-slate-300">ملاحظة أمنية:</span>
                <p>
                  ملف `.env` محمي تلقائياً ومستبعد في `.gitignore` لمنع تسريب أي مفاتيح سرية، بينما يتم رفع `.env.example` لتوثيق المتغيرات المطلوبة.
                </p>
              </div>
            </div>
          </div>

          {/* File Trees included in the GitHub Repo */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
            <h4 className="text-xs font-bold text-white flex items-center gap-2">
              <FileCode className="w-4 h-4 text-cyan-400" />
              <span>الملفات المجهزة والمفحوصة لمستودع GitHub (Repository Manifest)</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="text-slate-300">.github/workflows/ci.yml</span>
              </div>
              <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="text-slate-300">.github/workflows/deploy.yml</span>
              </div>
              <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="text-slate-300">README.md (التوثيق الكامل)</span>
              </div>
              <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="text-slate-300">CONTRIBUTING.md & LICENSE</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: Workflows & Actions CI/CD */}
      {activeSubTab === 'workflows' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <Workflow className="w-4 h-4 text-indigo-400" />
                <span>مسارات أتمتة البناء والنشر (GitHub Actions Workflows)</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                مراقبة حية لاختبارات الجودة وفحص TypeScript وبناء حزم الإنتاج
              </p>
            </div>

            <div className="flex items-center gap-3">
              <select
                value={dispatchEnv}
                onChange={(e) => setDispatchEnv(e.target.value as any)}
                className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white font-mono focus:outline-none"
              >
                <option value="production">البيئة: الإنتاج (production)</option>
                <option value="staging">البيئة: التجريبية (staging)</option>
              </select>

              <button
                onClick={handleTriggerWorkflow}
                disabled={isDispatching}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition-all shadow-md flex items-center gap-2"
              >
                <Play className={`w-3.5 h-3.5 ${isDispatching ? 'animate-spin' : ''}`} />
                <span>تشغيل مسار CD الآن</span>
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {workflows.map((wf) => (
              <div
                key={wf.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 hover:border-slate-700 transition-colors shadow-sm"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-3">
                    <span
                      className={`p-2 rounded-xl ${
                        wf.conclusion === 'success'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : wf.status === 'in_progress'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse'
                          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                      }`}
                    >
                      {wf.conclusion === 'success' ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : wf.status === 'in_progress' ? (
                        <RefreshCw className="w-5 h-5 animate-spin" />
                      ) : (
                        <XCircle className="w-5 h-5" />
                      )}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-bold text-white">{wf.workflowName}</h4>
                        <span className="font-mono text-[11px] text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                          {wf.workflowFile}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                        <span className="flex items-center gap-1 font-mono">
                          <GitBranch className="w-3 h-3 text-indigo-400" />
                          {wf.branch}
                        </span>
                        <span>·</span>
                        <span className="font-mono text-emerald-400">{wf.commitHash}</span>
                        <span>·</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-400" />
                          {wf.duration}
                        </span>
                        <span>·</span>
                        <span>{wf.startedAt}</span>
                      </div>
                    </div>
                  </div>

                  <span
                    className={`px-3 py-1 rounded-xl text-xs font-bold font-mono ${
                      wf.conclusion === 'success'
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                        : wf.status === 'in_progress'
                        ? 'bg-amber-950/80 text-amber-300 border border-amber-800'
                        : 'bg-rose-950/80 text-rose-300 border border-rose-800'
                    }`}
                  >
                    {wf.conclusion === 'success' ? 'Passed' : wf.status === 'in_progress' ? 'Running' : 'Failed'}
                  </span>
                </div>

                {/* Steps execution trace */}
                <div className="space-y-2">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    خطوات التنفيذ (Execution Steps):
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2 text-xs font-mono">
                    {wf.steps.map((st, i) => (
                      <div
                        key={i}
                        className={`p-2.5 rounded-xl border flex items-center justify-between gap-2 ${
                          st.status === 'completed'
                            ? 'bg-slate-950/90 border-slate-800 text-slate-300'
                            : st.status === 'running'
                            ? 'bg-amber-950/40 border-amber-500/40 text-amber-300 animate-pulse'
                            : 'bg-slate-950/40 border-slate-800/40 text-slate-600'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 truncate">
                          {st.status === 'completed' ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          ) : st.status === 'running' ? (
                            <RefreshCw className="w-3.5 h-3.5 text-amber-400 shrink-0 animate-spin" />
                          ) : (
                            <Clock className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                          )}
                          <span className="truncate">{st.name}</span>
                        </div>
                        <span className="text-[10px] text-slate-500 shrink-0">{st.duration}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SUB-TAB 3: Pull Requests */}
      {activeSubTab === 'prs' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <GitPullRequest className="w-4 h-4 text-indigo-400" />
                <span>طلبات السحب والمراجعة البرمجية (Pull Requests)</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                تتبع التغييرات وموافقة المراجعين وفحوصات الـ CI التلقائية قبل الدمج
              </p>
            </div>
            <span className="px-3 py-1 rounded-xl bg-slate-800 text-slate-300 text-xs font-mono border border-slate-700">
              {pullRequests.filter((p) => p.state === 'open').length} مفتوحة · {pullRequests.filter((p) => p.state === 'merged').length} مدمجة
            </span>
          </div>

          <div className="space-y-3">
            {pullRequests.map((pr) => (
              <div
                key={pr.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-4.5 hover:border-slate-700 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`p-1.5 rounded-lg ${
                        pr.state === 'merged'
                          ? 'bg-purple-500/20 text-purple-400'
                          : pr.state === 'open'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-rose-500/20 text-rose-400'
                      }`}
                    >
                      <GitPullRequest className="w-4 h-4" />
                    </span>
                    <h5 className="text-sm font-bold text-white font-mono">
                      #{pr.number} {pr.title}
                    </h5>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                    <span className="text-indigo-400">{pr.branch}</span>
                    <span>→</span>
                    <span className="text-slate-300">{pr.targetBranch}</span>
                    <span>·</span>
                    <span>بواسطة @{pr.author}</span>
                    <span>·</span>
                    <span className="text-emerald-400 font-bold">+{pr.additions}</span>
                    <span className="text-rose-400 font-bold">-{pr.deletions}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-1 rounded border border-emerald-800">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>CI Passed</span>
                  </span>
                  <span
                    className={`px-2.5 py-1 rounded-xl text-xs font-bold font-mono ${
                      pr.state === 'merged'
                        ? 'bg-purple-950/80 text-purple-300 border border-purple-800'
                        : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                    }`}
                  >
                    {pr.state === 'merged' ? 'Merged' : 'Open'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SUB-TAB 4: SRE Incidents to GitHub Issues */}
      {activeSubTab === 'issues' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>تزامن حوادث الخوادم مع GitHub Issues</span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  قم بتحويل أي عطل أو حادثة تشغيلية مباشرة إلى Issue موثق بتفاصيل الـ Stack Trace على GitHub
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">حوادث الخوادم النشطة ({incidents.length})</span>
              </div>
            </div>

            {/* Quick incident converter chips */}
            <div className="space-y-2 pt-2">
              <span className="text-xs font-semibold text-slate-300">
                اختر حادثة لتحويلها إلى GitHub Issue فوراً:
              </span>
              <div className="flex flex-wrap gap-2">
                {incidents.slice(0, 4).map((inc) => (
                  <button
                    key={inc.id}
                    onClick={() => handleConvertIncidentToIssue(inc)}
                    className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-700/80 text-xs text-slate-300 transition-colors flex items-center gap-2"
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        inc.severity === 'critical'
                          ? 'bg-rose-400'
                          : inc.severity === 'warning'
                          ? 'bg-amber-400'
                          : 'bg-sky-400'
                      }`}
                    />
                    <span className="font-mono text-white">{inc.code}</span>
                    <span className="text-slate-500">@{inc.serverName}</span>
                    <span className="text-indigo-400 font-semibold text-[11px]">+ فتح Issue</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Issues List */}
          <div className="space-y-3">
            {issues.map((iss) => (
              <div
                key={iss.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-4.5 space-y-3 hover:border-slate-700 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`p-1.5 rounded-lg ${
                          iss.state === 'open' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-purple-500/20 text-purple-400'
                        }`}
                      >
                        <AlertCircle className="w-4 h-4" />
                      </span>
                      <h5 className="text-sm font-bold text-white font-mono">
                        #{iss.number} {iss.title}
                      </h5>
                    </div>
                    <p className="text-xs text-slate-300 line-clamp-2 pr-6">{iss.body}</p>
                  </div>

                  <span
                    className={`px-2.5 py-1 rounded-xl text-xs font-bold font-mono shrink-0 ${
                      iss.state === 'open'
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                        : 'bg-purple-950/80 text-purple-300 border border-purple-800'
                    }`}
                  >
                    {iss.state === 'open' ? 'Open' : 'Closed'}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/60 text-xs">
                  {iss.labels.map((lb, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-950 border border-slate-700 text-slate-300"
                    >
                      {lb.name}
                    </span>
                  ))}
                  <span className="text-slate-500 text-[11px]">بواسطة @{iss.author} · {iss.createdAt}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SUB-TAB 5: Commits Tree */}
      {activeSubTab === 'commits' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <GitCommit className="w-4 h-4 text-emerald-400" />
                <span>شجرة الإيداعات البرمجية (Git Commits History)</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                تاريخ الشيفرة المصدرية على الفرع <span className="text-indigo-400 font-mono">main</span>
              </p>
            </div>
          </div>

          <div className="space-y-3 font-mono">
            <div className="p-4 bg-slate-950 rounded-xl border border-indigo-500/40 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 font-bold rounded">HEAD</span>
                  <span className="text-white font-bold text-sm">
                    {gitInfo.latestCommit.message}
                  </span>
                </div>
                <span className="text-xs text-emerald-400 font-bold">
                  {gitInfo.latestCommit.hash.slice(0, 7)}
                </span>
              </div>
              <div className="text-xs text-slate-400 flex items-center gap-3">
                <span>{gitInfo.latestCommit.author} ({gitInfo.latestCommit.email})</span>
                <span>·</span>
                <span>{new Date(gitInfo.latestCommit.date).toLocaleString('ar')}</span>
              </div>
            </div>

            {deployments.map((dep, idx) => (
              <div key={idx} className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <GitCommit className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-slate-200">{dep.changeLog}</span>
                  </div>
                  <span className="text-slate-400 font-bold">{dep.commitHash}</span>
                </div>
                <div className="text-[11px] text-slate-500 flex items-center gap-2">
                  <span>@{dep.author}</span>
                  <span>·</span>
                  <span>{dep.timestamp}</span>
                  <span>·</span>
                  <span className="text-indigo-400">{dep.version}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SUB-TAB 6: AI Release Notes Generator */}
      {activeSubTab === 'releases' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span>مُولّد ملاحظات الإصدار التلقائي بالذكاء الاصطناعي (Gemini 3.8 Flash)</span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                يقوم بتحليل آخر عمليات النشر والحوادث المحلولة وتوليد Release Notes احترافية جاهزة للنشر على GitHub
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={releaseVersion}
                onChange={(e) => setReleaseVersion(e.target.value)}
                placeholder="v2.5.0"
                className="w-24 px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-xl text-xs text-white font-mono focus:outline-none"
              />
              <button
                onClick={handleGenerateReleaseNotes}
                disabled={isGeneratingReleaseNotes}
                className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-md"
              >
                <Sparkles className={`w-3.5 h-3.5 ${isGeneratingReleaseNotes ? 'animate-spin' : ''}`} />
                <span>{isGeneratingReleaseNotes ? 'جارٍ التوليد...' : 'توليد Release Notes'}</span>
              </button>
            </div>
          </div>

          {releaseNotesText ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">معاينة Markdown للإصدار:</span>
                <button
                  onClick={() => handleCopy(releaseNotesText, 'rel_notes')}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 flex items-center gap-1"
                >
                  {copiedIndex === 'rel_notes' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedIndex === 'rel_notes' ? 'تم النسخ!' : 'نسخ التقرير'}</span>
                </button>
              </div>
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-200 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed" dir="ltr">
                {releaseNotesText}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800/80 text-xs text-slate-400 space-y-2">
              <Sparkles className="w-6 h-6 text-indigo-400 mx-auto" />
              <p>اضغط على "توليد Release Notes" لإنشاء تقرير إصدار كامل ومفصل بناءً على بيانات الخوادم الحالية.</p>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 7: Webhook Simulator */}
      {activeSubTab === 'webhooks' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div>
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <Radio className="w-4 h-4 text-emerald-400" />
              <span>محاكي إشارات GitHub Webhooks اللحظية</span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              اختبار استقبال أحداث `push` و `workflow_run` و `pull_request` وتأثيرها على استقرار الخوادم
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              onClick={() => alert('تم استقبال إشارة Webhook من نوع [push:main] بنجاح وتحديث سجل الإيداعات.')}
              className="p-3 bg-slate-950 hover:bg-slate-800 rounded-xl border border-slate-800 text-left transition-colors space-y-1"
            >
              <div className="text-xs font-bold text-indigo-400 font-mono">event: push</div>
              <div className="text-[11px] text-slate-400">إرسال كود جديد لفرع main</div>
            </button>

            <button
              onClick={() => alert('تم استقبال إشارة Webhook من نوع [workflow_run:completed] وتحديث سجل CI/CD.')}
              className="p-3 bg-slate-950 hover:bg-slate-800 rounded-xl border border-slate-800 text-left transition-colors space-y-1"
            >
              <div className="text-xs font-bold text-emerald-400 font-mono">event: workflow_run</div>
              <div className="text-[11px] text-slate-400">اكتمال مسار النشر بنجاح</div>
            </button>

            <button
              onClick={() => alert('تم استقبال إشارة Webhook من نوع [pull_request:opened] وإنشاء فحص آلي.')}
              className="p-3 bg-slate-950 hover:bg-slate-800 rounded-xl border border-slate-800 text-left transition-colors space-y-1"
            >
              <div className="text-xs font-bold text-violet-400 font-mono">event: pull_request</div>
              <div className="text-[11px] text-slate-400">طلب سحب جديد جاهز للمراجعة</div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
