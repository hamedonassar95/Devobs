# DevObs AI Intelligence — Authenticated read-only API security gate

**Scope:** Original `hamedonassar95/Devobs` only. The read-only source implementation is present in `main`, but the service is **not deployed**. `feat/devobs-oidc-readonly-api-20261025` is the historical development branch name, not a deployment. No external IdP, user signup, secrets, cloud database, public API host or paid platform was configured.

## Implemented source components (not deployed)

- `scripts/devobs_intelligence/oidc_tokens.py`: validates **RFC 9068-style JWT OAuth access tokens**, not OIDC ID Tokens. Public RSA signing keys are supplied by an operator-pinned JWKS; this module never fetches arbitrary URLs, never loads private keys, and never reads a provider secret.
- Required checks: `typ=at+jwt`, `RS256` allowlist, known `kid`, RSA signature, exact HTTPS issuer, exact single-value audience, configured client ID, `sub`, `exp`, `iat`, `jti`, explicit `devobs.read` scope and max 15-minute issued lifetime.
- `scripts/devobs_intelligence/api_app.py`: an *in-process, GET-only* WSGI callable. **No server listener** is created or deployed. Only endpoint: `GET /v1/tenants/{tenant}/projects/{project}/ci`.
- Authentication failure yields HTTP 401 with `invalid_token`; valid identity without resource access yields 403 with a uniform `access_denied`; unexpected storage failure is not translated to success; no raw token in errors or responses.
- `scripts/devobs_intelligence/tenant_store.py`: *SQLite memory-only fixture store* joining tenant, project and verified user on the same query; identical project names across tenants do not cause data crossover.
- `requirements-api.txt` declares direct API dependencies; `requirements-api.lock` pins the resolved dependency tree with SHA256 hashes, and CI installs it using pip hash-checking mode. Private keys are generated **only in test memory**. Nothing is deployed.
- `tests/test_intelligence_api_security.py`: verifies real test RSA signatures, rejection of unsigned/ID/wrong-scope/expired tokens, 401/403/405, tenant crossover and a real SQLite query.

## Trust contract (critical)

1. The configured RSA JWKS **must originate from authenticated, verified HTTPS issuer metadata** and be provisioned through approved config, not through requests or model answers. Discovery, rotation scheduling and revocation are **not implemented**.
2. The bearer access token must conform to the agreed JWT profile. **An ID Token is not valid API authorization.** Opaque token providers require a separately designed introspection boundary.
3. `sub` is cryptographically verified before passing to `OfflineTenantStore`. The store never accepts a public token as its input. Roles or claimed tenant IDs in client-supplied headers are ignored.
4. The API is **read-only**. No PR writing, build execution, merge, deploy, rollback, infrastructure mutation or payment action is exposed here.
5. Tests run entirely in-process. The proposed API includes a process-local sliding-window limit of 60 requests per verified subject and tenant per 60-second window, a 4,096-key state cap, and at most 8 concurrent storage reads per process. It returns 429 with `Retry-After` for a rate limit and 503 with `Retry-After` when saturated. These are conservative starting defaults, not load-derived service limits: they do not protect JWT verification from unauthenticated floods and do not coordinate across processes/instances. Do not expose the WSGI callable publicly without TLS termination, a global gateway limit, validated issuer onboarding, reverse proxy hardening, identity lifecycle, JWKS rotation, time-sync monitoring, sender-constrained or short-lived token risk controls and independent pentest.
6. SQLite fixture separation is **not PostgreSQL RLS**. Before SaaS, implement authenticated storage connections using per-tenant restrictions, negative RLS integration tests with non-owner DB roles and protection against admin bypass.
7. The API has no background task, connection to GitLab, customer ingestion, production data, OpenTelemetry collector or external authentication provider. All of these remain **BLOCKED** pending review.

## Verification commands

From the original repository root on the feature branch:

```bash
python3 -m pip install --require-hashes -r requirements-api.lock
python3 -m unittest discover -s tests -p 'test_intelligence_api_security.py' -v
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

For further changes, run the existing `CI` and required security checks on the exact candidate SHA. The resolved dependency lock is audited by `pip-audit --requirement requirements-api.lock` in CI. Passing code checks do not verify a hosted API, provider configuration or production tenant isolation.

## Pending requirements before a paid product

- Operator-managed OIDC client onboarding and signed JWKS discovery/rotation, revocation handling and session lifecycle.
- Private networking and secure TLS host; rate limiting, abuse protection, alerts and end-to-end service threat model.
- Staging PostgreSQL isolation and restore test; signed/atomic human approvals for mutations; independently tested audit/retention policies.
- Verified compatibility with chosen identity provider; live role provisioning, support/consent, legal documents and commercial licensing.
- Subscription billing and production deployment require **separate explicit approval**.

## Evidence-based standards (reviewed October 2026)

- RFC 9068 JWT access tokens: https://www.rfc-editor.org/rfc/rfc9068.html
- RFC 9700 OAuth Security BCP: https://www.rfc-editor.org/rfc/rfc9700.html
- PyJWT verified token APIs: https://pyjwt.readthedocs.io/en/stable/api.html
- OWASP broken object-level authorization: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- PyJWT package provenance and version: https://pypi.org/project/PyJWT/
