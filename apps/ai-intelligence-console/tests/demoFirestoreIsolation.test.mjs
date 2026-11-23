import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const APP_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const FIREBASE_FLAGS = [false, true];
const contexts = new Map();

async function loadAppWithFirebaseFlag(enabled) {
  const facadeImports = [];
  const persistenceCalls = [];
  const spyKey = `__devobsDemoFirestoreSpy_${enabled ? 'enabled' : 'disabled'}`;
  globalThis[spyKey] = persistenceCalls;

  const firestoreSpyModule = '\0devobs-demo-firestore-spy';
  const sessionStubModule = '\0devobs-demo-session-stub';
  const plugin = {
    name: 'demo-firestore-isolation-test-boundary',
    enforce: 'pre',
    resolveId(source, importer) {
      const normalizedSource = source.replaceAll('\\', '/');
      if (/(?:^|\/)firebaseFirestore(?:Facade)?(?:\.[cm]?[jt]sx?)?$/.test(normalizedSource)) {
        facadeImports.push({ source, importer });
        return firestoreSpyModule;
      }
      if (source === './components/dashboard/DevobsSession') {
        return sessionStubModule;
      }
      if (source.startsWith('firebase/')) {
        throw new Error('real_firebase_sdk_import_blocked_in_demo_isolation_test');
      }
      return null;
    },
    load(id) {
      if (id === sessionStubModule) {
        return 'export const DevobsSession = () => null;';
      }
      if (id === firestoreSpyModule) {
        const spy = `globalThis[${JSON.stringify(spyKey)}].push`;
        return [
          `const record = (method) => ${spy}({ method });`,
          "export const subscribeToServers = (...args) => { record('subscribeToServers'); return () => {}; };",
          "export const subscribeToIncidents = (...args) => { record('subscribeToIncidents'); return () => {}; };",
          "export const subscribeToDeployments = (...args) => { record('subscribeToDeployments'); return () => {}; };",
          "export const saveServerToFirestore = async (...args) => { record('saveServerToFirestore'); };",
          "export const deleteServerFromFirestore = async (...args) => { record('deleteServerFromFirestore'); };",
          "export const saveIncidentToFirestore = async (...args) => { record('saveIncidentToFirestore'); };",
          "export const saveDeploymentToFirestore = async (...args) => { record('saveDeploymentToFirestore'); };",
        ].join('\n');
      }
      return null;
    },
  };

  // Vite SSR module loading is documented at https://vite.dev/guide/ssr.html#ssrloadmodule.
  // middlewareMode is documented at https://vite.dev/config/server-options#server-middlewaremode.
  const server = await createServer({
    configFile: false,
    root: APP_ROOT,
    envDir: false,
    envPrefix: '__DEVOBS_TEST_ONLY_',
    define: {
      'import.meta.env.VITE_FIREBASE_ENABLED': JSON.stringify(String(enabled)),
      'import.meta.env.VITE_GOOGLE_WORKSPACE_ENABLED': JSON.stringify('false'),
    },
    plugins: [plugin],
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const appModule = await server.ssrLoadModule('/src/App.tsx');
    assert.equal(
      typeof appModule.createDemoDashboardActions,
      'function',
      'App must expose the action factory used by its demo UI',
    );
    return { appModule, facadeImports, persistenceCalls, server, spyKey };
  } catch (error) {
    await server.close();
    delete globalThis[spyKey];
    throw error;
  }
}

before(async () => {
  for (const enabled of FIREBASE_FLAGS) {
    contexts.set(enabled, await loadAppWithFirebaseFlag(enabled));
  }
});

after(async () => {
  await Promise.all(
    [...contexts.values()].map(async ({ server, spyKey }) => {
      await server.close();
      delete globalThis[spyKey];
    }),
  );
});

function makeFixture(context) {
  const state = {
    servers: [
      {
        id: 'server-synthetic-1',
        name: 'Synthetic API server',
        status: 'healthy',
        cpu: 30,
        uptimeDays: 12,
        lastPing: 'now',
      },
    ],
    incidents: [
      {
        id: 'incident-synthetic-1',
        serverId: 'server-synthetic-1',
        serverName: 'Synthetic API server',
        severity: 'warning',
        code: 'SYNTHETIC-OPEN',
        message: 'Synthetic incident only',
        stackTrace: 'synthetic stack',
        timestamp: '2026-11-23 11:00:00',
        resolved: false,
      },
    ],
    deployments: [
      {
        id: 'deployment-synthetic-1',
        service: 'Synthetic service',
        version: 'v0',
        status: 'success',
        timestamp: '2026-11-23 10:00:00',
      },
    ],
  };
  const toasts = [];
  let nextId = 0;

  function setState(key, update) {
    state[key] = typeof update === 'function' ? update(state[key]) : update;
  }

  function createActions() {
    return context.appModule.createDemoDashboardActions({
      servers: state.servers,
      incidents: state.incidents,
      setServers: (update) => setState('servers', update),
      setIncidents: (update) => setState('incidents', update),
      setDeployments: (update) => setState('deployments', update),
      addToast: (message, type) => toasts.push({ message, type }),
      createId: (prefix) => `synthetic-${prefix}-${++nextId}`,
      now: () => '2026-11-23T12:34:56.000Z',
      random: () => 0,
    });
  }

  function assertNoFirestorePersistence() {
    assert.deepEqual(context.persistenceCalls, [], 'demo actions must not call Firestore methods');
    assert.deepEqual(context.facadeImports, [], 'App demo code must not import the Firestore facade/service');
  }

  return { state, toasts, createActions, assertNoFirestorePersistence };
}

for (const firebaseEnabled of FIREBASE_FLAGS) {
  test(`demo dashboard actions stay local when VITE_FIREBASE_ENABLED=${firebaseEnabled}`, async (t) => {
    const context = contexts.get(firebaseEnabled);
    assert.ok(context, 'the isolated App module must load for this explicit flag fixture');

    await t.test('server creation changes only the synthetic dashboard state', () => {
      const fixture = makeFixture(context);
      fixture.createActions().handleAddServer({
        name: 'Synthetic worker',
        status: 'healthy',
        cpu: 12,
      });

      assert.equal(fixture.state.servers[0].id, 'synthetic-srv-1');
      assert.equal(fixture.state.servers[0].name, 'Synthetic worker');
      assert.equal(fixture.state.servers[0].uptimeDays, 0);
      assert.equal(fixture.toasts.length, 1);
      assert.match(fixture.toasts[0].message, /بيانات العرض التجريبية فقط/);
      fixture.assertNoFirestorePersistence();
    });

    await t.test('server update toggles only the synthetic dashboard state', () => {
      const fixture = makeFixture(context);
      fixture.createActions().handleToggleMaintenance('server-synthetic-1');

      assert.equal(fixture.state.servers[0].status, 'maintenance');
      assert.equal(fixture.toasts.length, 1);
      assert.match(fixture.toasts[0].message, /بيانات العرض فقط/);
      fixture.assertNoFirestorePersistence();
    });

    await t.test('server deletion removes only the synthetic dashboard item', () => {
      const fixture = makeFixture(context);
      fixture.createActions().handleDeleteServer('server-synthetic-1');

      assert.deepEqual(fixture.state.servers, []);
      assert.match(fixture.toasts[0].message, /لم يُحذف خادم حقيقي/);
      fixture.assertNoFirestorePersistence();
    });

    await t.test('incident creation and its server status update remain local', () => {
      const fixture = makeFixture(context);
      fixture.createActions().handleSimulateIncident({
        code: 'SYNTHETIC-CPU',
        severity: 'critical',
        message: 'Synthetic incident created by test',
        stack: 'synthetic stack only',
        serverId: 'server-synthetic-1',
      });

      assert.equal(fixture.state.incidents[0].id, 'synthetic-inc-1');
      assert.equal(fixture.state.incidents[0].code, 'SYNTHETIC-CPU');
      assert.equal(fixture.state.servers[0].status, 'critical');
      assert.equal(fixture.state.servers[0].cpu, 96);
      assert.match(fixture.toasts[0].message, /قائمة العرض فقط/);
      fixture.assertNoFirestorePersistence();
    });

    await t.test('incident resolution changes only the synthetic dashboard state', () => {
      const fixture = makeFixture(context);
      fixture.createActions().handleResolveIncident('incident-synthetic-1');

      assert.equal(fixture.state.incidents[0].resolved, true);
      assert.equal(fixture.state.incidents[0].resolvedAt, '2026-11-23 12:34:56');
      fixture.assertNoFirestorePersistence();
    });

    await t.test('deployment creation adds only a synthetic dashboard record', () => {
      const fixture = makeFixture(context);
      fixture.createActions().handleAddNewDeployment({
        service: 'Synthetic service',
        version: 'demo-v1',
        status: 'success',
      });

      assert.equal(fixture.state.deployments[0].id, 'synthetic-dep-1');
      assert.equal(fixture.state.deployments[0].version, 'demo-v1');
      assert.equal(fixture.state.deployments[0].timestamp, '2026-11-23 12:34:56');
      assert.match(fixture.toasts[0].message, /سجل نشر تجريبي فقط/);
      fixture.assertNoFirestorePersistence();
    });
  });
}
