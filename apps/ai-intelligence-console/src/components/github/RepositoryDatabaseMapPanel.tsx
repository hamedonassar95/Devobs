import { useState } from 'react';
import { AlertTriangle, Database, ExternalLink, Info } from 'lucide-react';
import inventorySource from '../../../../../docs/architecture/repository_database_map.json?raw';

const STATUSES = ['VERIFIED', 'UNVERIFIED', 'BLOCKED', 'PLANNED'] as const;
type Status = (typeof STATUSES)[number];
type Repo = { id: string; name: string; url: string; ref: string; identity_status: Status };
type Resource = Record<string, unknown> & { id: string; kind: string; status: Status };
type Relationship = { from: string; to: string; type: string; status: Status };
type Component = { id: string; repository_id: string; path: string; status: Status };
type Inventory = {
  map_format: 'devobs.repository-database-map';
  schema_version: 1;
  generated_at: string;
  canonical_repository: 'hamedonassar95/Devobs';
  status_values: Status[];
  baseline: { source_repositories_are_read_only: true; live_database_access_performed: false };
  repositories: Repo[];
  components: Component[];
  database_resources: Resource[];
  relationships: Relationship[];
};
type GithubObservation = {
  repository: string | null;
  status: 'OBSERVED' | 'PENDING' | 'UNVERIFIED';
  branch: string | null;
  commitSha: string | null;
  ciConclusion: string | null;
  runStatus: string | null;
  observedAt: string | null;
  cached: boolean;
  reason: string | null;
};
type GithubCheckState = { loading: boolean; result: GithubObservation | null };
const CI_CONCLUSIONS = new Set(['success', 'failure', 'cancelled', 'timed_out', 'neutral',
  'skipped', 'action_required', 'stale', 'startup_failure', 'pending']);
const CI_RUN_STATUSES = new Set(['completed', 'in_progress', 'queued', 'waiting', 'pending', 'requested']);
const CI_REASONS = new Set(['disabled', 'non_loopback_bind', 'request_denied', 'no_runs',
  'no_matching_ci_run', 'rate_limited', 'timeout', 'upstream_unavailable',
  'invalid_response', 'method_not_allowed', 'repository_not_allowed', 'public_visibility_unverified']);

const REQUIRED_REPOS = [
  ['devobs', 'hamedonassar95/Devobs'],
  ['ops', 'hamedonassar95/ops'],
  ['ai_intelligence_source', 'hamedonassar95/DevObs-ai-Intelligence-'],
  ['devobs_saas', 'hamedonassar95/devobs-saas'],
] as const;
const REQUIRED_RESOURCES = [
  'legacy_firebase_source', 'canonical_firestore_policy', 'render_ai_staging_service',
  'render_ai_staging_postgres', 'saas_postgres', 'saas_neon_candidate', 'phone_repair_supabase',
] as const;
const RESOURCE_TITLES: Record<(typeof REQUIRED_RESOURCES)[number], string> = {
  legacy_firebase_source: 'Legacy Firebase / Firestore',
  canonical_firestore_policy: 'Canonical Firestore policy',
  render_ai_staging_service: 'Render AI staging service',
  render_ai_staging_postgres: 'Render staging PostgreSQL',
  saas_postgres: 'SaaS PostgreSQL declaration',
  saas_neon_candidate: 'Potential SaaS database target',
  phone_repair_supabase: 'Phone Repair / Supabase boundary',
};
const SAFE_FIELDS: Record<string, Array<[string, string]>> = {
  legacy_firebase_source: [['project_id', 'Project ID'], ['firestore_database_id', 'Firestore database ID']],
  canonical_firestore_policy: [['rules_policy', 'Source rules policy'], ['runtime_enabled_by_default', 'Enabled by default']],
  render_ai_staging_service: [['resource_name', 'Service'], ['plan', 'Plan in checkpoint'], ['auto_deploy', 'Auto-deploy in checkpoint'], ['last_recorded_deploy_state', 'Last recorded deployment state']],
  render_ai_staging_postgres: [['provider_resource_name', 'Provider resource'], ['logical_database_name', 'Logical database'], ['engine', 'Engine'], ['plan', 'Plan in checkpoint'], ['free_expiry', 'Recorded free expiry']],
  saas_postgres: [['engine', 'Declared engine']],
  saas_neon_candidate: [['provider', 'Planned provider']],
  phone_repair_supabase: [['provider', 'Reported provider family']],
};
const BADGE_STYLE: Record<Status, string> = {
  VERIFIED: 'border-emerald-700 bg-emerald-950 text-emerald-200',
  UNVERIFIED: 'border-amber-700 bg-amber-950 text-amber-200',
  BLOCKED: 'border-rose-700 bg-rose-950 text-rose-200',
  PLANNED: 'border-sky-700 bg-sky-950 text-sky-200',
};
const SENSITIVE_DISPLAY_TEXT = /(?::\/\/|@|-----BEGIN|(?:api[_ -]?key|secret|token|password|credential|bearer)|[A-Za-z0-9]{32,})/i;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const isStatus = (value: unknown): value is Status =>
  typeof value === 'string' && STATUSES.includes(value as Status);
const isDate = (value: unknown): value is string => {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
};

function isSafeRepo(value: unknown): value is Repo {
  if (!isRecord(value) || typeof value.id !== 'string' || typeof value.name !== 'string' ||
      !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(value.name) ||
      typeof value.ref !== 'string' || !/^[a-f0-9]{40}$/.test(value.ref) ||
      !isStatus(value.identity_status) || typeof value.url !== 'string') return false;
  try {
    const url = new URL(value.url);
    return url.origin === 'https://github.com' && url.pathname === `/${value.name}` &&
      !url.username && !url.password && !url.search && !url.hash;
  } catch { return false; }
}

export function validateRepositoryDatabaseInventory(value: unknown): Inventory | null {
  if (!isRecord(value) || value.map_format !== 'devobs.repository-database-map' ||
      value.schema_version !== 1 || !isDate(value.generated_at) ||
      value.canonical_repository !== 'hamedonassar95/Devobs' ||
      !isRecord(value.baseline) || value.baseline.source_repositories_are_read_only !== true ||
      value.baseline.live_database_access_performed !== false ||
      !Array.isArray(value.status_values) || !Array.isArray(value.repositories) ||
      !Array.isArray(value.components) || !Array.isArray(value.database_resources) ||
      !Array.isArray(value.relationships)) return null;

  const statuses = value.status_values;
  if (statuses.length !== STATUSES.length || !STATUSES.every((status) => statuses.includes(status))) return null;
  const repos = value.repositories;
  if (repos.length !== REQUIRED_REPOS.length || !repos.every(isSafeRepo) ||
      new Set(repos.map((repo) => repo.id)).size !== repos.length ||
      !REQUIRED_REPOS.every(([id, name]) => repos.some((repo) => repo.id === id && repo.name === name))) return null;

  const repoIds = new Set(repos.map((repo) => repo.id));
  const components = value.components;
  if (!components.every((item) => isRecord(item) && typeof item.id === 'string' &&
      typeof item.repository_id === 'string' && repoIds.has(item.repository_id) &&
      typeof item.path === 'string' && isStatus(item.status)) ||
      !components.some((item) => isRecord(item) && item.id === 'devobs_console')) return null;
  const componentIds = new Set(components.map((item) => (item as Record<string, unknown>).id as string));

  const rawResources = value.database_resources;
  if (rawResources.length !== REQUIRED_RESOURCES.length || !rawResources.every((item) =>
      isRecord(item) && typeof item.id === 'string' && typeof item.kind === 'string' &&
      item.kind.length > 0 && isStatus(item.status)) ||
      new Set(rawResources.map((item) => (item as Record<string, unknown>).id)).size !== rawResources.length ||
      !REQUIRED_RESOURCES.every((id) => rawResources.some((item) => isRecord(item) && item.id === id))) return null;
  const resources = rawResources as Resource[];
  if (!resources.every((resource) => (SAFE_FIELDS[resource.id] ?? []).every(([key]) => {
    const field = resource[key];
    return field === undefined || typeof field === 'boolean' ||
      (typeof field === 'string' && field.length <= 120 && !SENSITIVE_DISPLAY_TEXT.test(field));
  }))) return null;
  const nodes = new Set([...repoIds, ...componentIds, ...resources.map((item) => item.id)]);
  const edges = value.relationships;
  if (!edges.every((item) => isRecord(item) && typeof item.from === 'string' && nodes.has(item.from) &&
      typeof item.to === 'string' && nodes.has(item.to) && typeof item.type === 'string' && isStatus(item.status))) return null;

  const getResource = (id: string) => resources.find((item) => item.id === id);
  const getEdge = (from: string, to: string, type: string) => edges.find((item) =>
    isRecord(item) && item.from === from && item.to === to && item.type === type);
  const firebase = getResource('legacy_firebase_source');
  const saas = getResource('saas_postgres');
  if (!firebase || firebase.evidence_classification !== 'VERIFIED SOURCE LINK' ||
      typeof firebase.project_id !== 'string' || typeof firebase.firestore_database_id !== 'string' ||
      !isStatus(firebase.live_access_status) || !isStatus(saas?.physical_provider) ||
      typeof getResource('render_ai_staging_postgres')?.logical_database_name !== 'string' ||
      !isStatus(getResource('phone_repair_supabase')?.attachment_to_devobs) ||
      !isStatus(getEdge('render_ai_staging_service', 'render_ai_staging_postgres', 'application_database_attachment')?.status) ||
      !isStatus(getEdge('devobs_saas', 'saas_postgres', 'declared_application_database')?.status)) return null;
  return value as unknown as Inventory;
}

function parseInventory(source: string): unknown {
  try { return JSON.parse(source) as unknown; } catch { return null; }
}
const canonicalInventory = parseInventory(inventorySource);

function Badge({ status }: { status: Status }) {
  return <span aria-label={`Inventory status: ${status}`} className={`inline-flex shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-bold ${BADGE_STYLE[status]}`}>{status}</span>;
}

function edgeStatus(data: Inventory, from: string, to: string, type: string): Status | null {
  const edge = data.relationships.find((item) => item.from === from && item.to === to && item.type === type);
  return edge?.status ?? null;
}

function connection(data: Inventory, resource: Resource): [string, Status] | null {
  if (resource.id === 'legacy_firebase_source' && isStatus(resource.live_access_status)) return ['Live access', resource.live_access_status];
  if (resource.id === 'render_ai_staging_postgres') {
    const status = edgeStatus(data, 'render_ai_staging_service', resource.id, 'application_database_attachment');
    if (status) return ['Service-to-database attachment', status];
  }
  if (resource.id === 'saas_postgres' && isStatus(resource.physical_provider)) return ['Physical provider / live target', resource.physical_provider];
  if (resource.id === 'phone_repair_supabase' && isStatus(resource.attachment_to_devobs)) return ['Attachment to Devobs', resource.attachment_to_devobs];
  return null;
}

export function RepositoryDatabaseMapPanel({ inventory = canonicalInventory }: { inventory?: unknown }) {
  const [githubChecks, setGithubChecks] = useState<Record<string, GithubCheckState>>({});
  const data = validateRepositoryDatabaseInventory(inventory);
  if (!data) return (
    <section role="alert" aria-labelledby="repository-database-map-error" className="rounded-2xl border border-rose-700 bg-rose-950/60 p-5 text-rose-100">
      <h2 id="repository-database-map-error" className="flex items-center gap-2 text-sm font-bold"><AlertTriangle aria-hidden="true" className="h-4 w-4 shrink-0" />Repository and database inventory unavailable</h2>
      <p className="mt-2 text-sm">The build-time map is missing or invalid. No topology data is displayed.</p>
    </section>
  );

  const checkGithubCi = async (repo: Repo) => {
    setGithubChecks(previous => ({ ...previous, [repo.id]: { loading: true, result: null } }));
    try {
      const query = new URLSearchParams({ repository: repo.name });
      const response = await fetch(`/api/github/public-ci-status?${query.toString()}`, {
        method: 'GET', credentials: 'omit', cache: 'no-store', redirect: 'error',
        referrerPolicy: 'no-referrer', signal: AbortSignal.timeout(7_000),
        headers: { Accept: 'application/json' },
      });
      const raw: unknown = await response.json();
      const result = validateGithubObservation(raw, repo.name);
      if (!result || (!response.ok && result.status !== 'UNVERIFIED')) throw new Error('invalid_status');
      setGithubChecks(previous => ({ ...previous, [repo.id]: { loading: false, result } }));
    } catch {
      setGithubChecks(previous => ({ ...previous, [repo.id]: {
        loading: false,
        result: { repository: repo.name, status: 'UNVERIFIED', branch: null, commitSha: null,
          ciConclusion: null, runStatus: null, observedAt: null, cached: false, reason: 'upstream_unavailable' },
      } }));
    }
  };

  return (
    <section id="github-repository-database-map" aria-labelledby="repository-database-map-title" className="min-w-0 space-y-5">
      <header className="rounded-2xl border border-slate-700 bg-slate-900 p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h2 id="repository-database-map-title" className="flex items-center gap-2 text-base font-bold text-white sm:text-lg"><Database aria-hidden="true" className="h-5 w-5 shrink-0 text-cyan-300" />Repository &amp; Database Map</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">Verified source evidence is not verified live connectivity. The dated topology is a checked-in snapshot and makes no database or provider requests; public GitHub CI is a separate point-in-time check only after you press a button.</p>
          </div>
          <span role="note" className="inline-flex w-fit shrink-0 items-center gap-2 rounded-lg border border-amber-700 bg-amber-950/70 px-3 py-2 text-xs font-semibold text-amber-100"><Info aria-hidden="true" className="h-4 w-4 shrink-0" />Not real-time · {data.generated_at}</span>
        </div>
      </header>

      <section aria-labelledby="repository-map-heading" className="space-y-3">
        <div className="flex items-center justify-between gap-2"><h3 id="repository-map-heading" className="text-sm font-bold text-white">Repositories</h3><span className="text-xs text-slate-400">Verified source evidence</span></div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {data.repositories.map((repo) => <article key={repo.id} className="min-w-0 rounded-xl border border-slate-700 bg-slate-900 p-4">
            <div className="flex min-w-0 items-start justify-between gap-2"><h4 className="min-w-0 break-words text-sm font-semibold text-white">{repo.name}</h4><Badge status={repo.identity_status} /></div>
            <a href={repo.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex min-w-0 items-center gap-1.5 break-all text-xs text-cyan-300 underline decoration-cyan-700 underline-offset-2 hover:text-cyan-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">Open repository <ExternalLink aria-hidden="true" className="h-3.5 w-3.5 shrink-0" /></a>
            <p className="mt-2 text-[11px] text-slate-400">Source snapshot</p><code className="block break-all text-[10px] leading-5 text-slate-300">{repo.ref}</code>
            <div className="mt-3 border-t border-slate-700 pt-3">
              <button type="button" onClick={() => void checkGithubCi(repo)} disabled={githubChecks[repo.id]?.loading}
                className="rounded-lg border border-cyan-700 bg-cyan-950/70 px-3 py-2 text-xs font-semibold text-cyan-100 hover:bg-cyan-900 disabled:cursor-wait disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">
                {githubChecks[repo.id]?.loading ? 'Checking GitHub CI…' : 'Check GitHub CI'}
              </button>
              <div role="status" aria-live="polite" className="mt-2 space-y-1 break-words text-[11px] text-slate-300">
                {githubChecks[repo.id]?.result ? <GithubStatusDetails result={githubChecks[repo.id].result!} /> :
                  <p>UNVERIFIED · Not checked in this session.</p>}
              </div>
            </div>
          </article>)}
        </div>
      </section>

      <section aria-labelledby="database-map-heading" className="space-y-3">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between"><h3 id="database-map-heading" className="text-sm font-bold text-white">Database resources and relationships</h3><span className="text-xs text-slate-400">Verified live connectivity: none established by this inventory</span></div>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {data.database_resources.map((resource) => {
            const details = SAFE_FIELDS[resource.id] ?? [];
            const linkStatus = resource.id === 'saas_postgres' ? edgeStatus(data, 'devobs_saas', resource.id, 'declared_application_database') : null;
            const link = connection(data, resource);
            return <article key={resource.id} className="min-w-0 rounded-xl border border-slate-700 bg-slate-900 p-4">
              <div className="flex min-w-0 flex-wrap items-start justify-between gap-2"><h4 className="min-w-0 break-words text-sm font-semibold text-white">{RESOURCE_TITLES[resource.id as keyof typeof RESOURCE_TITLES]}</h4><Badge status={resource.status} /></div>
              <dl className="mt-3 grid grid-cols-1 gap-x-3 gap-y-2 text-xs sm:grid-cols-2">
                {details.map(([key, label]) => {
                  const value = resource[key];
                  return (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') ? <div key={key} className="min-w-0"><dt className="text-slate-400">{label}</dt><dd className="mt-0.5 break-all text-slate-200">{String(value)}</dd></div> : null;
                })}
                {resource.id === 'legacy_firebase_source' && <div className="min-w-0 sm:col-span-2"><dt className="text-slate-400">Evidence classification</dt><dd className="mt-0.5 break-words text-slate-200">{String(resource.evidence_classification)}</dd></div>}
                {linkStatus && <div className="min-w-0"><dt className="text-slate-400">Declared relationship</dt><dd className="mt-0.5"><Badge status={linkStatus} /></dd></div>}
              </dl>
              {link && <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-700 pt-3"><span className="text-xs text-slate-400">{link[0]}</span><Badge status={link[1]} /></div>}
            </article>;
          })}
        </div>
      </section>

      <p role="note" className="rounded-xl border border-slate-700 bg-slate-950 p-4 text-xs leading-5 text-slate-300">Firebase remains disabled by default in the console, and canonical Firestore rules remain deny-all. Legacy rule text and live database contents are not loaded into this panel.</p>
    </section>
  );
}

function validateGithubObservation(value: unknown, repository: string): GithubObservation | null {
  if (!isRecord(value) || value.repository !== repository ||
      !['OBSERVED', 'PENDING', 'UNVERIFIED'].includes(String(value.status)) ||
      ![null, 'main'].includes(value.branch as null | string) ||
      !(value.commitSha === null || (typeof value.commitSha === 'string' && /^[a-f0-9]{40}$/.test(value.commitSha))) ||
      !(value.ciConclusion === null || (typeof value.ciConclusion === 'string' && CI_CONCLUSIONS.has(value.ciConclusion))) ||
      !(value.runStatus === null || (typeof value.runStatus === 'string' && CI_RUN_STATUSES.has(value.runStatus))) ||
      !(value.observedAt === null || (typeof value.observedAt === 'string' && Number.isFinite(Date.parse(value.observedAt)) &&
        new Date(value.observedAt).toISOString() === value.observedAt)) ||
      typeof value.cached !== 'boolean' ||
      !(value.reason === null || (typeof value.reason === 'string' && CI_REASONS.has(value.reason)))) return null;
  const result = value as unknown as GithubObservation;
  const complete = result.branch === 'main' && result.commitSha !== null && result.observedAt !== null;
  if (result.status === 'OBSERVED' && (!complete || result.runStatus !== 'completed' ||
      result.ciConclusion === null || result.ciConclusion === 'pending' || result.reason !== null)) return null;
  if (result.status === 'PENDING' && (!complete || !['in_progress', 'queued', 'waiting', 'pending', 'requested'].includes(result.runStatus ?? '') ||
      result.ciConclusion !== 'pending' || result.reason !== null)) return null;
  if (result.status === 'UNVERIFIED' && (result.ciConclusion !== null || result.reason === null)) return null;
  return result;
}

function GithubStatusDetails({ result }: { result: GithubObservation }) {
  const reasons: Record<string, string> = {
    disabled: 'Server integration is disabled.',
    non_loopback_bind: 'Read-only status is limited to the local console.',
    request_denied: 'Local request was rejected.',
    no_runs: 'No matching CI run was found.',
    no_matching_ci_run: 'The latest run does not match the observed branch commit.',
    rate_limited: 'GitHub anonymous rate limit reached; try again later.',
    timeout: 'GitHub request timed out.',
    upstream_unavailable: 'GitHub status is unavailable.',
    invalid_response: 'GitHub response could not be verified.',
    method_not_allowed: 'Only a GET status request is allowed.',
    repository_not_allowed: 'Repository is not allowlisted.',
    public_visibility_unverified: 'Public visibility is not verified; no GitHub status request was made.',
  };
  const conclusion = result.status === 'PENDING' ? 'pending' : result.ciConclusion;
  return <>
    <p><strong>Status:</strong> {result.status === 'UNVERIFIED' ? 'UNVERIFIED' : `CI ${conclusion}`}</p>
    {result.branch && <p><strong>Observed branch:</strong> {result.branch}</p>}
    {result.commitSha && <p className="break-all"><strong>Branch commit:</strong> {result.commitSha}</p>}
    {result.status !== 'UNVERIFIED' && <p><strong>Run state:</strong> {result.runStatus}</p>}
    {result.observedAt && <p><strong>GitHub observation:</strong> <time dateTime={result.observedAt}>{result.observedAt}</time>{result.cached ? ' · cached observation' : ' · fresh request'}</p>}
    {result.reason && <p>{reasons[result.reason] ?? 'Status not verified.'}</p>}
  </>;
}
