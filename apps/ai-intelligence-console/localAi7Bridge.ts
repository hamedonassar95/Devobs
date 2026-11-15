import type { RequestHandler } from 'express';

/**
 * Local-only, optional bridge to the existing AI-7 snapshot API.
 * Never accepts a user-controlled URL and never forwards raw incidents or logs.
 */
const SOURCE = 'http://127.0.0.1:8765/api/v1/intelligence';
const MAX_BYTES = 65_536;
const STAGES = ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7'] as const;

type Data = Record<string, unknown>;
function object(value: unknown): value is Data {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function count(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0 || value > 10_000_000) {
    throw new Error('invalid_local_ai7_count');
  }
  return value;
}
function normalize(raw: unknown) {
  if (!object(raw) || raw.schema_version !== 1 || raw.status !== 'local_snapshot'
      || !object(raw.summary) || !object(raw.pipeline)
      || raw.pipeline.id !== 'devobs-ai-local-1-7'
      || raw.pipeline.mode !== 'local_advisory_only'
      || !Array.isArray(raw.pipeline.stages) || raw.pipeline.stages.length !== 7) {
    throw new Error('invalid_local_ai7_schema');
  }
  const summary = {
    event_count: count(raw.summary.event_count),
    log_cluster_count: count(raw.summary.log_cluster_count),
    recommendation_count: count(raw.summary.recommendation_count),
    anomaly_candidate_count: count(raw.summary.anomaly_candidate_count),
  };
  const stages = raw.pipeline.stages.map((step: unknown, index: number) => {
    if (!object(step) || step.id !== STAGES[index] || typeof step.status !== 'string'
        || !/^[a-z_]{1,32}$/.test(step.status)) {
      throw new Error('invalid_local_ai7_stage');
    }
    return { id: STAGES[index], status: step.status, count: count(step.count) };
  });
  return { source: 'local_ai7_snapshot', status: 'local_snapshot',
    mode: 'local_advisory_only', read_only: true, summary, stages };
}

async function readBounded(response: Response): Promise<unknown> {
  if (!response.ok || response.status !== 200
      || !response.headers.get('content-type')?.toLowerCase().startsWith('application/json')
      || !response.body) {
    throw new Error('invalid_local_ai7_response');
  }
  const declared = response.headers.get('content-length');
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > MAX_BYTES)) {
    throw new Error('local_ai7_response_too_large');
  }
  const reader = response.body.getReader();
  const buffers: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > MAX_BYTES) throw new Error('local_ai7_response_too_large');
      buffers.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  return JSON.parse(Buffer.concat(buffers.map(chunk => Buffer.from(chunk))).toString('utf8'));
}

export function createLocalAi7Handler({
  enabled = false,
  bindHost = '127.0.0.1',
  consolePort = 3000,
  fetchImpl = fetch,
}: {
  enabled?: boolean;
  bindHost?: string;
  consolePort?: number;
  fetchImpl?: typeof fetch;
} = {}): RequestHandler {
  return async (req, res) => {
    res.set({ 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer' });
    if (!enabled || bindHost !== '127.0.0.1') {
      res.status(503).json({ error: 'local_ai7_disabled' });
      return;
    }
    const expectedHost = `127.0.0.1:${consolePort}`;
    if (req.get('host') !== expectedHost
        || (req.get('origin') && req.get('origin') !== `http://${expectedHost}`)
        || (req.get('sec-fetch-site') && !['none', 'same-origin'].includes(req.get('sec-fetch-site')!))
        || req.socket.localAddress !== '127.0.0.1') {
      res.status(403).json({ error: 'local_ai7_denied' });
      return;
    }
    try {
      const upstream = await fetchImpl(SOURCE, {
        method: 'GET', redirect: 'error', cache: 'no-store',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(2500),
      });
      res.status(200).json(normalize(await readBounded(upstream)));
    } catch {
      // No private upstream contents, URLs, tokens, or logs in the response.
      res.status(503).json({ error: 'local_ai7_unavailable' });
    }
  };
}
