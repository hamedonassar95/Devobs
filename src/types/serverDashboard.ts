export type ServerType = 'api' | 'database' | 'worker' | 'cache' | 'storage';
export type ServerStatus = 'healthy' | 'warning' | 'critical' | 'maintenance';
export type Environment = 'production' | 'staging' | 'development';
export type IncidentSeverity = 'critical' | 'warning' | 'info';
export type DeploymentStatus = 'successful' | 'failed' | 'in_progress' | 'rolled_back';

export interface Server {
  id: string;
  name: string;
  ip: string;
  type: ServerType;
  region: string;
  environment: Environment;
  status: ServerStatus;
  cpu: number;
  memory: number;
  disk: number;
  networkMbps: number;
  uptimeDays: number;
  lastPing: string;
  os: string;
}

export interface Incident {
  id: string;
  serverId: string;
  serverName: string;
  severity: IncidentSeverity;
  code: string;
  message: string;
  stackTrace: string;
  timestamp: string;
  resolved: boolean;
  resolvedAt?: string;
  aiAnalysis?: string;
}

export interface Deployment {
  id: string;
  version: string;
  commitHash: string;
  serviceName: string;
  branch: string;
  author: string;
  timestamp: string;
  status: DeploymentStatus;
  durationSeconds: number;
  changeLog: string;
  targetServers: string[];
}

export interface MetricPoint {
  time: string;
  cpu: number;
  memory: number;
  requests: number;
  latencyMs: number;
}
