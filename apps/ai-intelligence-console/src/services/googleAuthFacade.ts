import type { User } from 'firebase/auth';

type GoogleAuthService = typeof import('./googleAuth');

const explicitlyEnabled =
  import.meta.env.VITE_FIREBASE_ENABLED === 'true' &&
  import.meta.env.VITE_GOOGLE_WORKSPACE_ENABLED === 'true';
let servicePromise: Promise<GoogleAuthService> | undefined;

function loadService(): Promise<GoogleAuthService> {
  if (!explicitlyEnabled) {
    return Promise.reject(
      new Error('Google Workspace sign-in is disabled. Configure and explicitly enable it first.')
    );
  }
  servicePromise ??= import('./googleAuth');
  return servicePromise;
}

export function initAuth(
  onAuthSuccess?: (user: User, token: string) => void,
  onAuthFailure?: () => void
): () => void {
  if (!explicitlyEnabled) {
    onAuthFailure?.();
    return () => {};
  }

  let cancelled = false;
  let unsubscribe = () => {};
  void loadService()
    .then((service) => {
      if (!cancelled) unsubscribe = service.initAuth(onAuthSuccess, onAuthFailure);
    })
    .catch(() => onAuthFailure?.());

  return () => {
    cancelled = true;
    unsubscribe();
  };
}

export async function googleSignIn(): Promise<{ user: User; accessToken: string } | null> {
  return (await loadService()).googleSignIn();
}
