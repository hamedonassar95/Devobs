# AI-9 trusted identity and service-mapping audit

**Review baseline:** `main` at `72e1a5f2332441c6e4e04beab054e4e97458bc78` (2026-10-30). **Scope:** read-only source review to identify whether the new Node confirmation adapter can consume the repository's existing authenticated identity and service registry. No code, identity configuration, data, or service was changed.

## Findings

| Boundary | Verified source behavior | Missing for AI-9 integration |
| --- | --- | --- |
| AI-9 adapter | [`post_detector_confirmation_adapter.mjs`](../scripts/ai_intelligence/post_detector_confirmation_adapter.mjs) requires an injected `authorizeService` callback and passes it only a frozen `serviceId`. A repository search found its only executable consumer is the local contract test; there is no application route or production call site. | No caller supplies a verified principal or trusted callback. The callback is an interface seam, not authentication evidence. |
| OIDC verifier | [`oidc_tokens.py`](../scripts/devobs_intelligence/oidc_tokens.py) verifies RS256 access tokens against operator-supplied JWKS and returns an `AuthenticatedPrincipal` containing subject and scopes. | It is Python code and is not wired into the JavaScript AI-9 adapter. No provider tenant, client, or live JWKS lifecycle was verified in this review. |
| Existing API | [`api_app.py`](../scripts/devobs_intelligence/api_app.py) accepts only `GET /v1/tenants/{tenant}/projects/{project}/ci`, verifies a bearer token, and passes the verified subject, tenant and project to the tenant gate. | There is no AI-9 event ingestion or service-authorization route. The API is read-only and no internal service-to-service protocol exists. |
| Membership and registry | [`tenant_scope.py`](../scripts/devobs_intelligence/tenant_scope.py) models actor membership in a tenant and project IDs. [`postgres_store.py`](../scripts/devobs_intelligence/postgres_store.py) enforces RLS for the `memberships` and `project_ci` tables. | The current membership and database schema contain no tenant-to-service registry or metric-ingestion grants. A project ID cannot be assumed to authorize an AI-9 `serviceId`. |
| Metric batch | [`trusted_metric_batch.py`](../scripts/devobs_intelligence/trusted_metric_batch.py) is a bounded, offline parser. Its caller must supply trusted tenant, project, SHA and clock; it has no request endpoint or authentication. | No authenticated collector, service binding, source signature, persistent telemetry store, ingress quota, or hosted negative tenancy evidence. |
| Staging bootstrap | [`staging_app.py`](../scripts/devobs_intelligence/staging_app.py) requires operator-provided OIDC metadata/JWKS and a TLS-verified database DSN before startup. It performs no metadata fetch or resource provisioning. | Provider setup and service health are not verified; P01 remains blocked by the unproven combined spend stop and remaining owner controls. |

## Integration decision

The repository has two distinct application runtimes: the experimental AI-9 confirmation path is JavaScript, while the current authenticated read-only API and tenant store are Python. There is no trusted principal-to-service path between them. Passing `serviceId` across that gap or returning `true` from a local stub would not establish authorization.

**Recommended direction for a future offline implementation:** keep token verification and tenant/service membership checks at the existing Python API boundary, add an explicit tenant-scoped service registry under reviewed RLS, and only then choose how the AI-9 state machine is hosted. Porting the deterministic confirmation component into the Python service keeps one identity boundary; a separate Node process would instead require a defined authenticated, audience-bound, replay-resistant internal protocol and its own operational controls. Neither design is implemented or activated here.

Before the next code change, the implementation scope must say which runtime owns the confirmation state and how the authenticated subject is bound to `(tenant_id, service_id)`. Until then, do not connect the callback to provider tokens or treat project membership as service membership.

## Status and limits

- **AI-9: FAIL.** This source review does not run an evaluator or alter quality gates.
- **P01: NO-GO / BLOCKED.** No live identity, service, database, network, or cloud resource was accessed or created.
- All identity and membership behavior cited above is source/test evidence only. It does not prove provider configuration, live authentication, hosted RLS, or service health.
