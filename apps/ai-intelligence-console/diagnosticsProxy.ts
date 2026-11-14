/** Opt-in proxy; the upstream Devobs API owns OIDC, tenant checks and AI budget. */
import type { RequestHandler } from 'express';

const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
const BEARER = /^Bearer [A-Za-z0-9._~-]{1,8192}$/;
const MAX_REPLY_BYTES = 32768;
const SECRETS = /Authorization\s*:\s*Bearer\s+(?!<redacted>|redacted\b)\S+|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\b["']?\s*[:=]\s*["']?(?!<redacted>|redacted\b)[^\s"'`,;]{8,}|\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?):\/\/[^/\s:@]+:[^@\s/]+@|\b(?:gh[pousr]_|github_pat_|sk-|AIza|sb_secret_)[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b/i;
type Binding = { tenantId: string; projectId: string; serviceId: string };

function configuration(settings: NodeJS.ProcessEnv) {
  if (settings.DEVOBS_DIAGNOSTICS_ENABLED !== 'true') return null;
  try {
    const url = new URL(settings.DEVOBS_API_BASE_URL || '');
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash
      || url.pathname !== '/' || url.port || !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(url.hostname)
      || /(?:^|\.)(?:localhost|local|internal|invalid|test|example)$/.test(url.hostname)) return null;
    const raw = settings.DEVOBS_SERVICE_BINDINGS_JSON || '';
    if (Buffer.byteLength(raw) > 32768) return null;
    const bindings = JSON.parse(raw);
    if (!bindings || Array.isArray(bindings) || typeof bindings !== 'object'
      || Object.keys(bindings).length < 1 || Object.keys(bindings).length > 100) return null;
    for (const [key, value] of Object.entries(bindings)) {
      const item = value as Binding;
      if (!ID.test(key) || !item || typeof item !== 'object' || Array.isArray(item)
        || Object.keys(item).sort().join(',') !== 'projectId,serviceId,tenantId'
        || ![item.tenantId, item.projectId, item.serviceId].every(v => typeof v === 'string' && ID.test(v))) return null;
    }
    return { origin: url.origin, bindings: bindings as Record<string, Binding> };
  } catch { return null; }
}

async function boundedReply(response: Response) {
  if (!response.body) throw new Error('invalid_reply');
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_REPLY_BYTES) throw new Error('invalid_reply');
      chunks.push(value);
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } finally { await reader.cancel(); }
}

function validReply(value: any): boolean {
  return value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',') === 'confidence,diagnosis,latency_ms,model,recommendation,severity'
    && ['diagnosis', 'recommendation'].every(key => typeof value[key] === 'string' && value[key].trim()
      && value[key].length <= 1200 && !SECRETS.test(value[key]))
    && ['low', 'medium', 'high', 'critical', 'unknown'].includes(value.severity)
    && ['low', 'medium', 'high'].includes(value.confidence)
    && typeof value.model === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value.model)
    && Number.isSafeInteger(value.latency_ms) && value.latency_ms >= 0;
}

export function createDiagnosticsHandler(settings: NodeJS.ProcessEnv, fetchImpl: typeof fetch = fetch): RequestHandler {
  const config = configuration(settings);
  let windowStarted = Date.now();
  let calls = 0;
  let active = 0;
  return async (req, res) => {
    res.set('Cache-Control', 'no-store');
    const fail = (status: number, error: string) => res.status(status).json({ error });
    if (!config) { fail(503, 'diagnostics_not_configured'); return; }
    const authorization = req.get('Authorization') || '';
    if (!BEARER.test(authorization)) { fail(401, 'access_token_required'); return; }
    const body = req.body;
    if (!body || typeof body !== 'object' || Array.isArray(body)
      || Object.keys(body).sort().join(',') !== 'dataRedacted,errorLog,serverId'
      || body.dataRedacted !== true || typeof body.serverId !== 'string'
      || typeof body.errorLog !== 'string' || !body.errorLog.trim()
      || Buffer.byteLength(body.errorLog) > 8192 || /[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(body.errorLog)
      || SECRETS.test(body.errorLog)) { fail(400, 'reviewed_log_required'); return; }
    if (!Object.hasOwn(config.bindings, body.serverId)) { fail(403, 'service_not_registered'); return; }
    if (Date.now() - windowStarted >= 60000) { windowStarted = Date.now(); calls = 0; }
    if (calls >= 5 || active >= 2) { fail(429, 'diagnostics_rate_limited'); return; }
    const binding = config.bindings[body.serverId];
    calls++; active++;
    try {
      const response = await fetchImpl(`${config.origin}/v1/tenants/${binding.tenantId}/projects/${binding.projectId}/services/${binding.serviceId}/diagnostics`, {
        method: 'POST', redirect: 'error', signal: AbortSignal.timeout(22000),
        headers: { Authorization: authorization, 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ error_log: body.errorLog, data_redacted: true }),
      });
      if (response.status !== 200) {
        await response.body?.cancel();
        fail([401, 403, 429, 503].includes(response.status) ? response.status : 502, 'diagnostics_unavailable'); return;
      }
      const result = await boundedReply(response);
      if (!validReply(result)) throw new Error('invalid_reply');
      res.json({ analysis: `تحليل استشاري — يحتاج إلى مراجعة بشرية\n\n${result.diagnosis}\n\nالتوصية: ${result.recommendation}\nالخطورة: ${result.severity} · الثقة: ${result.confidence}\nالنموذج: ${result.model}` });
    } catch { fail(502, 'diagnostics_unavailable'); }
    finally { active--; }
  };
}
