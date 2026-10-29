# P01 Managed Staging: Owner Activation Decision

**Decision status: NO-GO / BLOCKED by default.** This is an unsigned preparation packet, not an authorization to create services, transfer data, spend money, deploy a P01 service, or enable AI. The repository baseline used when this packet was prepared was `origin/main` [`1eaad2c95da559095aa2160f81bdda62d064dcee`](https://github.com/hamedonassar95/Devobs/commit/1eaad2c95da559095aa2160f81bdda62d064dcee). **Current repository evidence was refreshed on 2026-10-29 at `main` `837e9790ce45fbc7fa624fdf68db1c3b5b396105`**; repository checks do not establish P01 provider settings or service health.

## Authorization boundary

**VERIFIED:** The owner recorded P00 GO with bounded repository-governance risks in the [P00 decision comment](https://github.com/hamedonassar95/Devobs/pull/277#issuecomment-6423508484) and [decision packet](P00_OWNER_DECISION.md). That decision does **not** approve P01, staging resources, a provider/account, data transfer, a deployment, a budget, service integrations, or AI/API inference. The canonical [P00–P12 roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md) keeps P01–P12 blocked pending separate approvals.

**ASSUMED for safety until explicitly decided:** absence of a completed checklist means **NO-GO**. A future GO must name its exact provider, service, region, budget enforcement, data scope, identity and runtime controls below. It authorizes only that bounded P01 staging scope; production release, customer data, commercial use, and P13–P19 remain outside scope.

## Evidence available now

| Area | Evidence and status | What it does not establish |
| --- | --- | --- |
| Staging architecture | **VERIFIED (proposal):** [Render + Supabase staging plan](RENDER_SUPABASE_STAGING.md) describes a read-only WSGI API, PostgreSQL RLS and OIDC/JWKS. `render.yaml` is proposed configuration, not a live service. | Provider eligibility, create authorization, contractual residency, or a deployed endpoint. |
| Provider workspace | **VERIFIED (owner-provided prior read-only evidence, planning reference only):** the “Primary” and “Render” connector aliases resolved to the same Render workspace, “My Workspace” (`tea-dafq4ue7bikc73d7tmig`). Service listings returned null, so no Devobs service was verified; null does not prove none exists. **UNVERIFIED:** create authorization and Supabase organization. | Workspace identification grants no creation permission and does not establish a service exists or is absent. |
| Synthetic tenant isolation | **VERIFIED (offline contract):** [STAGING_ACCEPTANCE.md](STAGING_ACCEPTANCE.md) and [`test_intelligence_staging_smoke.py`](../tests/test_intelligence_staging_smoke.py) exercise six mocked calls: liveness, readiness, anonymous denial, authorized tenant read, a separate denied-tenant fixture, then cross-tenant denial. The test uses queued synthetic responses and makes no network call. | Hosted tenancy, real identity, actual database RLS, TLS, network, or concurrent isolation. |
| Application and authorization | **VERIFIED (source/tests):** [`test_intelligence_staging_app.py`](../tests/test_intelligence_staging_app.py), [`test_intelligence_api_security.py`](../tests/test_intelligence_api_security.py), and [`test_intelligence_tenant_scope.py`](../tests/test_intelligence_tenant_scope.py) cover mocked startup/authentication and tenant-scope denial. | An operator-selected IdP, verified live issuer/JWKS lifecycle, or real user membership. |
| PostgreSQL boundary | **VERIFIED (source/CI fixture):** [RLS staging evidence](POSTGRES_RLS_STAGING.md) documents a restricted non-owner, non-BYPASSRLS reader, forced RLS and parameterized tenant/subject-scoped reads. [`test_postgres_rls_integration.py`](../tests/test_postgres_rls_integration.py) is a disposable-PostgreSQL integration suite. | A live managed database, its runtime role/policies, or production protection from direct SQL access. |
| Health and recovery | **VERIFIED (source contract):** offline tests distinguish liveness from readiness. The staging proposal requires real runtime-role checks and a restore rehearsal. | Live readiness, backup integrity, restore time, RPO/RTO, incident response, or rollback performance. |
| Spend, privacy and network | **UNVERIFIED:** no selected hard spend ceiling/enforcement, data classification, retention/deletion approval, or live network policy is evidenced by these source documents. | Do not infer a spend cap from an inference-authorization flag or a provider alert. |
| Publication / preview | **VERIFIED (runtime, 2026-10-29):** PR #290 produced a Vercel preview at [the PR preview URL](https://devobs-git-docs-readiness-evidence-after-pr-289-hamedonassar.vercel.app); merging it published the static Pages site and passed `verify-production` in [CI run 40964990632](https://github.com/hamedonassar95/Devobs/actions/runs/40964990632). **UNVERIFIED:** Vercel configuration, preview access controls and intended audience have not been independently inspected. | This confirms behavior for a repository documentation PR and static Pages only. It does not authorize a P01 endpoint, staging data, or customer access. See [Vercel Git integration docs](https://vercel.com/docs/git). |

### Repository publication evidence (2026-10-29)

- **VERIFIED:** PR #290 was documentation-only and merged as `837e9790ce45fbc7fa624fdf68db1c3b5b396105`. Main CI [run 40964990632](https://github.com/hamedonassar95/Devobs/actions/runs/40964990632) and separate CodeQL [run 40964990346](https://github.com/hamedonassar95/Devobs/actions/runs/40964990346) succeeded. GitHub Pages publication and production-site verification succeeded; the PR's Vercel preview is linked above.
- **Scope:** these results verify repository CI and static-site publication. No P01 service, database, provider resource, staging data transfer, paid inference, or customer data was created or used. **P01 remains NO-GO / BLOCKED.**

### Offline evidence versus live acceptance

The synthetic six-call contract is useful **offline acceptance evidence** for expected response shape and tenant-denial behavior only. Other safe preparation includes the staging-app/authentication unit tests and code review of the SQL policy. The PostgreSQL RLS integration suite requires a disposable PostgreSQL fixture (as used by CI); it is not a hosted-staging test. A passing test or CI run cannot replace live checks.

After separate authorization and provisioning, **live P01 evidence** must include: exact staged source SHA; TLS and hostname verification; readiness against the actual restricted runtime role; authenticated valid/invalid/expired-token tests; JWKS rotation and revocation behavior; the six-call sequence against the isolated staging service using synthetic identities/data; cross-tenant denial against real RLS, including same-project-name cases; denied writes; rate/request limits and redacted logs; controlled database/network failure handling; and a successful isolated backup restore with measured recovery objectives. Record exact commands, outputs, time, scope and approver without recording credentials.

## Owner decisions required before any P01 action

P01 provider, service, budget, data, identity, runtime and release values remain blank. The repository-only preview and Pages entries below record the owner's standing repository instruction; they do not grant a P01 GO. Attach evidence or an owner-approved reference for the remaining decisions. Do not put credentials, DSNs, tokens, keys, or private customer data in this document.

| Decision | Owner-selected value / evidence (blank) |
| --- | --- |
| Provider, account/workspace, service and authorized operator |  |
| Region, data residency and permitted data classification |  |
| Maximum monthly spend ceiling **and enforceable provider quota/cap mechanism**; alerting and stop procedure |  |
| PII/telemetry allowance, purpose, retention, deletion and privacy/legal approval |  |
| IdP, issuer/audience/client scope, trusted JWKS source, rotation/revocation and failure behavior |  |
| PostgreSQL runtime identity: non-owner, non-superuser, no `BYPASSRLS`, minimum read grants; migration owner and reviewed policy evidence |  |
| TLS/CA verification and allowed network ingress/egress, including private access restrictions |  |
| Backup encryption/retention and successful restore evidence; approved RPO/RTO |  |
| Readiness/liveness semantics, smoke-test target, failure thresholds and exact staged SHA |  |
| Incident owner/on-call path, stop conditions, rollback procedure and resource deletion authority |  |
| Independent release approver and approval mechanism; distinguish this from the implementer |  |
| Vercel preview visibility accepted before any push/PR? Scope and audience | The owner's standing repository instruction authorizes routine source/documentation PRs, CI, and merge; PR #290's preview was generated. Scope is limited to repository artifacts and synthetic/static content. This does not approve a P01 staging endpoint, staging data, or customer access. The Vercel access-control settings remain unverified. |
| Separate approval for any main merge that may publish GitHub Pages | The owner's standing repository instruction authorizes merge after green CI; PR #290's merge published and verified the static site. This is not approval to deploy a P01 service or create resources. |

### Unsigned decision record

- Decision: [ ] **GO for the bounded P01 scope above**  [ ] **NO-GO — remain blocked**
- Scope and exclusions:
- Owner identity:
- Independent approver (if applicable):
- UTC timestamp:
- Decision-time main SHA and exact required-check run:
- Evidence/approval reference:
- Owner signature/reference:

Until a human completes this record and gives separate explicit authorization for the specific action, P01 remains **NO-GO / BLOCKED**. A GO here is not a general production release, customer-data, billing, or AI-inference approval.

## Future AI roadmap boundary

These are future planning milestones only, not P01 requirements that activate an integration:

| Milestone | Future direction; not enabled |
| --- | --- |
| P13 | Per-tenant, minimized OpenTelemetry telemetry with data-quality checks. |
| P14 | Offline-baselined anomaly detection with measured false positives. |
| P15 | Read-only AI incident analysis and human-reviewed draft fixes. |
| P16 | Deterministic Trivy/CodeQL/OPA security gates; AI is advisory only. |
| P17 | FinOps recommendations with actual owner-approved spend limits and enforcement. |
| P18 | Least-privilege code/IaC copilots producing reviewable proposals only. |
| P19 | Auditable evaluation, feedback, prompt versioning and rollback evidence. |

The deep-research article is a **planning input**, not validation of vendor claims. GPT-6.1 Terra performance, security benchmarks, API syntax, eligibility, licensing and prices remain **UNVERIFIED** and are not used here. No model, Copilot, API, telemetry, payment, or cloud integration is activated. Preserve tenant isolation, redaction, prompt-injection defenses, provenance, cost enforcement and human approval as later-stage gates.

## Publication and P01 authorization boundary

The owner has authorized routine repository PRs, CI, and merges after green checks; PR #290 confirms that a repository preview can be generated and a merge can publish the static Pages site. This standing instruction covers repository artifacts and the existing static-site path only. **It does not authorize P01 resource creation, provider spend, data transfer, staging endpoints, paid AI, or customer access. P01 remains NO-GO / BLOCKED until the owner completes the decision record and separately authorizes the exact bounded staging scope.** See the [current Pages release source](../.github/workflows/ci.yml) and [P00 publication boundary](P00_OWNER_DECISION.md).

## References

- [Canonical P00–P12 execution roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md)
- [Offline staging acceptance](STAGING_ACCEPTANCE.md)
- [Managed staging proposal and prerequisites](RENDER_SUPABASE_STAGING.md)
- [PostgreSQL RLS implementation and limits](POSTGRES_RLS_STAGING.md)
- [Product/SaaS readiness blockers](PRODUCT_SAAS_READINESS.md)
- [PostgreSQL row security documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP API Broken Object Level Authorization guidance](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
