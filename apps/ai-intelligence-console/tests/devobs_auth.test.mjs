import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createDevobsAuth, DEVOBS_CALLBACK } from '../src/services/devobsAuth.ts';

const origin = 'https://console.onrender.com';
const issuer = 'https://devobs-keycloak-hosted.onrender.com/realms/devobs-hosted';
const settings = { enabled: 'true', issuer, redirectUri: `${origin}${DEVOBS_CALLBACK}` };
const response = (extra = '') => `${settings.redirectUri}#code=synthetic-code&state=synthetic-state&iss=${encodeURIComponent(issuer)}${extra}`;

function fixture(options = {}) {
  const calls = { load: [], init: [], login: [], clear: 0, scrub: 0 };
  const adapter = {
    authenticated: true, token: 'synthetic-access',
    init: async value => { calls.init.push(value); return true; },
    login: async value => { calls.login.push(value); },
    clearToken: async () => { calls.clear++; adapter.authenticated = false; adapter.token = undefined; },
    isTokenExpired: () => false,
    ...options.adapter,
  };
  const auth = createDevobsAuth(options.settings ?? settings, {
    origin, initTimeoutMs: options.timeout ?? 1000,
    loadAdapter: async config => { calls.load.push(config); return adapter; },
    scrubCallback: () => { calls.scrub++; },
  });
  return { auth, adapter, calls };
}

test('disabled/malformed configuration never loads an adapter, signs in or exposes tokens', async () => {
  const invalid = [{}, { ...settings, enabled: 'false' },
    ...['http://devobs-keycloak-hosted.onrender.com/realms/devobs-hosted',
      `${issuer}?key=synthetic-marker`, `${issuer}/`, issuer.replace('devobs-hosted', 'other'),
      issuer.replace('.onrender.com', '.onrender.com.attacker.net')].map(issuer => ({ ...settings, issuer })),
    ...['https://other.onrender.com/auth/devobs/callback', `${settings.redirectUri}?return=elsewhere`,
      `${settings.redirectUri}#fragment`, `${origin}/callback`].map(redirectUri => ({ ...settings, redirectUri }))];
  for (const config of invalid) {
    const { auth, calls } = fixture({ settings: config });
    await auth.signIn();
    await auth.handleCallback(response());
    assert.equal(calls.load.length, 0);
    assert.equal(auth.getAccessToken(), null);
    assert.equal(calls.scrub, 1);
  }
});

test('only explicit sign-in initializes the official standard S256 adapter without silent SSO', async () => {
  const { auth, calls } = fixture();
  assert.equal(auth.getSnapshot(), 'signed_out');
  assert.equal(calls.load.length, 0);
  await auth.handleCallback(origin);
  assert.equal(calls.load.length, 0);
  await auth.signIn();
  assert.deepEqual(calls.load, [{ url: new URL(issuer).origin, realm: 'devobs-hosted', clientId: 'devobs-hosted-public' }]);
  assert.deepEqual(calls.init, [{ redirectUri: settings.redirectUri, flow: 'standard', pkceMethod: 'S256',
    responseMode: 'fragment', useNonce: true, checkLoginIframe: false, enableLogging: false, scope: 'devobs.read' }]);
  assert.deepEqual(calls.login, [{ redirectUri: settings.redirectUri, scope: 'devobs.read' }]);
  assert.equal(auth.getAccessToken(), null);
});

test('callback consumes the adapter result before exposing memory-only access and scrubs URL', async () => {
  const { auth, calls } = fixture();
  const states = [];
  const unsubscribe = auth.subscribe(() => states.push(auth.getSnapshot()));
  await auth.handleCallback(response());
  assert.equal(auth.getSnapshot(), 'signed_in');
  assert.equal(auth.getAccessToken(), 'synthetic-access');
  assert.equal(calls.scrub, 1);
  assert.equal(calls.login.length, 0);
  assert.deepEqual(states, ['busy', 'signed_in']);
  unsubscribe();
  await auth.signOut();
  assert.equal(auth.getAccessToken(), null);
  assert.equal(auth.getSnapshot(), 'signed_out');
  assert.equal(calls.clear, 1);
  assert.deepEqual(states, ['busy', 'signed_in']);
});

test('wrong issuer, duplicate/missing/foreign fields and query-mode callbacks fail before adapter calls', async () => {
  const invalid = [response('&state=duplicate'), response('&code=duplicate'), response('&unknown=marker'),
    response().replace(encodeURIComponent(issuer), encodeURIComponent('https://other.onrender.com')),
    response().replace('state=synthetic-state&', ''), response().replace('code=synthetic-code&', ''),
    response().replace('code=synthetic-code', 'code='), response('&error=access_denied'),
    response().replace('#', '?'), response('&padding=' + 'x'.repeat(16385)),
    response().replace(origin, 'https://other.onrender.com')];
  for (const href of invalid) {
    const { auth, calls } = fixture();
    await auth.handleCallback(href);
    assert.equal(auth.getSnapshot(), 'unavailable');
    assert.equal(calls.load.length, 0);
    assert.equal(auth.getAccessToken(), null);
    assert.equal(calls.scrub, 1);
  }
});

test('adapter-rejected state/replay, provider errors and expired tokens remain denied', async () => {
  for (const adapter of [
    { init: async () => { throw new Error('synthetic-private-provider-details'); } },
    { authenticated: false }, { isTokenExpired: () => true }, { token: undefined },
  ]) {
    const { auth, calls } = fixture({ adapter });
    await auth.handleCallback(response());
    assert.equal(auth.getSnapshot(), 'unavailable');
    assert.equal(auth.getAccessToken(), null);
    assert.equal(calls.clear, 1);
    assert.equal(calls.scrub, 1);
  }
  for (const error of ['error=access_denied', 'error=login_required&error_description=authentication_expired']) {
    const { auth, calls } = fixture();
    await auth.handleCallback(response().replace('code=synthetic-code', error));
    assert.equal(auth.getSnapshot(), 'unavailable');
    assert.equal(calls.load.length, 0);
    assert.equal(calls.init.length, 0);
    assert.equal(calls.login.length, 0);
    assert.equal(calls.scrub, 1);
  }
});

test('expiry clears access without refreshing or requesting analysis', async () => {
  const { auth, adapter, calls } = fixture();
  await auth.handleCallback(response());
  adapter.onTokenExpired();
  assert.equal(auth.getAccessToken(), null);
  assert.equal(auth.getSnapshot(), 'signed_out');
  assert.equal(calls.clear, 1);
  assert.equal(calls.login.length, 0);
});

test('a callback can be consumed once per page, including after an earlier failure', async () => {
  for (const first of [response(), response('&state=duplicate')]) {
    const { auth, calls } = fixture();
    await auth.handleCallback(first);
    await auth.handleCallback(response());
    assert.equal(auth.getSnapshot(), 'unavailable');
    assert.equal(auth.getAccessToken(), null);
    assert.ok(calls.init.length <= 1);
    assert.equal(calls.scrub, 2);
  }
});

test('timed-out initialization cannot restore a late session', async () => {
  let resolve;
  const { auth, adapter, calls } = fixture({ timeout: 5, adapter: {
    init: () => new Promise(done => { resolve = done; }),
  } });
  await auth.handleCallback(response());
  assert.equal(auth.getSnapshot(), 'unavailable');
  adapter.authenticated = true;
  adapter.token = 'synthetic-late-access';
  resolve(true);
  await new Promise(done => setTimeout(done, 0));
  assert.equal(auth.getAccessToken(), null);
  assert.equal(adapter.token, undefined);
  assert.ok(calls.clear >= 2);
  assert.equal(calls.scrub, 1);
});

test('local sign-out during a pending callback cannot restore its late token', async () => {
  let resolve, started;
  const ready = new Promise(done => { started = done; });
  const { auth, adapter } = fixture({ adapter: {
    init: () => new Promise(done => { resolve = done; started(); }),
  } });
  const callback = auth.handleCallback(response());
  await ready;
  await auth.signOut();
  adapter.authenticated = true;
  adapter.token = 'synthetic-late-access';
  resolve(true);
  await callback;
  assert.equal(auth.getSnapshot(), 'signed_out');
  assert.equal(auth.getAccessToken(), null);
  assert.equal(adapter.token, undefined);
});

test('a stalled lazy import times out before any adapter initialization', async () => {
  let resolve;
  const { adapter } = fixture();
  let scrubbed = false;
  const auth = createDevobsAuth(settings, {
    origin, initTimeoutMs: 5, loadAdapter: () => new Promise(done => { resolve = done; }),
    scrubCallback: () => { scrubbed = true; },
  });
  await auth.handleCallback(response());
  assert.equal(auth.getSnapshot(), 'unavailable');
  assert.equal(scrubbed, true);
  resolve(adapter);
  await new Promise(done => setTimeout(done, 0));
  assert.equal(auth.getAccessToken(), null);
  assert.equal(adapter.token, undefined);
});
