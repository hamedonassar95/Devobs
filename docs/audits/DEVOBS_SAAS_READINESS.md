# Devobs — SaaS readiness audit

Audited SHA: `10f8dd9b1e884e16cea3ffd847cf20405794cb8b` (VERIFIED). Statuses are source/offline evidence only; no hosted tenant, billing or identity runtime was exercised. Commercial readiness is owner-signed **NO-GO**.

## Capability matrix

| Capability | Implementation / evidence | Status | Missing requirements | Priority |
| --- | --- | --- | --- | --- |
| Organizations / tenants / users | `deploy/postgres/001_tenant_rls.sql:4-56` (`project_ci`, `memberships`, forced RLS); `scripts/devobs_intelligence/tenant_scope.py:13-142` roles viewer/operator/owner, `execute()` always denies | PARTIAL | No signup/provisioning/organization lifecycle; no hosted identity binding | P1 |
| Tenant isolation (RLS) | Forced default-deny policies with `current_setting`; `postgres_store.py:82-139` verifies role, privileges, RLS and pinned policy body; disposable CI PG test | PARTIAL | Hosted cross-tenant denial on reviewed SHA; LOGIN-tenant binding; global (not per-process) rate limit | P1 |
| Authentication (OIDC) | `oidc_tokens.py:29-96` public-RSA JWKS, RS256 `at+jwt`, strict issuer/audience/exp ≤ 900s/jti/scope; Keycloak profile docs + offline verifier | PARTIAL | Real issuer/JWKS/callback/signed-token behavior; historical staging `invalid_staging_config stage=oidc` | P1 |
| Authorization (RBAC) | `tenant_scope.py:106-137` injected resolver; `propose_change` needs operator/owner; no model may grant capabilities (`policy.py:1`) | PARTIAL | Live identity resolver; API route wiring for mutations | P1 |
| Administrative roles | Owner/operator/viewer defined offline; restricted actions in `check_two_agent_tasks.py` and `audit_store.py:332` deny billing/permission changes | PARTIAL | Hosted admin UI/API and ruleset enforcement | P1 |
| Subscription / billing | `docs/PRODUCT_SAAS_READINESS.md:12` "Stripe billing and metering not configured"; `:25-33` plans DRAFT, "No billing system exists" | MISSING | Processor, signed webhooks, idempotent invoices, plan quotas, reconciliation, refunds, cancellation | P1 (pre-sales) |
| Usage metering / quotas | Per-process rate limiters `api_app.py:207,233,251`; `agent-spec.yaml:4-10` boolean budget flag, `estimated_cost_usd_per_run: null` | PARTIAL | Token usage capture, per-tenant USD ledger, enforced quotas/dollar cap | P0 |
| Account lifecycle | `docs/PRODUCT_SAAS_READINESS.md:16-23` target onboarding only; `docs/ENTERPRISE_OPERATIONS.md:68` requires policy/tests before customer signup | MISSING | Signup, consent, suspension, deletion, ownership transfer — implemented and tested | P1 |
| Data retention / deletion | TTLs only: approvals 7d (`incident_memory_approval.py:27`), encrypted memory (`incident_memory_encryption.py:126-152`); audit chain local (`audit_store.py:1-90`) | MISSING | Tenant export/delete, retention policy, hosted audit retention | P1 |
| Backup / restore | `docs/ENTERPRISE_OPERATIONS.md:55-60` no restore drill; `docs/p01/p01-no-go-matrix-2026-11-19.json:44-49` BACKUP BLOCKED; Render Free has no managed backup | BLOCKED | Encrypted 7-day hosted backup, isolated restore, RPO/RTO | P0 |
| PostgreSQL retention deadline | `docs/p01/render-free-expiry-snapshot.json` expiry `2026-12-05T10:33:24.202776Z`; fresh `check_render_free_expiry.py --json` → `REVIEW_REQUIRED`, exit 1; plan `docs/plans/2026-11-19-render-free-postgres-retirement-plan.md:3,13` planning-only | BLOCKED | Owner preserve-or-retire decision naming exact resource/date; no backup exists | P0 |
| Cost control | `docs/P01_RENDER_BUDGET_ENVELOPE.md:3-21` targets (70/80/100 USD) explicitly not provider limits; `render.yaml:19-24` `DEVOBS_AI_BUDGET_APPROVED: "false"` | BLOCKED | Enforced combined cap including Render/OpenAI/backup/fees/tax; maintain USD 0 activation | P0 |
| Legal / licensing / privacy | `docs/PRODUCT_SAAS_READINESS.md:39-45`: privacy/terms/DPA unapproved, licensing audit unresolved | BLOCKED | Legal review before any external customer | P0 |
| Commercial go/no-go | `docs/PRODUCT_SAAS_READINESS.md:3,47-49` "Not yet sellable"; all criteria BLOCKED; ledger `p01-managed-saas: BLOCKED` | BLOCKED | All P01/AI-9/Codex gates + owner approval | P0 |
| Console UX for SaaS | `apps/ai-intelligence-console`: Arabic RTL + `DEMO ONLY` banner (`index.html:2`, `App.tsx:448`), preview-only restart/redeploy/rollback; mock server data | PARTIAL | English LTR toggle MISSING, per-panel synthetic/live badges, approval queue UI | P2 |

## External customer readiness statement

No customer onboarding, payment collection, retention deletion, or hosted tenant acceptance exists on a reviewed SHA. The documented "synthetic/disposable" classification of the expiring Render database is **not** a deletion authorization. Selling or activating paid services is prohibited without the owner's exact-SHA, exact-scope decision.

## Evidence commands (fresh)

- `python scripts/check_render_free_expiry.py --json` → `{"status":"REVIEW_REQUIRED","expires_at":"2026-12-05T10:33:24.202776Z","paid_activation_authorized":false,"production_approved":false,"provider_access_performed":false}`, exit 1.
- `python scripts/milestone_ledger.py --summary` → `p01-managed-saas: BLOCKED`, 3 open gates, exit 0.

## Not verified

Hosted signup/login, live RLS denial, Stripe/webhook behavior, deletion/export execution, backup restore, SLO attainment, legal approval. All four remain BLOCKED or MISSING above; none is claimed as passing.
