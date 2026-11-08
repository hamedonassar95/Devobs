import { getApps, getApp, initializeApp } from 'firebase/app';
import {
  getFirestore,
  collection,
  doc,
  setDoc,
  getDocs,
  onSnapshot,
  deleteDoc,
  getDocFromServer,
} from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import firebaseConfig from '../../firebase-applet-config.json';
import { Server, Incident, Deployment } from '../types/serverDashboard';

const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
const auth = getAuth(app);

const customDatabaseId =
  (firebaseConfig as any).firestoreDatabaseId ||
  'ai-studio-promptpal-f1b3ebe9-9826-4fca-9a67-b5376e8669b3';

// CRITICAL: Must pass firestoreDatabaseId if configured
export const db = customDatabaseId
  ? getFirestore(app, customDatabaseId)
  : getFirestore(app);

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
      userId: auth.currentUser?.uid,
      email: auth.currentUser?.email,
      emailVerified: auth.currentUser?.emailVerified,
      isAnonymous: auth.currentUser?.isAnonymous,
      tenantId: auth.currentUser?.tenantId,
      providerInfo:
        auth.currentUser?.providerData?.map((provider) => ({
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
  const path = `${SERVERS_COLLECTION}/${server.id}`;
  try {
    const docRef = doc(db, SERVERS_COLLECTION, server.id);
    await setDoc(docRef, server, { merge: true });
  } catch (err: any) {
    console.warn('Failed to save server to Firestore:', err.message);
  }
}

export async function deleteServerFromFirestore(serverId: string): Promise<void> {
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
  const path = `${DEPLOYMENTS_COLLECTION}/${deployment.id}`;
  try {
    const docRef = doc(db, DEPLOYMENTS_COLLECTION, deployment.id);
    await setDoc(docRef, deployment, { merge: true });
  } catch (err: any) {
    console.warn('Failed to save deployment to Firestore:', err.message);
  }
}

// Seed initial data if Firestore collections are empty
export async function seedFirestoreIfEmpty(
  initialServers: Server[],
  initialIncidents: Incident[],
  initialDeployments: Deployment[]
): Promise<void> {
  try {
    const serversSnap = await getDocs(collection(db, SERVERS_COLLECTION));
    if (serversSnap.empty) {
      for (const s of initialServers) {
        await saveServerToFirestore(s);
      }
      for (const inc of initialIncidents) {
        await saveIncidentToFirestore(inc);
      }
      for (const dep of initialDeployments) {
        await saveDeploymentToFirestore(dep);
      }
      console.log('Seeded initial server operations data to Cloud Firestore.');
    }
  } catch (err: any) {
    console.warn('Notice: Firestore seeding check skipped:', err.message);
  }
}
