# Devobs Production Execution Roadmap Implementation Plan

> **For agentic workers:** Execute only the single active phase and its named next task. Do not start a later phase until the preceding phase's exit evidence and human signoff are recorded. Read-only exploration does not promote a gate.

**Historical evidence snapshot:** 2026-10-26 11:53 UTC; `main` = `8f1c22fd3d2cabf1c9a7a2fea6c69669e6cba272` ([commit](https://github.com/hamedonassar95/Devobs/commit/8f1c22fd3d2cabf1c9a7a2fea6c69669e6cba272)). The PR states below preserve what was observed then; they are not current state.

**Current P00 refresh:** 2026-10-26 12:07 UTC; `main` = merge commit `d948aebeb046e9d2a224dcbb89f5dc805bcfa147` from #264. PR #264 head `5f25d5c018a8f0600898592b228d4d1636f0274e` was merged by `hamedonassar95`; GitHub records no submitted human review. Its CI run [40315830867](https://github.com/hamedonassar95/Devobs/actions/runs/40315830867) passed `validate` on that exact head, and post-merge run [40319674325](https://github.com/hamedonassar95/Devobs/actions/runs/40319674325/job/121561314112) passed `validate` on the merge commit. The bot explicitly said AI review was skipped because budget approval was absent ([comment](https://github.com/hamedonassar95/Devobs/pull/264#issuecomment-6414977830)); workflow success is not an AI review. **VERIFIED:** these are GitHub/API facts. **UNVERIFIED:** whether any approval occurred outside GitHub's review records. The merged PR adds offline synthetic acceptance tests and documentation; it is not evidence of live staging or production.

## Goal

Reach a reviewed, measured, tenant-isolated and human-operated Devobs service suitable for a controlled internal pilot; only after a separate commercial gate consider customer launch. The repository does not currently establish a deployed multi-tenant API or commercial SaaS. **VERIFIED:** current main has a static GitHub Pages site, Python read-only intelligence/API source, CI, PostgreSQL RLS integration coverage and proposed staging configuration. **UNVERIFIED:** managed staging, live identity, service uptime, commercial operations and production readiness. Source and synthetic tests do not prove deployment.

## Architecture

**VERIFIED (source/proposal):** keep GitHub Actions `validate` as the required source gate; proposed Render WSGI staging serves a read-only API backed by proposed Supabase PostgreSQL 17+ with tenant RLS and operator-configured OIDC/JWKS. `render.yaml` sets `autoDeployTrigger: off`; it is a proposal, not a configured service. Static Pages remains separate from API hosting. Add tenant-scoped telemetry, provenance, governance, audit and controlled operations only as approved, reviewed increments.

## Tech Stack

**VERIFIED in repository:** Python 3.12, WSGI/Gunicorn, PostgreSQL 17 CI fixture, OIDC/JWKS validation, GitHub Actions, unittest, Trivy image scan and Terraform validation. **PROPOSED:** managed Render runtime, Supabase PostgreSQL, approved OpenTelemetry pipeline, and any model/payment provider. No provider or model is presumed configured.

## Global Constraints

- One `feature/<short-task-name>` branch per PR-sized task; fewer than 500 changed lines per commit. Test first when behavior changes. Open Draft PRs, obtain human review/decision, and require passing `validate` on the exact head SHA before phase promotion.
- One phase only is active. No later phase begins until the previous phase's acceptance evidence and owner signoff are recorded. Offline or read-only inspection is not gate promotion.
- **STOP immediately** on CI failure, cross-tenant access, missing/ineffective RLS, invalid JWT/JWKS trust, exposed credentials, absent restore evidence when required, unauthorized spend, missing human owner decision, or unapproved model write/action. Keep the phase blocked; do not weaken tests or bypass controls.
- Never read or alter secrets, GitHub Environments, deployment settings, provider configuration, billing, or cloud resources without separate explicit authorization. This plan performs no provisioning, migration, Terraform apply/destroy, deployment, merge, rule change, or inference purchase.
- Models have no execution authority. Outputs are advisory; production changes require separate signed, scoped authorization and a human-controlled release path.
- Owner decisions are required for each stage's cost, privacy, safety and release gate. The repository ruleset currently requires PR plus strict `validate`, but zero independent approvals and no Code Owner review. **VERIFIED:** repository rules API at snapshot; **UNVERIFIED:** external organization/enterprise policy and whether independent review is available. Do not assume another reviewer or alter rules.
- Source references below distinguish **EXISTING** interfaces/evidence from **PROPOSED** additions. “Acceptance evidence” is a required future artifact, not a claim it exists.

## Evidence baseline and open PR queue

**VERIFIED — historical baseline at 11:53 UTC:** `main` was `8f1c22fd3d2cabf1c9a7a2fea6c69669e6cba272`; [run 40314817447](https://github.com/hamedonassar95/Devobs/actions/runs/40314817447) passed `validate` on that exact SHA. This is not the current main after #264 merged. The effective rules response then was [`GET /repos/hamedonassar95/Devobs/rules/branches/main`](https://api.github.com/repos/hamedonassar95/Devobs/rules/branches/main); ruleset [24507159](https://github.com/hamedonassar95/Devobs/rules/24507159) required PR and strict `validate`, blocked deletion/non-fast-forward, and reported zero approving reviews, Code Owner review false, and an empty bypass actor list. These are returned repository-level fields only; they do not establish hidden external policies. GitHub documents [rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

**VERIFIED — queue at the historical 11:53 UTC snapshot:** #264 OPEN DRAFT, head `5f25d5c018a8f0600898592b228d4d1636f0274e`, `validate` passed in [run 40315830867](https://github.com/hamedonassar95/Devobs/actions/runs/40315830867/job/121548303624); its AI review job was skipped because explicit budget approval was absent ([bot comment](https://github.com/hamedonassar95/Devobs/pull/264#issuecomment-6414977830)); no human review was submitted. #259 OPEN, head `5b3bb1cf79c26cb2daa8daf314dfe8e6a8506866`, `validate` passed in [run 40314109382](https://github.com/hamedonassar95/Devobs/actions/runs/40314109382/job/121542501808), then behind main. #262 OPEN DRAFT, head `b5a1b9ea27ef2b26c9bbcfe1b7a218b705c8ffe0`, `validate` passed in [run 40313425421](https://github.com/hamedonassar95/Devobs/actions/runs/40313425421/job/121540193207), then dirty against main. #253 OPEN, head `78483b69ca8a61eef32c787a982e08520b1264cc`, then dirty against main; its Trivy work overlaps merged [#255](https://github.com/hamedonassar95/Devobs/pull/255). These are historical observations only; refresh all states and checks before review. No PR is to be blindly merged or closed.

**VERIFIED — refreshed queue at 2026-10-26 12:07 UTC, before branch synchronization:** #264 is MERGED as `d948aebeb046e9d2a224dcbb89f5dc805bcfa147`, with no submitted GitHub human review; merge actor is recorded above, but no independent approval is inferred. #259 remains OPEN at `5b3bb1cf79c26cb2daa8daf314dfe8e6a8506866`, behind main. #262 remains OPEN DRAFT at `b5a1b9ea27ef2b26c9bbcfe1b7a218b705c8ffe0`, dirty against main. #253 remains OPEN at `78483b69ca8a61eef32c787a982e08520b1264cc`, dirty against main and overlapping #255. #265 is OPEN DRAFT at its pre-synchronization head `339c3630e5e31bce391c8290b3be2dc2cbcb0a7e`, with no submitted human review; the branch refresh is described below. The #264 acceptance material is now [on main](../STAGING_ACCEPTANCE.md); its tests establish only offline synthetic behavior.

**VERIFIED — branch synchronization:** after the 12:07 queue observation, `feature/production-execution-roadmap` merged current `main` commit `d948aebeb046e9d2a224dcbb89f5dc805bcfa147` without force-push. That merge adds the already-merged #264 staging acceptance test and document verbatim and preserves both README links. The updated #265 head SHA and exact-head CI result are available in the live PR metadata; refresh again before any owner decision.

**VERIFIED (historical evidence, not current proof):** [2026-10-25 readiness plan](2026-10-25-devobs-managed-production-readiness.md), [governance audit](../DEVOBS_MAIN_GOVERNANCE_AUDIT.md), [AI baseline](../AI_DEVOPS_2027_BASELINE.md), [repository audit](../REPO_AUDIT.md), [staging proposal](../RENDER_SUPABASE_STAGING.md), [product readiness](../PRODUCT_SAAS_READINESS.md), and [offline staging acceptance in PR #264](https://github.com/hamedonassar95/Devobs/blob/5f25d5c018a8f0600898592b228d4d1636f0274e/docs/STAGING_ACCEPTANCE.md) record prior observations. Preserve their historical scope and dates; do not rewrite them as current evidence.

## Single phase ledger

Only **P00** is active. P01–P12 are blocked until the previous phase's documented exit gate is met and owner signoff recorded. Status describes this plan's current evidence, not future completion.

| Phase | Status | Blocking prerequisite |
| --- | --- | --- |
| P00 | ACTIVE — review/governance baseline | Owner decision on roadmap PR #265; then exact-head read-only review of #259 |
| P01 | BLOCKED — managed staging | P00 signed exit; owner approvals for provider, data and spend |
| P02 | BLOCKED — live observability | P01 live staging and privacy approval |
| P03 | BLOCKED — topology and incident memory | P02 accepted tenant-safe signals |
| P04 | BLOCKED — measured evaluation | P03 provenance-bound fixtures and approved evaluation data |
| P05 | BLOCKED — durable audit | P04 accepted evidence schema and privacy/retention decision |
| P06 | BLOCKED — AI governance | P05 audit controls and model cost/privacy approval |
| P07 | BLOCKED — scoped actions | P06 governance signoff and separate action authorization design |
| P08 | BLOCKED — recovery | P07 signed rollback boundaries; approved staging data/resources |
| P09 | BLOCKED — security/legal review | P08 restore evidence and scoped threat model |
| P10 | BLOCKED — commercial SaaS | P09 security/legal review and business/payment eligibility |
| P11 | BLOCKED — operations | P10 product scope plus named support/on-call/SLO owners |
| P12 | BLOCKED — controlled pilot | P00–P11 exit evidence and explicit release decision |

## Sequential execution phases

### P00: Baseline, governance, and release safety

- **Entry:** this roadmap PR receives an owner decision; refresh main SHA, rules, PR states and exact-head checks using read-only GitHub API. **Next smallest task after owner decision on #265:** perform an exact-head read-only security/CI review of PR #259. #264 is already merged; verify its merge/check evidence rather than treating it as an open PR. This plan does not approve or merge any PR.
- **Existing:** `.github/workflows/ci.yml`, `scripts/check_action_pins.py`, current rules API and PR queue above. **Proposed:** no source files; future small documentation/evidence PRs only.
- **Order:** record #264's merged disposition and exact head/merge CI evidence (refreshed above; merge has no submitted GitHub human review); then review #259, #262 and #253 separately, in that order. For every open PR verify current head SHA, base, merge state, `validate`, security checks and review history. #253 must be compared with already merged #255; do not duplicate Trivy. Resolve conflicts or redundancy by review decision, never blind merge/close.
- **Acceptance artifacts/tests:** timestamped API evidence, exact SHA/run/job URLs, reviewer decision, documented blockers and unchanged protected-main rules. Tests: API state cross-check plus PR-specific CI on exact head; no bypass.
- **Exit/go:** owner records a disposition for each queued PR and confirms the required gate still applies. #265 remains pending owner review; its successful `validate` is necessary but not human approval. If PR/check state changed, CI failed, review is absent, or policy differs, STOP and re-baseline. **Signoff:** repository owner/authorized maintainer; no independent reviewer is configured by the observed ruleset and feasibility is UNVERIFIED. No external cost/data is approved here.
- **Rollback:** documentation-only corrections in a new reviewed PR; preserve historical evidence. **Unverified:** hidden external policy and whether independent review can be obtained.

### P01: Managed read-only staging (Render, PostgreSQL, OIDC)

- **Entry:** P00 exit signed. **Existing:** `scripts/devobs_intelligence/staging_app.py`, `staging_smoke.py`, `tests/test_intelligence_staging_app.py`, `tests/test_postgres_rls_integration.py`, `deploy/postgres/001_tenant_rls.sql`, `render.yaml`, `docs/RENDER_SUPABASE_STAGING.md`; smoke acceptance in #264 is offline/synthetic only. **Proposed:** approved Render WSGI staging, separate Supabase PostgreSQL 17+ project, chosen OIDC IdP/JWKS lifecycle and operator-only secret injection.
- **Owner approval before any resource:** account/workspace, provider, region/residency, exact scope and maximum budget; data class/retention; secret-manager and rotation policy; IdP; deletion/rollback plan. Review migration; separate restricted non-owner/non-BYPASSRLS runtime DB identity; TLS `verify-full` and trusted CA installation; FORCE RLS; live JWKS rotation/revocation; valid and invalid/cross-tenant tests; request/rate/body limits, sanitized logs, downtime/failure recovery. No provisioning or migrations under this plan.
- **Acceptance artifacts/tests:** exact deployment SHA, authenticated TLS/hostname evidence, live issuer/audience/signature/expiry tests, role/RLS catalog evidence, negative cross-tenant proof with existing fixture, readiness/downtime/limits tests, redacted logs and recovery transcript. Offline tests alone fail the live gate. Official references: [Render Blueprint](https://render.com/docs/blueprint-spec), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [Supabase production checklist](https://supabase.com/docs/guides/platform/going-into-prod).
- **Exit/go:** only after every live security condition passes on approved staging and owner signs evidence; any missing RLS, invalid trust, leak, limit/recovery failure or unapproved spend is NO-GO. **Signoff:** owner/authorized maintainer; independent review availability UNVERIFIED. Cost/privacy approval must precede resource creation and data use.
- **Rollback:** keep auto-deploy off; stop traffic, revoke test identity, disable service through separately approved provider procedure, preserve approved evidence, and remove only with owner authorization. **Unverified:** actual service, DB, IdP, TLS and recovery remain nonexistent/unproven until this gate.

### P02: Approved live OpenTelemetry signals

- **Entry:** P01 live exit signed. **Existing:** offline evidence contracts/collectors and local Prometheus/Grafana configuration; no deployed application metrics endpoint is evidenced. **Proposed:** tenant-aware OTLP ingestion/export, metrics/traces schema, instrumentation and dashboards.
- **Acceptance artifacts/tests:** synthetic and approved staging traces with tenant separation; missing/malformed and high-cardinality rejection; redaction tests; trace context and source/build provenance; retention/deletion proof; measured ingestion and query cost. **Tests:** unit/contract, adversarial tenant-label tests, live canary under approved limits. Official reference: [OpenTelemetry documentation](https://opentelemetry.io/docs/).
- **Exit/go:** no raw secrets, prompts or unapproved customer payloads; no cross-tenant telemetry; retention, cardinality and spend within owner-approved limits. Otherwise disable export and NO-GO. **Signoff:** owner plus data/privacy decision owner (identity to be named); both cost and data-use approvals required before enabling.
- **Rollback:** disable exporter/collector and revert reviewed instrumentation PR; follow approved deletion/retention procedure. **Unverified:** live OTLP, tenant separation, redaction and operational cost.

### P03: Dependency topology and incident memory

- **Entry:** P02 signals accepted. **Existing:** bounded offline context/correlation and synthetic incident-memory modules. **Proposed:** tenant-scoped service graph ingestion, provenance schema, memory approval/retrieval boundary and freshness controls.
- **Acceptance artifacts/tests:** graph snapshots bind tenant, service, source SHA and capture time; test cycles, missing/stale nodes, poisoned memory, cross-tenant retrieval, bounded expansion and source provenance. Live evidence must be redacted and owner-approved; no vector service assumed.
- **Exit/go:** every returned edge/memory item is tenant-authorized, source-attributed, fresh or explicitly stale, and bounded; any leak or untraceable memory is NO-GO. **Signoff:** owner plus privacy/data owner; approval of data sources and retention precedes ingestion.
- **Rollback:** disable retrieval and return to deterministic no-memory advisory mode; remove affected data under approved retention procedure. **Unverified:** production graph and trusted incident corpus.

### P04: Golden dataset and measured quality

- **Entry:** P03 evidence schema and provenance accepted. **Existing:** synthetic evaluation fixtures and deterministic adviser. **Proposed:** versioned golden dataset, labeling protocol, evaluation runner and scorecard.
- **Acceptance artifacts/tests:** reviewed dataset manifest and labels; reproducible precision/recall, safe-refusal rate, latency and per-request cost with denominators, confidence intervals and slice results; tests for leakage, insufficient evidence and unsafe recommendations. Targets must be approved and measured, never invented in advance.
- **Exit/go:** owner approves dataset provenance/privacy and explicit target thresholds before evaluation; all thresholds meet target on an exact versioned dataset. Missing sample quality, fabricated metrics or regression is NO-GO. **Signoff:** owner and named evaluation/data approver; dataset retention and any inference spend approved first.
- **Rollback:** disable candidate ranking/model and restore prior deterministic advisory path; retain scorecard and dataset version for comparison. **Unverified:** production quality, latency, safe refusal and cost.

### P05: Tenant-scoped tamper-evident audit

- **Entry:** P04 accepted evidence and data classification. **Existing:** local hash-chained audit ledger; not externally anchored. **Proposed:** tenant-bound durable audit events, integrity anchor, export/deletion workflow and redacted retention policy.
- **Acceptance artifacts/tests:** tamper/replay/order tests; actor, tenant, object, decision and source SHA linkage; cross-tenant query/export denial; redaction and retention/deletion evidence; independently verifiable anchor and restore test. Never log credentials or raw prompts.
- **Exit/go:** authorized reviewers can verify integrity and completeness without seeing another tenant's data; legal/privacy-approved retention and deletion behavior demonstrated. Any silent gap or leak is NO-GO. **Signoff:** owner plus privacy/legal record owner; storage cost and retention approved.
- **Rollback:** stop new writes to candidate ledger, preserve forensic copy under approved retention, revert readers to last verified audit path; never rewrite history silently. **Unverified:** external immutability, completeness and deletion behavior.

### P06: NIST AI RMF and model governance

- **Entry:** P05 audit gate signed. **Existing:** advisory-only workflow controls and offline model/policy docs; AI review budget gate may skip inference. **Proposed:** system/model cards, AI risk register mapped to [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), prompt-injection boundary, approved model/vendor configuration and human review records.
- **Acceptance artifacts/tests:** documented intended use/limits, threat cases for indirect prompt injection and poisoned evidence, tenant-bound context tests, refusal and escalation evidence, data-retention/vendor terms review, measured cost ceiling and explicit approval audit. No claim of NIST certification or compliance from mapping alone.
- **Exit/go:** model use remains advisory; data and vendor terms approved; injection tests cannot induce data disclosure/tool execution; spend is capped and human approval is observable. Otherwise disable inference. **Signoff:** owner and named AI/privacy decision owner; paid model and data transfer require prior approval.
- **Rollback:** turn off inference via reviewed/configured control and return to deterministic no-model path; preserve approved audit. **Unverified:** live model risk, vendor retention and governance effectiveness.

### P07: Deny-by-default, bounded actions

- **Entry:** P06 risk controls signed. **Existing:** human approval/recovery gates in repository automation; no autonomous production authority. **Proposed:** action broker/policy contract for any future staging action, signed approval bound to actor, tenant, action, exact SHA, TTL, scope and revocation.
- **Acceptance artifacts/tests:** deny-by-default matrix, invalid/expired/replayed/wrong-tenant/wrong-SHA signature tests, approver identity proof, revocation and kill-switch evidence, audit linkage and non-production dry-run. No model text may create or satisfy approval; no autonomous production changes.
- **Exit/go:** unauthorized requests provably denied, approval cannot be replayed or widened, and a human can revoke before execution. Any ambiguity or bypass is NO-GO. **Signoff:** owner and authorized action approver; no execution until separately approved per action and cost/privacy impact.
- **Rollback:** revoke signing authority, disable broker, cancel pending work and use P00-reviewed rollback process. **Unverified:** any production-grade action authorization service.

### P08: Encrypted backup and recovery rehearsal

- **Entry:** P07 scopes signed, approved staging environment exists. **Existing:** recovery runbooks and CI PostgreSQL fixture; neither proves managed restore. **Proposed:** encrypted tenant-consistent backups, key custody, restore automation, measured RPO/RTO and service rollback drill.
- **Acceptance artifacts/tests:** restore from a real approved staging backup into isolated staging; integrity, RLS, tenant isolation and deletion checks; measured achieved RPO/RTO, operator transcript, alert and rollback runbook. No customer data without separate approval.
- **Exit/go:** restore succeeds within owner-approved targets, keys and access are controlled, and no tenant mixing occurs. Missing restore evidence or data loss is NO-GO. **Signoff:** owner and named recovery/data owner; approve storage/restore cost and retention first.
- **Rollback:** isolate failed restore, keep source untouched, restore prior known-good staging state or shut down service; do not promote damaged data. **Unverified:** backup encryption, recovery time and recoverability.

### P09: Independent security, supply chain, privacy and legal review

- **Entry:** P08 restore gate passed. **Existing:** pinned Actions, Trivy, Python dependency/security checks, Terraform validation and RLS CI. **Proposed:** current threat model, SBOM/license disposition, dependency response process, penetration test, privacy impact and legal review; Terraform plan only.
- **Acceptance artifacts/tests:** exact-SHA CI/security report, reviewed SBOM and license obligations, tested threat mitigations, independent penetration findings closure, privacy/legal disposition and non-destructive Terraform plan. No `apply`; no certification claims absent accredited assessment.
- **Exit/go:** no unresolved critical/high finding outside an explicitly approved remediation plan; licensing/privacy/legal blockers resolved for intended pilot. **Signoff:** owner plus qualified independent security and legal/privacy reviewers (availability is UNVERIFIED); approve assessment cost and data scope.
- **Rollback:** disable affected exposure/features, pin/revert reviewed dependency/config change and preserve reports; never suppress findings automatically. **Unverified:** independent test results, commercial license clearance and compliance certification.

### P10: Tenant lifecycle, subscriptions and lawful commerce

- **Entry:** P09 approved for intended internal/pilot scope. **Existing:** read-only tenant/project API contract and draft commercial readiness document; no complete customer lifecycle or billing system. **Proposed:** tenant create/invite/SSO/deactivate/delete flows, authorization model, metering/entitlement ledger, legally eligible payment processor and signed idempotent webhook handling.
- **Acceptance artifacts/tests:** full tenant lifecycle and isolation tests across reads, writes, search, exports, queues and deletion; SSO ownership and recovery; webhook signature/replay/idempotency, quotas, cancellation, refunds/disputes and reconciliation; lawful terms, tax, processor and data-processing review.
- **Exit/go:** customer data and subscription state reconcile; lifecycle cannot leak or retain data unlawfully; business/payment eligibility, support and public terms approved. Otherwise no sales/customer onboarding. **Signoff:** owner plus qualified legal/business/payment approvers; no processor, charge or customer data before approval.
- **Rollback:** disable signup/checkout, stop new tenant intake, honor lawful export/deletion/refund obligations and reconcile event ledger. **Unverified:** provider eligibility, legal terms, subscriptions, billing and tenant administration.

### P11: Reliability, support and operations

- **Entry:** P10 scope and lifecycle accepted; internal-only service scope may be explicitly approved. **Existing:** CI health checks and local monitoring demo; no live application SLO/on-call evidence. **Proposed:** meaningful service and tenant SLOs, alerting, runbooks, capacity/cost forecasts, staffed on-call and incident response.
- **Acceptance artifacts/tests:** SLO definitions with measured windows and error budgets, alert delivery/acknowledgment drill, capacity/failure/load test, cost forecast and budget alerts, incident tabletop, escalation/contact and support coverage. Targets must be owner-approved, not fabricated.
- **Exit/go:** named staffed owner can detect, respond, recover and communicate within approved targets; budget and privacy limits remain enforceable. Otherwise no external pilot. **Signoff:** owner plus named support/on-call and privacy owners; approve staffing and monitoring spend.
- **Rollback:** reduce traffic or disable service, invoke incident and recovery runbooks, preserve tenant data and notifications. **Unverified:** production SLOs, staffing, load capacity and response performance.

### P12: Controlled internal pilot and separate commercial launch gate

- **Entry:** P00–P11 all have exact evidence, exit signoff, unresolved-risk disposition and current `validate` on release SHA. **Existing:** static Pages CI publishing; it is not API deployment evidence. **Proposed:** small named internal pilot cohort, explicit scope/consent, staged rollout and monitored rollback; later commercial launch is a separate decision.
- **Acceptance artifacts/tests:** signed release checklist covering identity/RLS, measured quality, audit, cost/privacy, restore, security/legal, support/SLO, rollback and incident contacts; canary results and exact release SHA; human go/no-go record. Rehearse rollback before pilot. No public signup/customer acquisition in this phase.
- **Exit/go:** owner explicitly approves pilot after every preceding gate; any failed control, unexplained spend, leak, missing restore, absent reviewer/owner or stale CI is NO-GO. Commercial customer launch requires a new approval and commercial/legal/payment readiness review; internal v1 is not commercial readiness. **Signoff:** repository/service owner and separately authorized release decision maker; cost/privacy approvals must cover cohort and data.
- **Rollback:** stop cohort intake, disable affected service/actions, revert to last verified release, execute tested restore/communications and incident process. **Unverified:** pilot outcomes, API availability and commercial launch suitability.

## Explicit unresolved owner decisions

These block only the phase that needs them: (1) hosting/provider account, workspace, region/residency and maximum budget (P01); (2) identity provider and key lifecycle (P01); (3) data classification, permitted residency, retention and deletion (P01 onward); (4) independent reviewer availability and authority (P00/P09); (5) business/legal and payment-provider eligibility (P09/P10); (6) support/on-call owner and SLO targets (P11); (7) approved telemetry/model vendors and privacy/cost limits (P02/P06). **UNVERIFIED:** no approval or certification is implied by this plan. Do not resolve these by reading settings or creating accounts; obtain an explicit owner decision first.

## Official references

- [GitHub rulesets and available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Supabase row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security) and [production checklist](https://supabase.com/docs/guides/platform/going-into-prod)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [OWASP API Security: Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
