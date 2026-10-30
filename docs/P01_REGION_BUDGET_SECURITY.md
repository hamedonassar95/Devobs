# P01 Render + Supabase Region, Budget, and Security Decision

> **Superseded planning snapshot (2026-10-30):** this document's USD 10/month planning target and Render + Supabase preference are historical, not the current owner budget/provider decision. The owner has conditionally approved a USD 100/month total ceiling with P01 **NO-GO / BLOCKED** pending enforcement evidence; Railway in Amsterdam is under evaluation only. See [P01_ACTIVATION_READINESS.md](P01_ACTIVATION_READINESS.md) and the [Railway spend-enforcement evidence](P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md). No resource creation or spend is authorized.

**Evidence checked:** repository source at main `1eaad2c95da559095aa2160f81bdda62d064dcee`; public provider documentation checked 2026-10-27. Public prices and product limits may change. Prior owner-provided read-only Render workspace evidence is summarized below. No billing console, service settings, secrets, or environment settings were accessed.

## Decision boundary

**VERIFIED — default state: NO-GO / BLOCKED.** The owner's [P00 decision](P00_OWNER_DECISION.md) approves repository governance with bounded residual risks only. It does **not** authorize P01, provider accounts, resources, payments, data transfer, secrets, migrations, deployments, service integrations, or paid AI. This packet records only the bounded geographical planning choice below; it does not record operational P01 approval.

**VERIFIED — owner planning input:** USD **$10/month is a target for planning only**. It is not approved spend, a hard financial cap, billing consent, or permission to provision. The current experimental preference is Render Free + Supabase Free with synthetic data only, subject to verified eligibility, security readiness, and separate live-create authorization. This is a planning preference, not an approved account, deployment, or plan enrollment; account eligibility and billing configuration remain **UNVERIFIED**.

**VERIFIED — repository history and local candidate:** at the stated main baseline, [`render.yaml`](../render.yaml) declared a Render web service with `plan: starter`, Frankfurt, `autoDeployTrigger: off`, and Render preview generation off. The unmerged candidate in this consolidation changes the proposed plan to `free` while retaining Frankfurt and both publication guards. Neither file state represents a live service or provisioning authorization; the file declares **no Supabase resource**. [`docs/RENDER_SUPABASE_STAGING.md`](RENDER_SUPABASE_STAGING.md) describes Supabase as a separate future project. Any phrase such as “managed services selected” means an architecture preference only, not account, payment, deployment, or activation approval.

## Cost and operating-shape comparison

Published list prices below were checked on 2026-10-27. They are not quotes or account-specific eligibility. “Base” excludes usage overages, tax, add-ons, and any unlisted provider/account charges.

| Option | Published base estimate | Limits and budget assessment |
| --- | --- | --- |
| **A. Offline synthetic only** | **$0 provider spend**; no provider resources or external calls | Lowest-risk next step. It can validate local contracts, but cannot pass live staging acceptance. |
| **B. Render Free web + Supabase Free** | **$0 base subscription/compute** on the listed Free tiers | Not a guaranteed zero invoice or continuously available staging. Render Free web sleeps after 15 minutes idle; its free hours, builds, and outbound bandwidth are limited, and bandwidth/build excess may be billed when a payment method is present or services/builds may be suspended otherwise. Supabase Free has project/database/egress limits, may pause after seven days of low activity, and lacks automatic backups. Account eligibility is **UNVERIFIED**. |
| **C. Render Starter web + Supabase Free** | About **$7/month** published Render web compute + $0 Supabase Free; roughly **$3 nominal headroom** against the $10 planning target | The $3 is arithmetic only, not enforceable headroom. Render bandwidth/build and other variable use can exceed it. Supabase Free inactivity/backup limits remain; this does not meet a tested recovery requirement. |
| **D. Render Starter web + Supabase Pro** | About **$32/month before variable use**: Render web compute from $7 + Supabase Pro from $25 for one database-only project on Micro compute | Exceeds the $10 target before overages/add-ons/tax. Supabase Pro includes a $10 monthly compute credit covering one Micro instance; do not add the $10 Micro price again for this one-project estimate. Pro adds daily backups (listed as seven days), but backup and restore still require an approved, tested procedure. |

**VERIFIED — documented cost-control limits:** Render documents a monthly spend limit for build-pipeline minutes; that is not a cap on running-service compute or outbound bandwidth. Render bills outbound bandwidth above included usage when a payment method is linked; without one, it describes service suspension instead. Supabase's Pro Spend Cap blocks only selected quota-based items (such as disk, egress, logs, storage, and selected invocations); it excludes compute and PITR as well as other listed items, so it is not a fine-grained total-dollar ceiling. **UNVERIFIED:** an account-level mechanism that guarantees this stack's total bill will never exceed USD $10. Alerts and usage dashboards are monitoring, not a hard cap.

**Assessment:** none of B–D is demonstrated to stay within the $10 target with an enforceable total-cost stop. A is the only option in this comparison with a known zero provider charge because it provisions nothing. The Free + Free pair is the current experiment preference for further evaluation, not an operational selection. P01 remains blocked until the owner makes the independent decisions below.

### Public provider evidence (checked 2026-10-27)

- [Render pricing](https://render.com/pricing): Hobby workspace listed at $0/month plus compute; web compute from $7/month; Postgres compute from $6/month. [Free service limits](https://render.com/docs/free) describe idle spin-down, monthly usage limits, and Free Postgres expiration/no backups. [Regions](https://render.com/docs/regions) lists Frankfurt and says an existing service/database cannot be moved in place. [Outbound bandwidth](https://render.com/docs/outbound-bandwidth) explains included quota, overage billing, or suspension without a payment method. [Build-pipeline spend limit](https://render.com/docs/build-pipeline) applies to pipeline minutes, not total service spend.
- [Supabase pricing](https://supabase.com/pricing): Free is listed at $0/month with usage limits and inactivity pause; Pro starts at $25/month and includes $10/month in compute credits for one Micro instance. The page lists daily backups for seven days on Pro and a separate paid PITR add-on. [Cost control](https://supabase.com/docs/guides/platform/cost-control) enumerates Spend Cap coverage and exclusions. [Regions](https://supabase.com/docs/guides/platform/regions) identifies `eu-central-1` as Central EU (Frankfurt) and warns that region selection is a data-location control, not proof of regulatory compliance. [Free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing) explains pausing after low activity over seven days. [Backups](https://supabase.com/docs/guides/platform/backups) describes daily backup and restore limits.
- [Supabase connection security](https://supabase.com/docs/guides/database/connecting-to-postgres) and [SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement) are relevant to a future connection. The repository proposal requires `sslmode=verify-full` and a trusted CA; no cross-provider connection has been tested.

These public pages establish advertised product behavior only. They do not establish current account eligibility, contractual residency, actual account settings, an invoice limit, service availability, or Devobs readiness.

## Owner geographical planning decision — recorded 2026-10-27

**VERIFIED — owner response in this task:** on 2026-10-27 the owner replied **“اوفق”** to the question approving this region pair for P01 planning: Render **Frankfurt, Germany**, and Supabase **Frankfurt, Germany (`eu-central-1`)**. The [Render region documentation](https://render.com/docs/regions) lists Frankfurt, Germany; Supabase's [official region list](https://supabase.com/docs/guides/platform/regions) maps Central EU (Frankfurt) to `eu-central-1`.

This is approval of a geographical preference for planning only. It is **not** consent to create a Render service or Supabase project, deploy/import a Blueprint, enable a trial or paid plan, connect provider accounts, set a payment method, process or transfer customer data, or incur charges. It does not confirm regulatory/privacy compliance, account eligibility, or deployment permission.

**VERIFIED — owner-provided prior read-only Render workspace disambiguation (planning referent only):** connector aliases “Primary” and “Render” resolved to the same workspace, “My Workspace” (`tea-dafq4ue7bikc73d7tmig`); the “Render” connector is the planning referent. `list_services` returned null for both aliases, so no Devobs service was verified; null does not conclusively prove absence. This does not authorize a create action. **UNVERIFIED:** the intended Supabase organization and permission to create resources in either provider account.

**VERIFIED — blueprint caution:** the main baseline specified the paid Starter plan; this consolidation candidate proposes the Free plan in Frankfurt with `autoDeployTrigger: off` and previews disabled. It does not provision Supabase. The region-only consent does **not** authorize importing/applying either Blueprint: the exact account, eligibility, budget controls, secrets, data handling, and operational gates remain undecided.

Render private networking is for Render services in its own region. A Supabase database hosted by another provider is not on that Render private network; treat the connection as cross-provider network traffic and require TLS certificate verification (`sslmode=verify-full`) with an independently trusted CA. Actual routing, TLS, ingress controls, and connectivity are **UNVERIFIED**.

## Owner decision checklist — remaining fields blank

Only the geographical planning decision above is recorded. Every operational checkbox and all remaining owner fields/signatures below remain unselected or blank. Completing this checklist records a decision; it does not itself create resources. Any future provisioning requires separate explicit action authorization.

- [ ] **Provider/account:** Render workspace and authorized account owner: `____________________`; Supabase organization/project owner: `____________________`.
- [x] **Location for planning only:** owner approved Render Frankfurt, Germany + Supabase Frankfurt, Germany (`eu-central-1`) on 2026-10-27. Exact residency/jurisdiction and privacy/legal review: `____________________`.
- [ ] **Plan and scope:** assess the Render Free + Supabase Free experiment preference, then record exact Render service plan and Supabase plan/compute/database scope: `____________________`. Confirm no Blueprint import or Supabase creation until separately authorized: `____________________`. Preference does not select or enroll an account.
- [ ] **Budget:** keep USD $10/month as planning target, revise it, or defer: `____________________`. Owner-approved maximum monthly spend (if any): `____________________`. Provider-enforced total-cost stop mechanism and verified coverage: `____________________`. If no hard cap exists, explicit residual-cost acceptance and stop/delete procedure: `____________________`.
- [ ] **Cost inventory:** decide how to account for compute, builds, public egress, storage/disk, backups/PITR, logging, domains, taxes, and all overages: `____________________`.
- [ ] **Data/privacy:** synthetic-only data allowed? `____________________`; data classes/PII prohibited, retention, deletion, residency, provider terms/DPA and responsible privacy approver: `____________________`.
- [ ] **Service access:** public/private exposure, allowlists, authentication policy, request/body/rate limits, abuse response, and health endpoint exposure: `____________________`.
- [ ] **Secrets and identity:** secret storage outside Git and rotation owner: `____________________`; IdP issuer/audience/client policy, OIDC metadata trust, JWKS rotation/overlap/revocation: `____________________`.
- [ ] **Database:** distinct migration and restricted non-owner/non-superuser/non-`BYPASSRLS` runtime role; minimum grants; `ENABLE` and `FORCE ROW LEVEL SECURITY`; live negative cross-tenant/read/write tests; TLS `verify-full` and trusted CA distribution: `____________________`.
- [ ] **Recovery/operations:** backup plan and retention, successful restore rehearsal, RPO/RTO, monitoring/incident owner, rollback/cancel/delete authority and evidence retention: `____________________`.
- [ ] **Release/publishing:** keep Render `autoDeployTrigger: off`; approve/decline Vercel preview visibility before any PR; name the human responsible for explicit pre-production/staging release approval: `____________________`.
- [ ] **Decision:** `NO-GO / BLOCKED` (default) / authorize a specifically scoped next planning task only: `____________________`. Owner, UTC date, and review reference: `____________________`.

## What offline evidence does and does not establish

**VERIFIED — offline contract:** [`docs/STAGING_ACCEPTANCE.md`](STAGING_ACCEPTANCE.md) documents a six-call synthetic smoke sequence using fake response tuples and no network, DNS, provider, or IdP calls. It checks health/readiness, anonymous denial, a synthetic authorized read, existence of a denied-tenant fixture, and cross-tenant denial. The source packet recorded a prior local run of 38 tests across [staging smoke](../tests/test_intelligence_staging_smoke.py) (12), [application bootstrap](../tests/test_intelligence_staging_app.py), [API security](../tests/test_intelligence_api_security.py), and [tenant scope](../tests/test_intelligence_tenant_scope.py). These tests remain synthetic/offline contracts; they do not establish hosted tenancy or active staging.

**UNVERIFIED — live acceptance:** those tests do not establish hosted service availability, real OIDC/JWKS authenticity or rotation, TLS/network configuration, managed database permissions, live RLS isolation, rate limits, backups/restore, monitoring, deletion, or billing controls. The disposable PostgreSQL RLS CI tests are also not proof of a hosted database; the proposed schema is [`001_tenant_rls.sql`](../deploy/postgres/001_tenant_rls.sql). See the [RLS staging gate](POSTGRES_RLS_STAGING.md), [staging proposal](RENDER_SUPABASE_STAGING.md), and [SaaS readiness limits](PRODUCT_SAAS_READINESS.md).

**VERIFIED — Pages publication boundary:** at this baseline, [`ci.yml`](https://github.com/hamedonassar95/Devobs/blob/1eaad2c95da559095aa2160f81bdda62d064dcee/.github/workflows/ci.yml#L445-L457) runs the production-release reusable workflow on a successful push to `main`. A future main merge can therefore publish static Pages. **UNVERIFIED — Vercel:** the owner-provided process warning is that opening a PR may create an external preview; current provider-side triggers and preview visibility were not inspected. Vercel is outside `render.yaml`. No PR, merge, provider change, or deployment is authorized here.

## Future AI intelligence gates — planning only

The user's research recommendations remain future gated milestones, not this P01 authorization: P13 tenant-scoped/redacted OpenTelemetry; P14 offline anomaly baselines and false-positive measurement; P15 advisory incident analysis with human-reviewed fixes; P16 deterministic Trivy/CodeQL/OPA with AI advisory only; P17 measured FinOps with enforceable budget controls; P18 scoped code/IaC copilots; P19 versioned evaluation, audit, feedback, prompt records, and rollback. Tenant isolation, provenance, privacy, prompt-injection defenses, human approval, and cost controls apply throughout. GPT-6.1 Terra/Copilot/API eligibility, price, endpoints, performance, and safety claims remain **UNVERIFIED**; no model calls or integration are approved.

## Single next owner choice

**Next owner choice:** select or defer a staging plan/cost approach against the USD $10/month planning target, including whether an enforceable total-cost stop can be demonstrated or whether the managed option is unsuitable. This is still a decision request only—not payment consent or provisioning permission. Keep P01 **NO-GO / BLOCKED** until all independent budget, privacy, identity, database, recovery, exposure, and release gates above receive explicit decisions.

### Official references

- [Render Free services](https://render.com/docs/free)
- [Render regions](https://render.com/docs/regions)
- [Render outbound bandwidth](https://render.com/docs/outbound-bandwidth)
- [Render pricing](https://render.com/pricing)
- [Supabase pricing](https://supabase.com/pricing)
- [Supabase cost control](https://supabase.com/docs/guides/platform/cost-control)
- [Supabase regions](https://supabase.com/docs/guides/platform/regions)
- [Supabase Free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Supabase backups](https://supabase.com/docs/guides/platform/backups)
