import {
  getFirestore,
  collection,
  doc,
  setDoc,
  onSnapshot,
  deleteDoc,
  getDocFromServer,
} from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import type { Firestore } from 'firebase/firestore';
import { firebaseApp, firestoreDatabaseId } from './firebaseApp';
import { Server, Incident, Deployment } from '../types/serverDashboard';

const auth = firebaseApp ? getAuth(firebaseApp) : null;

export const db: Firestore | null = firebaseApp
  ? firestoreDatabaseId
    ? getFirestore(firebaseApp, firestoreDatabaseId)
    : getFirestore(firebaseApp)
  : null;

export enum OperationType {
  CREATE = 'create',
  UPDATE = 'update',
  DELETE = 'delete',
  LIST = 'list',
  GET = 'get',
  WRITE = 'write',
}

export interface FirestoreErrorInfo {
  error: string;
  operationType: OperationType;
  path: string | null;
  authInfo: {
    userId?: string | null;
    email?: string | null;
    emailVerified?: boolean | null;
    isAnonymous?: boolean | null;
    tenantId?: string | null;
    providerInfo?: {
      providerId?: string | null;
      email?: string | null;
    }[];
  };
}

export function handleFirestoreError(
  error: unknown,
  operationType: OperationType,
  path: string | null
) {
  const errInfo: FirestoreErrorInfo = {
    error: error instanceof Error ? error.message : String(error),
    authInfo: {
      userId: auth?.currentUser?.uid,
      email: auth?.currentUser?.email,
      emailVerified: auth?.currentUser?.emailVerified,
      isAnonymous: auth?.currentUser?.isAnonymous,
      tenantId: auth?.currentUser?.tenantId,
      providerInfo:
        auth?.currentUser?.providerData?.map((provider) => ({
          providerId: provider.providerId,
          email: provider.email,
        })) || [],
    },
    operationType,
    path,
  };
  console.error('Firestore Error: ', JSON.stringify(errInfo));
  throw new Error(JSON.stringify(errInfo));
}

// Connection validation test
async function testConnection() {
  if (!db) return;
  try {
    await getDocFromServer(doc(db, 'test', 'connection'));
  } catch (error) {
    if (error instanceof Error && error.message.includes('the client is offline')) {
      console.error('Please check your Firebase configuration.');
    }
  }
}
testConnection();

// Collection References
const SERVERS_COLLECTION = 'servers';
const INCIDENTS_COLLECTION = 'incidents';
const DEPLOYMENTS_COLLECTION = 'deployments';

// --- Servers Firestore APIs ---
export function subscribeToServers(onUpdate: (servers: Server[]) => void) {
  if (!db) return () => {};
  const colRef = collection(db, SERVERS_COLLECTION);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const items: Server[] = [];
      snapshot.forEach((d) => {
        items.push(d.data() as Server);
      });
      if (items.length > 0) {
        onUpdate(items);
      }
    },
    (err) => {
      console.warn('Firestore servers subscription warning (using local state):', err.message);
    }
  );
}

export async function saveServerToFirestore(server: Server): Promise<void> {
  if (!db) return;
  const path = `${SERVERS_COLLECTION}/${server.id}`;
  try {
    const docRef = doc(db, SERVERS_COLLECTION, server.id);
    await setDoc(docRef, server, { merge: true });
  } catch (err: any) {
    console.warn('Failed to save server to Firestore:', err.message);
  }
}

export async function deleteServerFromFirestore(serverId: string): Promise<void> {
  if (!db) return;
  const path = `${SERVERS_COLLECTION}/${serverId}`;
  try {
    const docRef = doc(db, SERVERS_COLLECTION, serverId);
    await deleteDoc(docRef);
  } catch (err: any) {
    console.warn('Failed to delete server from Firestore:', err.message);
  }
}

// --- Incidents Firestore APIs ---
export function subscribeToIncidents(onUpdate: (incidents: Incident[]) => void) {
  if (!db) return () => {};
  const colRef = collection(db, INCIDENTS_COLLECTION);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const items: Incident[] = [];
      snapshot.forEach((d) => {
        items.push(d.data() as Incident);
      });
      if (items.length > 0) {
        items.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
        onUpdate(items);
      }
    },
    (err) => {
      console.warn('Firestore incidents subscription warning:', err.message);
    }
  );
}

export async function saveIncidentToFirestore(incident: Incident): Promise<void> {
  if (!db) return;
  const path = `${INCIDENTS_COLLECTION}/${incident.id}`;
  try {
    const docRef = doc(db, INCIDENTS_COLLECTION, incident.id);
    await setDoc(docRef, incident, { merge: true });
  } catch (err: any) {
    console.warn('Failed to save incident to Firestore:', err.message);
  }
}

// --- Deployments Firestore APIs ---
export function subscribeToDeployments(onUpdate: (deployments: Deployment[]) => void) {
  if (!db) return () => {};
  const colRef = collection(db, DEPLOYMENTS_COLLECTION);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const items: Deployment[] = [];
      snapshot.forEach((d) => {
        items.push(d.data() as Deployment);
      });
      if (items.length > 0) {
        items.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
        onUpdate(items);
      }
    },
    (err) => {
      console.warn('Firestore deployments subscription warning:', err.message);
    }
  );
}

export async function saveDeploymentToFirestore(deployment: Deployment): Promise<void> {
  if (!db) return;
  const path = `${DEPLOYMENTS_COLLECTION}/${deployment.id}`;
  try {
    const docRef = doc(db, DEPLOYMENTS_COLLECTION, deployment.id);
    await setDoc(docRef, deployment, { merge: true });
  } catch (err: any) {
    console.warn('Failed to save deployment to Firestore:', err.message);
  }
}
