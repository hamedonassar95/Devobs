import type Keycloak from 'keycloak-js';
import type { KeycloakConfig } from 'keycloak-js';

export const DEVOBS_CALLBACK = '/auth/devobs/callback';
export type DevobsAuthStatus = 'disabled' | 'signed_out' | 'busy' | 'signed_in' | 'unavailable';
export type AuthSettings = { enabled?: string; issuer?: string; redirectUri?: string };
type Adapter = Pick<Keycloak, 'init' | 'login' | 'clearToken' | 'isTokenExpired'
  | 'authenticated' | 'token' | 'onTokenExpired' | 'onAuthLogout'>;
type Dependencies = {
  origin: string;
  loadAdapter: (config: KeycloakConfig) => Promise<Adapter>;
  scrubCallback: () => void;
  initTimeoutMs?: number;
};

function configuration(settings: AuthSettings, origin: string) {
  if (settings.enabled !== 'true') return null;
  try {
    const issuer = new URL(settings.issuer || '');
    const page = new URL(origin);
    if (!/^https:\/\/devobs-keycloak-hosted(?:-[a-z0-9-]+)?\.onrender\.com\/realms\/devobs-hosted$/.test(issuer.href)
      || page.origin !== origin || page.protocol !== 'https:' || page.port
      || !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(page.hostname)
      || /(?:^|\.)(?:localhost|local|internal|test|invalid|example)$/.test(page.hostname)
      || settings.redirectUri !== `${origin}${DEVOBS_CALLBACK}`) return null;
    return { url: issuer.origin, realm: 'devobs-hosted', clientId: 'devobs-hosted-public',
      issuer: issuer.href, redirectUri: settings.redirectUri };
  } catch { return null; }
}

/** Optional Devobs session, independent of Google/Firebase and diagnostics.
 * Official adapter owns nonce/state, PKCE S256 and code exchange:
 * https://www.keycloak.org/securing-apps/javascript-adapter
 */
export function createDevobsAuth(settings: AuthSettings, deps: Dependencies) {
  const config = configuration(settings, deps.origin);
  let status: DevobsAuthStatus = config ? 'signed_out' : settings.enabled === 'true' ? 'unavailable' : 'disabled';
  let adapter: Adapter | null = null;
  let initializing: Promise<Adapter> | null = null;
  let generation = 0;
  let callbackConsumed = false;
  const listeners = new Set<() => void>();
  function publish(next: DevobsAuthStatus) {
    status = next;
    listeners.forEach(listener => listener());
  }
  async function clear(client: Adapter | null) {
    try { await client?.clearToken(); } catch { /* Access stays denied by status. */ }
  }
  async function signOut() {
    generation++;
    const old = adapter;
    adapter = null;
    initializing = null;
    publish(config ? 'signed_out' : status);
    await clear(old);
  }
  async function initialize(): Promise<Adapter> {
    if (!config) throw new Error('devobs_auth_unavailable');
    if (!initializing) {
      const current = generation;
      let timer: ReturnType<typeof setTimeout> | undefined;
      const attempt = (async () => {
        const client = await deps.loadAdapter({ url: config.url, realm: config.realm, clientId: config.clientId });
        if (current !== generation) { await clear(client); throw new Error('devobs_auth_unavailable'); }
        adapter = client;
        client.onTokenExpired = () => { if (adapter === client) void signOut(); };
        client.onAuthLogout = () => { if (adapter === client) publish('signed_out'); };
        await client.init({
          redirectUri: config.redirectUri, flow: 'standard', pkceMethod: 'S256',
          responseMode: 'fragment', useNonce: true, checkLoginIframe: false,
          enableLogging: false, scope: 'devobs.read',
        });
        // A late import/exchange must not restore a cancelled/timed-out session.
        if (current !== generation) { await clear(client); throw new Error('devobs_auth_unavailable'); }
        return client;
      })();
      initializing = Promise.race([attempt, new Promise<Adapter>((_, reject) => {
          timer = setTimeout(() => reject(new Error('devobs_auth_unavailable')), deps.initTimeoutMs ?? 15000);
      })]).finally(() => { clearTimeout(timer); });
    }
    return initializing;
  }
  async function fail() {
    generation++;
    const old = adapter;
    adapter = null;
    initializing = null;
    await clear(old);
    publish(config ? 'unavailable' : status);
  }
  function usable(client: Adapter) {
    try { return client.authenticated === true && typeof client.token === 'string'
      && client.token.length > 0 && client.token.length <= 8192 && !client.isTokenExpired(5); }
    catch { return false; }
  }
  return {
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    getSnapshot: () => status,
    isConfigured: () => config !== null,
    async signIn() {
      if (!config || status === 'busy') return;
      const current = generation;
      publish('busy');
      try {
        const client = await initialize();
        if (current !== generation) return;
        await client.login({ redirectUri: config.redirectUri, scope: 'devobs.read' });
      } catch { if (current === generation) await fail(); }
    },
    async handleCallback(href: string) {
      let url: URL;
      try { url = new URL(href); } catch { return; }
      if (url.pathname !== DEVOBS_CALLBACK) return;
      const current = generation;
      try {
        if (callbackConsumed || initializing) throw new Error('devobs_auth_unavailable');
        callbackConsumed = true;
        const params = new URLSearchParams(url.hash.slice(1));
        const allowed = new Set(['code', 'state', 'session_state', 'iss', 'error', 'error_description', 'error_uri']);
        if (!config || url.origin !== deps.origin || url.search || url.hash.length > 16384
          || [...params.keys()].some(key => !allowed.has(key) || params.getAll(key).length !== 1)
          || !params.get('state') || params.get('iss') !== config.issuer
          || (params.has('code') === params.has('error'))
          || (params.has('code') && !params.get('code'))) throw new Error('devobs_auth_unavailable');
        // The adapter retries authentication_expired errors automatically.
        // Preserve explicit-only login by stopping before adapter initialization.
        if (params.has('error')) throw new Error('devobs_auth_unavailable');
        publish('busy');
        const client = await initialize();
        if (current !== generation) return;
        if (!usable(client)) throw new Error('devobs_auth_unavailable');
        publish('signed_in');
      } catch { if (current === generation) await fail(); }
      finally { deps.scrubCallback(); }
    },
    /** Memory only; callers must still pass the upstream API's JWT/scope/tenant checks. */
    getAccessToken() {
      if (status !== 'signed_in' || !adapter) return null;
      if (!usable(adapter)) { void signOut(); return null; }
      return adapter.token!;
    },
    signOut,
  };
}
