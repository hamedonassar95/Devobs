# Devobs managed staging — Render Free + separate Supabase Free proposal

**Status: preparation only; no service or database is provisioned.** This document and [`render.yaml`](../render.yaml) describe a candidate P01 experiment; they do not create resources, connect provider accounts, enter secrets, enable billing, migrate data, or certify readiness. The user's prior approval selected Frankfurt for planning only: Render Frankfurt, Germany and Supabase `eu-central-1` (Frankfurt). It did not approve accounts, deployment, cost, customer data, or any service integration.

**P00 is governance-only GO. P01 remains NO-GO / BLOCKED** until the owner separately authorizes exact provider accounts, an eligible plan, spending conditions, data policy, and a particular create/deploy action. The USD $10/month amount remains a planning target, not a cap or payment consent. Render Free + Supabase Free is the preferred experiment to evaluate, not an approved deployment. All use contemplated here is **synthetic data only**.

## Proposed Render Free Blueprint

This local candidate Blueprint declares one Python web service in Frankfurt, `plan: free`, Render preview generation off, `autoDeployTrigger: off`, `/readyz` health checks, and the existing Gunicorn WSGI entrypoint. It declares no Supabase database. The six DB/OIDC environment variable names remain `sync: false` placeholders with no values. `staging_app.py` and its tests reject absent or unsafe DB/identity configuration; no defaults, real tenant, key, DSN, or JWKS are supplied here. The previously observed main Blueprint used Starter; neither version is an applied or live configuration.

Render Free lists 512 MB memory. The proposed start command uses one Gunicorn worker as a conservative starting point for that limit; the repository has no hosted memory/load measurement proving this sizing. Confirm memory, readiness, restart, and latency behavior only in a separately authorized synthetic staging exercise. This is not an availability or capacity claim.

**Creation can publish.** Creating/importing a Render web service is public-facing and can start an initial build and deploy even while `autoDeployTrigger: off`; that setting governs later automatic commits, not initial creation. Render Free services cannot receive private-network traffic. Free plan does not imply zero total cost: outbound egress and build usage can exceed included limits and may be billed if a payment method is present, or suspend services/builds otherwise. Free web services sleep after 15 minutes idle and can take about a minute to wake; the filesystem is ephemeral. **VERIFIED from owner-provided prior read-only evidence (planning only):** the “Primary” and “Render” connector aliases resolve to the same Render workspace, “My Workspace” (`tea-dafq4ue7bikc73d7tmig`), with “Render” used as the planning referent. Service listings returned null, so no Devobs service was verified; null does not prove none exists. **UNVERIFIED:** permission to create there, Free eligibility, and account-specific cost. Do not import this Blueprint until separately authorized for the exact account and create action.

`previews: generation: off` disables Render Blueprint previews only. It does not control a possible Vercel PR preview. No PR is opened in this task. Merging to `main` can separately publish GitHub Pages under the repository workflow.

## Supabase Free is a separate, future action

There is intentionally no Supabase project declaration in `render.yaml`. The proposed Supabase location `eu-central-1` is the Frankfurt geography selected for planning, not a project or account selection. No Supabase organization has been selected. A future operator would need a separately chosen/authenticated Supabase organization and explicit project-creation authorization. Do not guess an organization, connect an account, or create the project under this task.

If separately approved, begin with **synthetic fixtures only**. Supabase Free may pause after a week of low activity and has no managed Free-tier backups; plan export/restore separately before treating it as persistent staging. Free-plan eligibility, region availability for the specific account, and any associated usage charges remain **UNVERIFIED**. The $10/month target is not enforceable here. Render egress/build overages and any Supabase plan or usage charges must be reviewed for the specific accounts before creating resources.

### Supabase Data API, identity, and database controls

Supabase's Data API is a public API surface if enabled and granted access. Its documentation describes default grants for roles such as `anon`, `authenticated`, and `service_role`; an RLS policy alone does not replace explicit grants/schema review. Before permitting even synthetic data, decide whether the Data API is needed. If enabled, expose only the intended schema and review every table/function grant and policy; test unauthenticated and cross-tenant access. Before any real data, require approved `ENABLE` and `FORCE ROW LEVEL SECURITY`, a restricted non-owner/non-superuser/non-`BYPASSRLS` runtime role, least-privilege grants, and live negative tenant-isolation tests. No hosted database or policy has been examined.

The Render environment placeholders are not a key lifecycle. Before any service create, OIDC issuer, audience, client identity, metadata/JWKS provenance, signature validation, rotation, overlap, and revocation behavior must be designed and owner-approved. Missing values must keep the API unavailable rather than falling back to anonymous or mock access. Never put secrets or connection details into this file, Git, tests, tickets, or logs.

Render-to-Supabase traffic crosses providers; it is not Render private-network transport. Require `sslmode=verify-full` with an independently trusted CA and verify TLS/network routing in an authorized live test. Before any public endpoint is used, approve its exposure, authentication, rate/body limits, abuse response, log redaction, and cancellation/rollback procedure.

## Required gates before any future create action

Keep each item unresolved until an owner explicitly decides it. A document or passing synthetic test does not authorize the action.

1. Select the exact Render workspace/account and Supabase organization/project; verify Free plan eligibility, geography, terms, and account-specific cost.
2. Agree on the $10/month planning target's status and a practical cost-stop policy. Render's documented build-pipeline spend limit is not a total account cap; monitor-only alerts are not a hard ceiling. Confirm egress/build behavior and payment method consequences.
3. Approve synthetic-only data handling, retention/deletion, public access, secrets storage, OIDC/JWKS lifecycle, TLS trust, network restrictions, and incident owner.
4. Review Supabase Data API exposure, schema grants, RLS policies, database roles, and the reviewed migration before any project receives data. Do not run the migration until separately authorized.
5. Design and rehearse backups/restoration and deletion/cancellation. Supabase Free has no managed backups; test and accept the consequences before relying on persistence.
6. Require live authenticated tests for liveness/readiness, DB availability, valid/invalid tokens, key rotation, request limits, sanitized logs, runtime role, and negative cross-tenant reads/writes before calling staging accepted. Keep customer data prohibited unless separately authorized.
7. Obtain a separate owner decision on Vercel preview visibility before opening any PR. Obtain a separate explicit approval before any Render create/import or deploy; auto-deploy off is not initial-deploy approval.

The original Blueprint must not be imported unchanged based on geography-only consent. Creating the Render service can publish an initial build; no provider operation was performed or authorized here.

## Offline checks and their limits

- `tests/test_render_free_staging_blueprint.py` parses the YAML and checks the single Free Frankfurt service, retained guards, safe worker command, required `sync: false` variable names, and absence of a Supabase resource.
- `tests/test_intelligence_staging_app.py` covers fail-closed configuration and local WSGI behavior.
- `tests/test_intelligence_staging_smoke.py` exercises a six-call synthetic response sequence. The related API security, tenant scope, and disposable PostgreSQL tests are also local/CI fixtures.

These checks do not create a provider service, validate account eligibility, test hosted TLS/OIDC/JWKS, prove a managed database's RLS state, or establish live backup/restore, billing, isolation, availability, or SaaS readiness.

## Official references

- [Render Free services and limits](https://render.com/docs/free)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Render regions](https://render.com/docs/regions)
- [Render pricing](https://render.com/pricing)
- [Supabase regions](https://supabase.com/docs/guides/platform/regions)
- [Supabase backups](https://supabase.com/docs/guides/platform/backups)
- [Supabase Data API security](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase cost control](https://supabase.com/docs/guides/platform/cost-control)
- [Supabase PostgreSQL connection and TLS](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement)
