# AI-9 Service Authorization API v1 — Preregistration

**Status:** Registered before implementation and behavioral testing. This is a repository integration contract, not an AI-9 quality evaluation or production authorization.

- Policy version: `ai9-python-service-authorization-api-v1`
- Base: `main` at `2bc56e8e9be1c24880c5e245ec22fd1f9af8d401`
- Scope: connect the existing authenticated Python WSGI boundary to the tenant-scoped PostgreSQL service registry using the existing read-only `authorize_service` method.
- Exclusions: no detector, confirmation policy, thresholds, evaluator, AI-9 quality result, P01 decision, schema/migration, service registration data, cloud resource, secret, deployment, or live integration changes.

## Contract fixed before implementation

Add one read-only route:

```text
GET /v1/tenants/{tenant}/projects/{project}/services/{service_id}/authorization
```

The route will:

1. Accept only the existing RS256 access-token format handled by `AccessTokenVerifier` and `RotatingOIDCVerifier`. The subject comes only from the verified principal. Tenant, project and service identifiers come only from the bounded route path; authorization headers, query parameters, and request bodies cannot override them.
2. Apply the existing process-local subject/tenant rate limit and in-flight limit before a store operation.
3. Call `tenant_gate.authorize_service(subject, tenant, project, service_id)` once. The deployed adapter is `PostgresTenantStore`; its existing read-only transaction and forced RLS policy remain the authorization authority.
4. Return `204 No Content` with an empty body and `Cache-Control: no-store` only when the method returns the literal boolean `True`.
5. Return the same generic `403 access_denied` response for a false result, invalid scope, missing registration, or missing tenant membership. No response distinguishes registry existence from membership.
6. Return `401 invalid_token` for absent or invalid bearer credentials, `405` with `Allow: GET` for other methods on this route, `404` for an unrecognized path, and generic `503 backend_unavailable` if the store errors or returns a non-boolean. Never expose exception or database details.

The endpoint is an authorization probe only. It does not accept telemetry, invoke the Node confirmation adapter, run the detector, or create an AI-9 alert. It adds no registry write path. Registration/removal remains a separately reviewed owner-controlled operation using an authorized database owner/migration identity after provisioning approval; no statement is run or registration row created in this step.

## Preregistered behavioral acceptance

Tests will verify:

- A valid signed synthetic token whose verified subject has access to the exact registered tenant/project/service tuple receives `204`, an empty body, and `Cache-Control: no-store`.
- A different tenant, project, service, unregistered tuple, or unlisted subject receives the same `403` response, with no store/service details in the body.
- Missing, malformed, or invalidly signed credentials receive `401` without calling the store.
- A method other than GET receives `405` and `Allow: GET`; unrelated paths remain `404`.
- Store exceptions and any return other than literal `True` or `False` fail closed as generic `503` without exposing exception text.
- The PostgreSQL integration test sends a cryptographically signed synthetic bearer token through the WSGI app and proves that the resulting request is authorized or denied by the existing RLS-backed service registry. The test remains in the disposable PostgreSQL CI fixture; it is not hosted staging evidence.

No benchmark/scorer, AI-9 seeds, synthetic fault windows, customer data, or real identities will be used. Test fixtures exercise route behavior only and do not produce Precision, Recall, FPR, or gate results. A passing suite will demonstrate this code contract only. **AI-9 remains FAIL; P01 remains NO-GO / BLOCKED; technical rating remains 6/10 unless separately evidenced.**

## Known boundaries after this step

- A populated service registry and safe owner-operated registration procedure are still prerequisites for real use.
- This route does not transport metrics or connect the Python API to the Node detector/confirmation components.
- Hosted OIDC/JWKS, live database/RLS, TLS/network policy, budget enforcement, backups/restore, and production traffic are not tested or authorized.
- A later integration must record its own preregistered contract, tests, source SHA, and authorization scope.
