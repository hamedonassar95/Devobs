# AI-9 Service Authorization API v1 — Implementation Record

**Status:** Implemented locally on `feature/ai9-python-service-authorization-api-v1`, based on `main` tree `2d6a347618c4f075390a418cc6d7e758861cc687` (main commit `6f16e2f923536526ef563377f2dc6775c4dc370c`). The contract was registered and merged first in [the preregistration](AI9_SERVICE_AUTHORIZATION_API_V1_PREREGISTRATION.md). This is application integration evidence only, not an AI-9 model evaluation, hosted-service test, or production approval.

## Change

- Added `GET /v1/tenants/{tenant}/projects/{project}/services/{service_id}/authorization` to `scripts/devobs_intelligence/api_app.py`.
- The verified bearer-token subject is the only identity sent to `PostgresTenantStore.authorize_service`; tenant, project, and service scope are read only from the bounded route path.
- A literal `True` returns an empty `204 No Content` with `Cache-Control: no-store`. False results and `ValueError` return the existing generic `403 access_denied`; invalid credentials return `401`; exceptions and non-boolean store responses fail closed with generic `503`. Other methods return `405` with `Allow: GET`; unrecognized paths return `404`.
- The route uses the existing subject/tenant rate limiter and in-flight bound. It creates no registry rows, accepts no telemetry, and does not invoke the Node detector, confirmation adapter, journal, or evaluator.
- Added unit behavior tests in `tests/test_intelligence_api_security.py` and a signed-token-to-PostgreSQL-RLS WSGI integration test in `tests/test_postgres_rls_integration.py`.

## Local verification

Dependencies came from the repository's hash-pinned requirements files. The PostgreSQL service was an ephemeral local Docker `postgres:17` container and was stopped after the run. It used synthetic fixture identities and rows only.

| Command / scope | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p 'test_intelligence_api_security.py' -v` | 17 tests, all passed. |
| `PG_TEST_ADMIN_DSN=postgresql://postgres@127.0.0.1:55432/postgres PG_TEST_READER_DSN=postgresql://devobs_ci_reader@127.0.0.1:55432/postgres /tmp/devobs-ai9-service-api-v1-venv/bin/python -m unittest discover -s tests -p 'test_postgres_rls_integration.py' -v` | 22 tests, all passed against disposable PostgreSQL 17, including the new signed WSGI-to-RLS path. |
| `/tmp/devobs-ai9-service-api-v1-venv/bin/python -m unittest discover -s tests -v` | 549 tests completed: `OK (skipped=22)`. The skipped cases require the PostgreSQL fixture, which was run separately above. |

These runs validate only mocked route behavior and an isolated disposable PostgreSQL fixture. No hosted identity provider, managed database, endpoint, live tenant, real data, AI-9 seed, benchmark, Precision/Recall/FPR calculation, or production gate was used. The global `AI-9 = FAIL`, `P01 = NO-GO / BLOCKED`, and technical rating `6/10` are unchanged.

## Remaining integration work

- Define and review a distinct operator-controlled service registration procedure. The runtime role remains read-only; the P01 `devobs_migrator` is migrations-only, so this implementation deliberately adds no row-write privilege or API.
- Connect an approved, authenticated metric-ingestion source to the Python authorization context. This route currently proves authorization for a path tuple but receives no service telemetry and invokes no AI-9 component.
- Complete the Node/Python event and confirmation boundary, with durable delivery/recovery and an authorized service identity, under a separate preregistered change.
- Hosted OIDC/JWKS, actual RLS policy, TLS/network restrictions, automatic spend enforcement, backup restore, and P01 live checks remain unverified and unauthorized. AI-9 quality still requires recovery of its actual evaluator/source and an admissible preregistered evaluation; this route does not resolve its failed Precision/FPR gates.
