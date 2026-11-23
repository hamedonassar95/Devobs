import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { after, before, test } from 'node:test';
import {
  assertSucceeds,
  initializeTestEnvironment,
} from '@firebase/rules-unit-testing';
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  query,
  setDoc,
  updateDoc,
  where,
} from 'firebase/firestore';

const PROJECT_ID = 'demo-devobs-firestore-authz';
const EXPECTED_EMULATOR_HOST = '127.0.0.1:8080';
const COLLECTIONS = ['servers', 'incidents', 'deployments'];
const SEED_RECORDS = COLLECTIONS.flatMap((collectionName) => [
  {
    collection: collectionName,
    id: collectionName + '-tenant-a-owner-a1',
    data: { tenantId: 'tenant-a', ownerUid: 'owner-a1', name: 'synthetic-a1' },
  },
  {
    collection: collectionName,
    id: collectionName + '-tenant-a-owner-a2',
    data: { tenantId: 'tenant-a', ownerUid: 'owner-a2', name: 'synthetic-a2' },
  },
  {
    collection: collectionName,
    id: collectionName + '-tenant-b-owner-b1',
    data: { tenantId: 'tenant-b', ownerUid: 'owner-b1', name: 'synthetic-b1' },
  },
]);

let testEnv;

function recordRef(db, record) {
  return doc(db, record.collection, record.id);
}

async function expectPermissionDenied(operation, label) {
  await assert.rejects(
    () => operation(),
    (error) => error?.code === 'permission-denied',
    label + ': expected Firestore permission-denied',
  );
}

before(async () => {
  assert.ok(PROJECT_ID.startsWith('demo-'), 'A demo-only Firebase project ID is required');

  // Do not let this suite fall back to a live Firestore endpoint.
  assert.equal(
    process.env.FIRESTORE_EMULATOR_HOST,
    EXPECTED_EMULATOR_HOST,
    'Run through the configured localhost Firestore Emulator; remote hosts are forbidden',
  );

  const config = JSON.parse(
    await readFile(new URL('./firebase.json', import.meta.url), 'utf8'),
  );
  assert.equal(config.emulators?.firestore?.host, '127.0.0.1');
  assert.equal(config.emulators?.firestore?.port, 8080);
  assert.equal(config.emulators?.ui?.enabled, false);
  const packageManifest = JSON.parse(
    await readFile(new URL('./package.json', import.meta.url), 'utf8'),
  );
  assert.match(packageManifest.scripts?.test ?? '', /--only firestore/);
  assert.match(packageManifest.scripts?.test ?? '', /--project demo-devobs-firestore-authz/);

  const rules = await readFile(new URL('./firestore.rules', import.meta.url), 'utf8');
  testEnv = await initializeTestEnvironment({
    projectId: PROJECT_ID,
    firestore: { rules },
  });

  await testEnv.clearFirestore();
  await testEnv.withSecurityRulesDisabled(async (context) => {
    const db = context.firestore();
    await Promise.all(
      SEED_RECORDS.map((record) =>
        setDoc(recordRef(db, record), record.data),
      ),
    );
  });
});

after(async () => {
  await testEnv?.cleanup();
});

test('anonymous reads, creates, modifications and deletes are denied', async () => {
  const anonymousDb = testEnv.unauthenticatedContext().firestore();

  for (const record of SEED_RECORDS) {
    const ref = recordRef(anonymousDb, record);
    await expectPermissionDenied(
      () => getDoc(ref),
      'anonymous get ' + record.collection + '/' + record.id,
    );
    await expectPermissionDenied(
      () => getDocs(collection(anonymousDb, record.collection)),
      'anonymous list ' + record.collection,
    );
    await expectPermissionDenied(
      () => setDoc(doc(anonymousDb, record.collection, 'anonymous-create'), {
        tenantId: 'tenant-a',
        ownerUid: 'owner-a1',
        name: 'synthetic-anonymous',
      }),
      'anonymous create ' + record.collection,
    );
    await expectPermissionDenied(
      () => updateDoc(ref, { name: 'synthetic-anonymous-update' }),
      'anonymous update ' + record.collection + '/' + record.id,
    );
    await expectPermissionDenied(
      () => deleteDoc(ref),
      'anonymous delete ' + record.collection + '/' + record.id,
    );
  }
});

test('an authenticated user is isolated from other owners and tenants', async () => {
  const ownerA1 = testEnv.authenticatedContext('owner-a1', {
    tenant_id: 'tenant-a',
  }).firestore();

  for (const record of SEED_RECORDS) {
    if (record.data.ownerUid === 'owner-a1') {
      continue;
    }
    const ref = recordRef(ownerA1, record);
    await expectPermissionDenied(
      () => getDoc(ref),
      'owner-a1 read ' + record.collection + '/' + record.id,
    );
    await expectPermissionDenied(
      () => updateDoc(ref, { name: 'synthetic-cross-boundary-update' }),
      'owner-a1 update ' + record.collection + '/' + record.id,
    );
    await expectPermissionDenied(
      () => deleteDoc(ref),
      'owner-a1 delete ' + record.collection + '/' + record.id,
    );
  }
});

test('tenant and owner constrained queries return only the caller owned fixture', async () => {
  const ownerA1 = testEnv.authenticatedContext('owner-a1', {
    tenant_id: 'tenant-a',
  }).firestore();
  const ownerB1 = testEnv.authenticatedContext('owner-b1', {
    tenant_id: 'tenant-b',
  }).firestore();

  for (const collectionName of COLLECTIONS) {
    const ownQuery = query(
      collection(ownerA1, collectionName),
      where('tenantId', '==', 'tenant-a'),
      where('ownerUid', '==', 'owner-a1'),
    );
    const ownSnapshot = await assertSucceeds(getDocs(ownQuery));
    assert.deepEqual(
      ownSnapshot.docs.map((item) => item.id),
      [collectionName + '-tenant-a-owner-a1'],
    );

    const otherTenantQuery = query(
      collection(ownerA1, collectionName),
      where('tenantId', '==', 'tenant-b'),
      where('ownerUid', '==', 'owner-b1'),
    );
    await expectPermissionDenied(
      () => getDocs(otherTenantQuery),
      'owner-a1 query other tenant in ' + collectionName,
    );

    const incompleteOwnerQuery = query(
      collection(ownerA1, collectionName),
      where('tenantId', '==', 'tenant-a'),
    );
    await expectPermissionDenied(
      () => getDocs(incompleteOwnerQuery),
      'owner-a1 query without owner constraint in ' + collectionName,
    );

    const tenantBQuery = query(
      collection(ownerB1, collectionName),
      where('tenantId', '==', 'tenant-b'),
      where('ownerUid', '==', 'owner-b1'),
    );
    const tenantBSnapshot = await assertSucceeds(getDocs(tenantBQuery));
    assert.deepEqual(
      tenantBSnapshot.docs.map((item) => item.id),
      [collectionName + '-tenant-b-owner-b1'],
    );
  }
});

test('the experimental fixture permits an owner to create, read, update and delete own records', async () => {
  const ownerA1 = testEnv.authenticatedContext('owner-a1', {
    tenant_id: 'tenant-a',
  }).firestore();

  for (const collectionName of COLLECTIONS) {
    const ownRecord = SEED_RECORDS.find(
      (record) =>
        record.collection === collectionName
        && record.data.ownerUid === 'owner-a1',
    );
    const seededRef = recordRef(ownerA1, ownRecord);
    await assertSucceeds(getDoc(seededRef));
    await assertSucceeds(updateDoc(seededRef, { name: 'synthetic-a1-updated' }));

    const createdRef = doc(ownerA1, collectionName, collectionName + '-owner-created');
    await assertSucceeds(setDoc(createdRef, {
      tenantId: 'tenant-a',
      ownerUid: 'owner-a1',
      name: 'synthetic-owner-created',
    }));
    await assertSucceeds(deleteDoc(createdRef));
  }
});

test('an owner cannot create a record for another tenant or impersonate another owner', async () => {
  const ownerA1 = testEnv.authenticatedContext('owner-a1', {
    tenant_id: 'tenant-a',
  }).firestore();

  for (const collectionName of COLLECTIONS) {
    await expectPermissionDenied(
      () => setDoc(doc(ownerA1, collectionName, 'forged-tenant'), {
        tenantId: 'tenant-b',
        ownerUid: 'owner-a1',
        name: 'synthetic-forged-tenant',
      }),
      'owner-a1 create in tenant-b ' + collectionName,
    );
    await expectPermissionDenied(
      () => setDoc(doc(ownerA1, collectionName, 'forged-owner'), {
        tenantId: 'tenant-a',
        ownerUid: 'owner-a2',
        name: 'synthetic-forged-owner',
      }),
      'owner-a1 create as owner-a2 in ' + collectionName,
    );
  }
});

test('an owner cannot change tenant or ownership fields on an existing record', async () => {
  const ownerA1 = testEnv.authenticatedContext('owner-a1', {
    tenant_id: 'tenant-a',
  }).firestore();

  for (const collectionName of COLLECTIONS) {
    const ownRecord = SEED_RECORDS.find(
      (record) =>
        record.collection === collectionName
        && record.data.ownerUid === 'owner-a1',
    );
    const ref = recordRef(ownerA1, ownRecord);
    await expectPermissionDenied(
      () => updateDoc(ref, { tenantId: 'tenant-b' }),
      'owner-a1 change tenant on ' + collectionName,
    );
    await expectPermissionDenied(
      () => updateDoc(ref, { ownerUid: 'owner-a2' }),
      'owner-a1 transfer ownership on ' + collectionName,
    );
    await expectPermissionDenied(
      () => updateDoc(ref, { extraField: 'not-allowlisted' }),
      'owner-a1 add unapproved field on ' + collectionName,
    );
  }
});
