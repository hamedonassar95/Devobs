# Offline acceptance contract for Devobs staging smoke checks

## Purpose and boundaries

**VERIFIED (source contract):** `tests/test_intelligence_staging_smoke.py` exercises the public `SmokeSettings.validate()` and `run_smoke(..., fetch=...)` seams in `scripts/devobs_intelligence/staging_smoke.py`. It uses synthetic settings, fake HTTPS response tuples, and standard-library `unittest`; it makes no socket, DNS, cloud, identity-provider, Render, or Supabase calls. It adds tests and documentation only, not a runtime feature or CI workflow change.

**VERIFIED (expected six-call read-only sequence):**

1. `GET /healthz` → `204`, empty body, `Cache-Control: no-store`.
2. `GET /readyz` → `204`, empty body, `Cache-Control: no-store`.
3. Anonymous scoped CI read → `401` and exactly `{"error":"invalid_token"}`.
4. Synthetic authorized tenant/project read → `200` and exactly the fixture `{"ci_state":"success","source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}`.
5. Separately authorized denied-tenant fixture → `200` with a valid CI state and full source SHA. This proves the synthetic target fixture exists before checking isolation.
6. Original tenant credentials against that other tenant's same project → `403` and exactly `{"error":"access_denied"}`.

The harness asserts every requested URL and whether the synthetic tenant token, denied-tenant token, or no token is supplied. The fetch seam consumes only its fixed response queue; it does not make a request. The verifier returns no data to the caller: observable acceptance is completion without `SmokeFailure`, while failure cases assert the public fixed error code.

## Negative cases covered offline

**VERIFIED (test behavior):** the suite requires fail-closed rejection for readiness `503`, unexpected status, missing or malformed `no-store`, missing JSON content type, empty/malformed/non-dictionary/oversized JSON, invalid full SHA, unknown CI status, unexpected response fields, and a denied-tenant fixture that returns `403` before the cross-tenant check. It also rejects wrong expected hostname/origin, non-HTTPS scheme, a path or query in the base URL, URL credentials, duplicate tenant tokens, and identical tenant scopes. A mocked transport exception must become `network_failure` without exposing its synthetic URL or token. A mocked redirect response is not followed and fails the liveness status check.

No assertion weakens the existing verifier. This suite validates the verifier's existing contract; it does not alter production code or existing tests.

## What this does not prove

**UNVERIFIED by this offline harness:**

- Live OIDC issuer authenticity, JWT signature/claim validation against an external identity provider, JWKS refresh, rotation, overlap, or key revocation.
- Hosted TLS certificate issuance, hostname ownership, DNS, real network routing, proxy behavior, or the managed service's actual redirect handling beyond the mocked standard-library path.
- PostgreSQL RLS behavior, database role privileges, migrations, connection pooling, or readiness against a live managed database. Those have separate disposable-PostgreSQL coverage in `tests/test_postgres_rls_integration.py`; that CI integration does not establish a managed production database's state.
- Tenant/user lifecycle, real tenant membership, or isolation under concurrent hosted requests.
- Real staging uptime, production SLOs, backup/restore, incident response, or SaaS readiness.

The existing `tests/test_intelligence_staging_app.py` exercises offline application bootstrap and mocked readiness behavior. `render.yaml` is a proposal with `autoDeployTrigger: off`, not evidence that a Render service or Supabase project exists. Do not interpret a passing offline suite as staging approval or production readiness.

## Separate approval before any future staging provisioning

**VERIFIED (repository operating boundary):** no provider configuration, service, database, secret, migration, billing, or environment was created or changed for this acceptance harness.

Before a future operator provisions managed staging, obtain explicit owner approval for the provider account/workspace, region and data residency, exact service/database scope, monthly budget and provider limits, synthetic-data policy, secret storage and rotation plan, network exposure, retention, and rollback/deletion plan. Independently review database roles and migrations before any approved staging migration. Supply credentials only through the approved provider secret interface; never place them in repository files, test fixtures, issues, or logs. Provisioning may incur charges and is a separate operation from this offline test PR.

## Run locally

```sh
python3 -m unittest tests.test_intelligence_staging_smoke -v
python3 -m unittest tests.test_intelligence_staging_app -v
python3 -m unittest discover -s tests -v
```

The first command requires only the Python standard library. The latter commands require the repository's pinned runtime dependencies; the complete suite may also skip tests that need a disposable PostgreSQL service when those test DSNs are absent.

## References

- [Python `unittest` documentation](https://docs.python.org/3/library/unittest.html)
- [OWASP API Security — Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- [Devobs staging proposal and operator gates](RENDER_SUPABASE_STAGING.md)
- [Offline staging application tests](../tests/test_intelligence_staging_app.py)
- [Disposable PostgreSQL RLS integration tests](../tests/test_postgres_rls_integration.py)
