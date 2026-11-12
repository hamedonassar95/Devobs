import type { Deployment, Incident, Server } from '../types/serverDashboard';

type FirestoreService = typeof import('./firebaseFirestore');

const explicitlyEnabled = import.meta.env.VITE_FIREBASE_ENABLED === 'true';
let servicePromise: Promise<FirestoreService> | undefined;

function loadService(): Promise<FirestoreService> {
  servicePromise ??= import('./firebaseFirestore');
  return servicePromise;
}

function subscribe(register: (service: FirestoreService) => () => void): () => void {
  if (!explicitlyEnabled) return () => {};

  let cancelled = false;
  let unsubscribe = () => {};
  void loadService()
    .then((service) => {
      if (!cancelled) unsubscribe = register(service);
    })
    .catch((error: unknown) => {
      console.warn('Optional Firebase service failed to load:', error);
    });

  return () => {
    cancelled = true;
    unsubscribe();
  };
}

export const subscribeToServers = (onUpdate: (servers: Server[]) => void) =>
  subscribe((service) => service.subscribeToServers(onUpdate));

export const subscribeToIncidents = (onUpdate: (incidents: Incident[]) => void) =>
  subscribe((service) => service.subscribeToIncidents(onUpdate));

export const subscribeToDeployments = (onUpdate: (deployments: Deployment[]) => void) =>
  subscribe((service) => service.subscribeToDeployments(onUpdate));

export async function saveServerToFirestore(server: Server): Promise<void> {
  if (!explicitlyEnabled) return;
  await (await loadService()).saveServerToFirestore(server);
}

export async function deleteServerFromFirestore(serverId: string): Promise<void> {
  if (!explicitlyEnabled) return;
  await (await loadService()).deleteServerFromFirestore(serverId);
}

export async function saveIncidentToFirestore(incident: Incident): Promise<void> {
  if (!explicitlyEnabled) return;
  await (await loadService()).saveIncidentToFirestore(incident);
}

export async function saveDeploymentToFirestore(deployment: Deployment): Promise<void> {
  if (!explicitlyEnabled) return;
  await (await loadService()).saveDeploymentToFirestore(deployment);
}
