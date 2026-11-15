import { createDevobsAuth, DEVOBS_CALLBACK } from './devobsAuth';

// Public build configuration only; never accepts a provider/client secret.
export const devobsAuth = createDevobsAuth({
  enabled: import.meta.env.VITE_DEVOBS_OIDC_ENABLED,
  issuer: import.meta.env.VITE_DEVOBS_OIDC_ISSUER,
  redirectUri: import.meta.env.VITE_DEVOBS_OIDC_REDIRECT_URI,
}, {
  origin: window.location.origin,
  loadAdapter: async config => {
    const { default: Keycloak } = await import('keycloak-js');
    return new Keycloak(config);
  },
  scrubCallback: () => { window.history.replaceState(null, '', DEVOBS_CALLBACK); },
});
