import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import { Buffer } from 'node:buffer';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config();

const app = express();
const port = parseInt(process.env.PORT || '3000', 10);

app.use(express.json({ limit: '32kb', strict: true }));

// Initialize Google GenAI client (Server-side only)
const apiKey = process.env.GEMINI_API_KEY;
const ai = apiKey
  ? new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    })
  : null;

const identifierPattern = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
const recentDiagnosisRequests: number[] = [];
let diagnosesInFlight = 0;

function readServiceBindings(): Record<string, { tenantId: string; projectId: string; serviceId: string }> | null {
  const raw = process.env.DEVOBS_SERVICE_BINDINGS_JSON;
  if (!raw || raw.length > 16_384) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    const bindings = Object.create(null) as Record<string, { tenantId: string; projectId: string; serviceId: string }>;
    for (const [serverId, value] of Object.entries(parsed)) {
      if (!identifierPattern.test(serverId) || !value || typeof value !== 'object' || Array.isArray(value)) return null;
      const binding = value as Record<string, unknown>;
      if (Object.keys(binding).sort().join(',') !== 'projectId,serviceId,tenantId'
        || typeof binding.tenantId !== 'string' || !identifierPattern.test(binding.tenantId)
        || typeof binding.projectId !== 'string' || !identifierPattern.test(binding.projectId)
        || typeof binding.serviceId !== 'string' || !identifierPattern.test(binding.serviceId)) return null;
      bindings[serverId] = {
        tenantId: binding.tenantId as string,
        projectId: binding.projectId as string,
        serviceId: binding.serviceId as string,
      };
    }
    return Object.keys(bindings).length ? bindings : null;
  } catch {
    return null;
  }
}

function makeErrorLog(incident: unknown): string | null {
  if (!incident || typeof incident !== 'object' || Array.isArray(incident)) return null;
  const value = incident as Record<string, unknown>;
  const allowedKeys = ['code', 'message', 'severity', 'stackTrace'];
  if (Object.keys(value).some((key) => !allowedKeys.includes(key))) return null;
  if (typeof value.message !== 'string' || value.message.length < 1 || value.message.length > 4096) return null;
  if (value.code !== undefined && (typeof value.code !== 'string' || value.code.length > 128)) return null;
  if (value.severity !== undefined && !['critical', 'warning', 'info'].includes(String(value.severity))) return null;
  if (value.stackTrace !== undefined && (typeof value.stackTrace !== 'string' || value.stackTrace.length > 4096)) return null;
  const fields = [
    value.code ? `error_code: ${value.code}` : '',
    value.severity ? `severity: ${value.severity}` : '',
    `message: ${value.message}`,
    value.stackTrace ? `stack_trace: ${value.stackTrace}` : '',
  ].filter(Boolean);
  const errorLog = fields.join('\n');
  return Buffer.byteLength(errorLog, 'utf8') <= 8192 ? errorLog : null;
}

// Proxy only the minimum redacted incident fields to the authenticated Devobs API.
// The browser supplies its short-lived user access token; it is never persisted or logged here.
app.post('/api/ai/analyze-incident', async (req, res) => {
  res.set('Cache-Control', 'no-store');
  if (process.env.DEVOBS_DIAGNOSTICS_ENABLED !== 'true') {
    return res.status(503).json({ error: 'devobs_integration_not_enabled' });
  }
  const authorization = req.get('Authorization') || '';
  const bearer = authorization.startsWith('Bearer ') ? authorization.slice(7) : '';
  if (bearer.length < 40 || bearer.length > 8192 || bearer.split('.').length !== 3 || !/^[\x21-\x7E]+$/.test(bearer)) {
    return res.status(401).json({ error: 'missing_or_invalid_access_token' });
  }
  if (!req.body || Object.keys(req.body).sort().join(',') !== 'dataRedacted,incident,serverId'
    || req.body.dataRedacted !== true) return res.status(400).json({ error: 'redaction_confirmation_required' });

  const serverId = req.body?.serverId;
  const errorLog = makeErrorLog(req.body?.incident);
  if (typeof serverId !== 'string' || !identifierPattern.test(serverId) || !errorLog) {
    return res.status(400).json({ error: 'invalid_incident_request' });
  }

  const bindings = readServiceBindings();
  const binding = bindings?.[serverId];
  const baseUrl = process.env.DEVOBS_API_BASE_URL;
  if (!binding || !baseUrl) return res.status(503).json({ error: 'devobs_integration_not_configured' });

  let apiOrigin: string;
  try {
    const parsed = new URL(baseUrl);
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.search || parsed.hash || parsed.pathname !== '/') {
      return res.status(503).json({ error: 'devobs_integration_not_configured' });
    }
    apiOrigin = parsed.origin;
  } catch {
    return res.status(503).json({ error: 'devobs_integration_not_configured' });
  }

  const now = Date.now();
  while (recentDiagnosisRequests.length && recentDiagnosisRequests[0] <= now - 60_000) recentDiagnosisRequests.shift();
  if (recentDiagnosisRequests.length >= 5) {
    res.set('Retry-After', String(Math.max(1, Math.ceil((recentDiagnosisRequests[0] + 60_000 - now) / 1000))));
    return res.status(429).json({ error: 'rate_limited' });
  }
  if (diagnosesInFlight >= 2) return res.status(503).json({ error: 'diagnostics_busy' });
  recentDiagnosisRequests.push(now);
  diagnosesInFlight += 1;

  try {
    const endpoint = new URL(
      `/v1/tenants/${binding.tenantId}/projects/${binding.projectId}/services/${binding.serviceId}/diagnostics`,
      apiOrigin,
    );
    const upstream = await fetch(endpoint, {
      method: 'POST',
      redirect: 'error',
      signal: AbortSignal.timeout(22_000),
      headers: {
        Authorization: `Bearer ${bearer}`,
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ error_log: errorLog, data_redacted: true }),
    });

    if (!upstream.ok) {
      const status = [400, 401, 403, 429].includes(upstream.status) ? upstream.status : 503;
      const errors: Record<number, string> = {
        400: 'diagnosis_input_rejected',
        401: 'invalid_access_token',
        403: 'service_access_denied',
        429: 'rate_limited',
        503: 'diagnostics_unavailable',
      };
      const retryAfter = upstream.headers.get('Retry-After');
      if (status === 429 && retryAfter && /^\d{1,4}$/.test(retryAfter)) res.set('Retry-After', retryAfter);
      return res.status(status).json({ error: errors[status] || 'diagnostics_unavailable' });
    }

    const rawResponse = await upstream.text();
    if (Buffer.byteLength(rawResponse, 'utf8') > 16_384) return res.status(503).json({ error: 'invalid_diagnostics_response' });
    const result: unknown = JSON.parse(rawResponse);
    if (!result || typeof result !== 'object' || Array.isArray(result)) return res.status(503).json({ error: 'invalid_diagnostics_response' });
    const diagnosis = result as Record<string, unknown>;
    if (typeof diagnosis.diagnosis !== 'string' || diagnosis.diagnosis.length < 1 || diagnosis.diagnosis.length > 1200
      || typeof diagnosis.recommendation !== 'string' || diagnosis.recommendation.length < 1 || diagnosis.recommendation.length > 1200
      || !['low', 'medium', 'high', 'critical', 'unknown'].includes(String(diagnosis.severity))
      || !['low', 'medium', 'high'].includes(String(diagnosis.confidence))
      || typeof diagnosis.model !== 'string' || diagnosis.model.length < 1 || diagnosis.model.length > 128
      || typeof diagnosis.latency_ms !== 'number' || !Number.isSafeInteger(diagnosis.latency_ms) || diagnosis.latency_ms < 0) {
      return res.status(503).json({ error: 'invalid_diagnostics_response' });
    }
    const analysis = [
      `التشخيص: ${diagnosis.diagnosis}`,
      `التوصية: ${diagnosis.recommendation}`,
      `الخطورة: ${diagnosis.severity} · الثقة: ${diagnosis.confidence}`,
      `النموذج: ${diagnosis.model} · زمن المعالجة: ${diagnosis.latency_ms} ms`,
      'هذه توصية استشارية؛ تحقّق منها يدويًا قبل أي تغيير.',
    ].join('\n\n');
    return res.json({ analysis });
  } catch {
    return res.status(503).json({ error: 'devobs_api_unavailable' });
  } finally {
    diagnosesInFlight -= 1;
  }
});

// Route 2: Generate Infrastructure Health Audit Report
app.post('/api/ai/generate-audit-report', async (req, res) => {
  try {
    const { servers, incidents, deployments, systemStats } = req.body;

    if (!ai) {
      return res.status(200).json({
        report: `## تقرير فحص البنية التحتية الدوري (محلي)
- إجمالي الخوادم المسجلة: ${servers?.length || 0}
- الحوادث المفتوحة: ${incidents?.filter((i: any) => !i.resolved).length || 0}
- التوصية العامة: يُنصح بربط مفتاح Gemini للحصول على تدقيق معمق لسلامة البنية التحتية وتنبؤات بأعطال الأنظمة.`,
      });
    }

    const prompt = `قم بإعداد تقرير تدقيق هندسي دوري وشامل (Infrastructure Health & Reliability Audit Report) لحالة مجموعة الخوادم والأنظمة باللغة العربية.

البيانات الإحصائية الحالية:
- إجمالي الخوادم: ${servers?.length}
- الخوادم السليمة: ${servers?.filter((s: any) => s.status === 'healthy').length}
- الخوادم التي بها تحذيرات: ${servers?.filter((s: any) => s.status === 'warning').length}
- الخوادم المتعطلة أو الحرجة: ${servers?.filter((s: any) => s.status === 'critical').length}

بيانات الخوادم:
${JSON.stringify(servers?.map((s: any) => ({ name: s.name, type: s.type, status: s.status, cpu: s.cpu, memory: s.memory, region: s.region })), null, 2)}

الحوادث النشطة والأخيرة:
${JSON.stringify(incidents?.slice(0, 8), null, 2)}

آخر عمليات النشر البرمجي:
${JSON.stringify(deployments?.slice(0, 5), null, 2)}

نسق التقرير بتنسيق Markdown احترافي يتضمن:
- 📊 **الملخص التنفيذي لحالة المنظومة (Executive Summary)**
- ⚠️ **أبرز نقاط الضعف ونقاط الاختناق المحتملة (Identified Bottlenecks & Risks)**
- 🚀 **تقييم موثوقية عمليات النشر واستقرار الإصدارات (Deployment Reliability)**
- 💡 **خارطة طريق التوصيات الهندسية ذات الأولوية (Actionable Recommendations)**`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        systemInstruction: 'أنت مهندس موثوقية بنية تحتية سحابية يقدم تقارير تنفيذية عالية الجودة باللغة العربية.',
      },
    });

    res.json({ report: response.text });
  } catch (error: any) {
    console.error('Audit report error:', error);
    res.status(500).json({
      error: error.message || 'فشل في توليد تقرير التدقيق بالذكاء الاصطناعي',
    });
  }
});

// Setup Vite middleware in dev or static files in production
async function startServer() {
  if (process.env.NODE_ENV === 'production') {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  } else {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(port, '0.0.0.0', () => {
    console.log(`Server listening on http://0.0.0.0:${port}`);
  });
}

startServer();
