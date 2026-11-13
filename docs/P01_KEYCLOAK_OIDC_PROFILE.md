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

## Optional local-only Keycloak 26.8.2 discovery/JWKS preflight

This is a disposable, operator-triggered development fixture. It does not modify the Devobs verifier or create an identity-provider account:

- `dev/keycloak/compose.local.yaml` pins the official `quay.io/keycloak/keycloak:26.8.2` OCI image index by digest: `sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0`. **VERIFIED 2026-11-13:** `docker buildx imagetools inspect quay.io/keycloak/keycloak:26.8.2` reported OCI image-index media type and this digest; a Quay Registry v2 `HEAD` for the same tag returned HTTP 200 with the same `Docker-Content-Digest`. The official registry is [Quay's Keycloak repository](https://quay.io/repository/keycloak/keycloak?tab=tags). Re-resolve and compare the digest before intentionally updating the image pin.
- The compose service uses Keycloak's documented `start-dev` and `--import-realm` development/import behavior, but publishes port 8080 only on `127.0.0.1`. It mounts the minimal `devobs-local` realm JSON read-only, uses no external database, and has no bootstrap administrator variables, users, clients, passwords, or committed keys. Do not use `start-dev` as a production configuration.
- [The local preflight](../scripts/p01_keycloak_local_preflight.py) performs only two bounded GETs to the exact local origin and fixed `devobs-local` realm: discovery and its same-origin JWKS. It rejects redirects, unexpected origins/paths, malformed or oversized responses, non-RS256 signing keys, weak RSA modulus sizes, duplicate key IDs, and private JWK fields. It prints fixed status codes and a key count only, never document contents. It does not request tokens or contact any non-loopback address.
- A `LOCAL_OIDC_PREFLIGHT_PASS` is only a response-shape and public-key-metadata check. The report always states `https_only_issuer_policy: NOT_COMPATIBLE_WITH_LOCAL_HTTP` and `readiness_claim: NOT_ESTABLISHED`. The existing production verifier requires an HTTPS issuer in [`oidc_tokens.py`](../scripts/devobs_intelligence/oidc_tokens.py); local HTTP discovery cannot populate or validate production configuration. The tool also cannot attest that a process answering on localhost is the pinned Keycloak container.

### Manual disposable smoke procedure

Tests do not start Docker, pull the Keycloak image, or run an IdP. To perform an explicitly local smoke test on an operator workstation with Docker Compose v2 and an available host port 8080:

```sh
docker compose -f dev/keycloak/compose.local.yaml config --quiet
docker compose -f dev/keycloak/compose.local.yaml up -d
python3 scripts/p01_keycloak_local_preflight.py
docker compose -f dev/keycloak/compose.local.yaml down --remove-orphans
```

`up -d` downloads the pinned public image if it is not already present and starts the disposable service. The realm has no configured user or application client and Compose does not create an administrator. The preflight is read-only and needs no login. Stop and remove the service even if the preflight fails; `down --remove-orphans` removes its container and Compose network. There is no named data volume. Do not export or commit any Keycloak-generated internal signing data. If port 8080 is occupied, stop here; do not expose Keycloak on a non-loopback interface or change the script's fixed CLI origin.

### Evidence required after this local preflight

Local HTTP success does **not** satisfy Devobs's HTTPS-only issuer policy or prove access-token interoperability. A later separately approved test must use an HTTPS issuer with a valid certificate and a real, short-lived, synthetic test access token. Apply the existing strict verifier unchanged and verify all of the following from the signed token and trusted public JWKS:

- JWT header `typ` is `at+jwt` (or `application/at+jwt`) and signature algorithm is RS256.
- `iss` exactly matches the HTTPS realm issuer; `aud` is exactly the single string `devobs-api`; `client_id` exactly matches the registered Devobs client. `azp` alone is not a substitute.
- `sub`, `jti`, integer `iat` and `exp` satisfy existing verifier bounds; required `devobs.read` scope is present. `devobs.ai.diagnose` needs a separate authorization decision.
- JWKS is fetched and verified over HTTPS from the exact trusted issuer origin. Exercise an approved key rollover with the existing rotation verifier, checking old/new key overlap and rejection once an old key is removed. Never trust a token-provided key URL.

Record only sanitized pass/fail evidence and the reviewed source SHA. Keep tokens, private keys and identity-provider values out of Git and CI logs. This future test requires a separate owner approval and still would not by itself clear PostgreSQL/RLS, backups, cost ceiling, hosted-service, AI-9, or other P01 gates.

### Sources checked 2026-11-13

- [Keycloak running in a container](https://www.keycloak.org/server/containers) — development-mode command, loopback port example, and `--import-realm` mount location.
- [Keycloak Docker getting-started guide](https://www.keycloak.org/getting-started/getting-started-docker) — versioned `26.8.2` example and the administrator environment variables deliberately omitted here.
- [Keycloak realm import/export](https://www.keycloak.org/server/importExport) — startup import behavior and `.json` import files.
- [Keycloak 26.2.0 release notes](https://www.keycloak.org/2025/04/keycloak-2620-released) — `at+jwt` access-token header setting is opt-in; this remains a future token test, not part of local discovery.

These official pages and Quay metadata were retrieved on the date above. They verify published instructions and the registry manifest digest, not a running Keycloak instance or future realm/token compatibility. Actual Docker runtime behavior remains **UNVERIFIED** until the operator executes the manual smoke procedure.

## Built-in verification
- `python3 -m unittest discover -s tests -p 'test_intelligence_keycloak_profile.py' -v`
- `python3 -m unittest discover -s tests -p 'test_p01_keycloak_local_preflight.py' -v`
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
