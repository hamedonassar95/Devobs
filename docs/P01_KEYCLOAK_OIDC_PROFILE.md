# P01 — Keycloak OIDC access-token compatibility (review-only)

**Decision scope (2026-11-10):** Keycloak is the preferred *synthetic staging interoperability candidate* for Devobs's current strict RFC 9068-style access-token verifier. This is not an approved hosted identity provider. No Keycloak instance, user, app, DNS, subscription, provider connection, token, or deployment was created here.

## Why this candidate
- Devobs's existing `scripts/devobs_intelligence/oidc_tokens.py` requires an RS256-signed OAuth **access** JWT with `typ=at+jwt`, one string `aud`, exact `iss` and `client_id`, `jti`, `iat`, `exp` within 900 seconds, an ASCII-safe `sub` no longer than 64 characters, and `devobs.read` scope. The diagnosis route also checks `devobs.ai.diagnose`.
- Keycloak 26.2+ has an **opt-in** client setting "Use \"at+jwt\" as access token header type". Its client-scope protocol mappers support intended audience and literal claim values. A Keycloak-generated UUID user subject is compatible in *format*; this must be proven from a real test token before any live acceptance.
- Auth0 is another managed candidate, but its default end-user subject is generally `<connection>|<id>`; that fails the current `sub` allowlist. Auth0's RFC 9068 profile can supply `client_id`, but it does not prove end-to-end compatibility. Do not weaken the Devobs verifier or silently rewrite identity claims to make an issuer appear to pass.

## Operator-only nonproduction setup checklist
1. **Before acquiring or hosting anything**, review account eligibility, region, availability, data processing and the owner-approved combined cost ceiling. Production-grade Keycloak hosting needs its *own* managed infrastructure, TLS, maintenance and backups. Never reuse the existing Render API/Postgres as an unreviewed identity host. P01 remains **NO-GO**.
2. In an owner-controlled, trusted **nonproduction** Keycloak 26.2+ environment, prepare a dedicated `devobs-staging` realm with HTTPS and a *single* application client `devobs-staging-app`; for interactive login use Authorization Code + PKCE (S256), exact allowed redirect URIs and minimal roles. Disable unnecessary grants, open registration, and broad defaults.
3. In **Clients → Advanced → Fine grain OpenID Connect configuration**, enable **Use "at+jwt" as access token header type** for the specific client. Ensure RS256 signatures and an access token lifespan no greater than 15 minutes. An ID token is not acceptable.
4. Configure an audience mapper scoped to this client to emit exactly the string `devobs-api`. **Inspect actual output**: a JSON audience array (even one element) or additional default audiences will fail Devobs's `strict_aud` verifier. Do not disable strict audience checks in the application to work around it.
5. Ensure a `client_id` claim with value `devobs-staging-app` is present in the access token; a *client-local* hardcoded claim mapper is suitable for a single reviewed test client. Do not attach a hardcoded identity claim to realm-wide/default scopes or share it across clients. An `azp` claim **alone** is insufficient for the current verifier.
6. Restrict `devobs.read` to the authorized synthetic test user, and grant `devobs.ai.diagnose` only by an independent, reviewed decision. Scope strings alone do not replace the database's verified tenant membership and PostgreSQL RLS. Confirm `jti`, integer `iat`/`exp`, UUID-like `sub`, and valid current/expiry times.
7. From the **trusted issuer's** HTTPS OIDC discovery, independently verify the exact issuer and same-origin JWKS URI. Inspect that public signing keys expose `kid`, RSA modulus/exponent, `alg=RS256`, `use=sig`, and at least 2048-bit modulus. No token-supplied `jku` or untrusted key URL may be trusted. Record only the public provenance and success/failure; **never** commit live tokens, private keys, URLs with embedded credentials, access logs or signing secrets.
8. In a controlled offline smoke test, use the actual verified public metadata/JWKS and a short-lived test token with existing `trusted_oidc_verifier(...).verify(...)`. Explicitly demonstrate rejection of `typ=JWT`, array audience, wrong client ID, unknown key, bad subject, expired token and missing scope. Keep tokens out of GitHub CI logs. Only after a separately authorized operator review should the reviewed values be entered in Render's private environment and an **exact-SHA** redeploy considered.

## Built-in verification
- `python3 -m unittest discover -s tests -p 'test_intelligence_keycloak_profile.py' -v`
- `python3 -m unittest discover -s tests -p 'test_intelligence_oidc_metadata.py' -v`
- `python3 -m unittest discover -s tests -p 'test_intelligence_oidc_rotation.py' -v`
- `python3 -m unittest discover -s tests -v`

The new test suite uses freshly generated in-memory RSA keys and synthetic claims only: **it does not exercise Keycloak, authenticate real users, or establish runtime compatibility.** A real issuer/token sample must be evaluated privately by the operator before P01 T13 can pass.

## Required release stops
- No live Keycloak instance, trusted issuer, confirmed client, real signed access token, audience/profile, JWKS lifecycle or revocation evidence is available in this review.
- The existing Render API deployment previously failed closed with `invalid_staging_config`; configuring a candidate IdP **alone** does not fix database login, TLS peer verification, temporary DB network access, backup/restore, or combined spend-cap evidence.
- No identity/admin-provider API, user account, cloud resource, token, subscription, customer data, deploy, secret, or production action is permitted by this document. P01 and AI-9 remain **BLOCKED**.

## Primary sources
- Keycloak at+jwt feature (26.2): https://www.keycloak.org/2025/04/keycloak-2620-released
- Keycloak Server Admin Guide (clients, audiences and mappers): https://www.keycloak.org/docs/latest/server_admin/
- Keycloak Protocol Mapper reference: https://www.keycloak.org/admin-api/protocol-mappers
- Keycloak secure production setup: https://www.keycloak.org/server/configuration-production
- RFC 9068: https://www.rfc-editor.org/rfc/rfc9068.html
- OAuth 2.0 Security Best Current Practice: https://www.rfc-editor.org/rfc/rfc9700.html
- Auth0 subject format (alternative compatibility constraint): https://support.auth0.com/center/s/article/Documentation-regard-ID-Token-sub-claim-is-unclear
