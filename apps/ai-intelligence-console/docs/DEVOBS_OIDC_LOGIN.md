# Optional Devobs read-only sign-in

**Prepared in code; disabled by default. Live identity acceptance is UNVERIFIED.**
This session is independent of Firebase/Google Workspace and does not change
Firestore access, dashboard sample data, diagnostics grants or AI spending.

## Public build configuration

Only enable after a reviewed Keycloak issuer and real HTTPS console exist:

- `VITE_DEVOBS_OIDC_ENABLED=true`
- `VITE_DEVOBS_OIDC_ISSUER`: the exact HTTPS issuer
  `https://<assigned-devobs-keycloak-hosted-subdomain>.onrender.com/realms/devobs-hosted`.
  No credentials, query, fragment, alternate realm or trailing slash.
- `VITE_DEVOBS_OIDC_REDIRECT_URI`: the exact console origin followed by
  `/auth/devobs/callback`. No return URL, wildcard, query or fragment.

Register that same redirect in the hosted realm through `DEVOBS_OIDC_REDIRECT_URI`.
Its public client remains `devobs-hosted-public`. These values are public, but
must be real operator-verified values; no provider/client secret belongs in a
`VITE_` variable. The host must serve this callback with the SPA fallback.

## Behavior and boundaries

The pinned official `keycloak-js` adapter owns standard Authorization Code,
PKCE S256, nonce/state checking and code exchange. Login starts only from an
explicit button click. It requests `devobs.read` (the adapter also requests
`openid`); it never requests `devobs.ai.diagnose` or calls an AI endpoint.
No automatic login, silent SSO, session iframe, background refresh or adapter
logging is enabled. Initialization, including lazy import, is bounded to 15s.
That timeout denies a late session; it does not abort the adapter's underlying
network exchange. The official adapter manages exchange transport/cookies and
response parsing; it does not inherit the separate diagnostics proxy's redirect
or response-size controls.

The code response uses a URL **fragment** to avoid sending it to the console's
HTTP server. The fixed callback is validated and consumed once per page, then
its query/fragment is removed before normal application modules initialize.
Untrusted issuer, duplicate/unexpected parameters, failed adapter state checks,
expiry and cancellation leave access unavailable, without displaying provider
errors or response values. The Devobs API remains the authority for JWT
signature, lifetime, issuer/audience, scope and tenant/service authorization.

Access/refresh/ID tokens stay in the adapter's memory. No token is displayed,
logged, exported or written by this integration to browser storage. The adapter
manages temporary pending login state/PKCE verifier storage across the redirect;
this is distinct from storing tokens. Reloading loses the access session.
Expiry clears local access without refreshing. **Local sign-out** clears this
console session; it does not end the provider's SSO session or Google session.
No token hint or logout request is sent to the provider by local sign-out.

The incident modal's explicit token/redaction/request workflow stays separate.
The current hosted realm grants read-only access; it cannot enable diagnosis.
Diagnosis needs an independently reviewed scope grant, tenant bindings and AI
budget, plus a passing deployed API. Do not copy a Google token into Devobs.

## Verification and activation

`npm test`, `npm run lint` and `npm run build` cover the console. New tests use
mock adapters and synthetic response markers only; they do not run a real IdP,
generate real authorization codes/tokens or prove the vendor's protocol internals.
Real signed-token acceptance, replay/denial tests, HTTPS/DB/CA/network validation,
key rotation, persistence/restore and all-in budget controls remain prerequisites.
No provider settings, user identities, secret material or resources are created.

Reference: [official Keycloak JavaScript adapter guide](https://www.keycloak.org/securing-apps/javascript-adapter)
for PKCE, fragment response mode, memory-only tokens and initialization options.
