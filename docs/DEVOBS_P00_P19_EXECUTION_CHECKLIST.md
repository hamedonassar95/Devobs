# Devobs AI Intelligence — P00–P19 evidence-first checklist

> **GitHub audit snapshot:** 2026-10-31; canonical `hamedonassar95/Devobs`; reviewed main `104050c066ec165ed3cd71aec738b0d3b96132c8`.
> **Observed main CI:** [run 41175406373](https://github.com/hamedonassar95/Devobs/actions/runs/41175406373) completed successfully on that SHA. Passing GitHub CI/Pages does not imply SaaS readiness.

## Evidence boundaries and B-series mapping

- **VERIFIED:** [Master issue #233](https://github.com/hamedonassar95/Devobs/issues/233) specifies 72 numbered acceptance tasks T01–T72 in P00–P12; all 13 phase issues #220–#232 remain open. The checkboxes below reproduce those official task names and acceptance statements.
- **VERIFIED:** P00 has an [owner-signed limited GO decision](https://github.com/hamedonassar95/Devobs/pull/277) for **repository governance only**. Source issue #220 still shows unchecked task-level acceptance boxes. Do not confuse a signed limited phase decision with all six T-items proved individually.
- **VERIFIED:** [P01](P01_ACTIVATION_READINESS.md) is owner-signed **NO-GO / BLOCKED**. The conditional monthly ceiling is **USD 100 total including fees and all resources**; no enforceable all-in guarantee has been established. This document does not authorize paid cloud resources, provider changes, data transfers, AI inference, production deployment or a merge.
- **VERIFIED:** [AI-9](MILESTONE_LEDGER.json) remains **FAIL / BLOCKED**; independent holdout has not been executed.
- **VERIFIED:** [P13–P19](P01_REGION_BUDGET_SECURITY.md) are future planning-only tracks, not accepted production capabilities.
- **UNVERIFIED:** A canonical B0/B0-1/B0-19/B1–B19 task series or formal mapping to P-series was not found in the inspected GitHub issues/code searches. Do **not** silently equate B and P or close arbitrary B numbers. An official B definition is required for a valid crosswalk.

**Checkbox interpretation:** `[ ]` = *individual acceptance proof has not been certified in this snapshot*, **not** "no source code exists". A task becomes `[x]` only after exact-SHA review plus its required positive/negative tests and, if applicable, real authorized runtime evidence.

## Phase completion matrix

| Phase | Stage-gate state | Scope | Source |
|---|---|---|---|
| P00 | LIMITED GO (governance only; individual T acceptance unverified) | Baseline audit and release controls | [Issue #220](https://github.com/hamedonassar95/Devobs/issues/220) |
| P01 | BLOCKED (all-in budget/provider/identity/runtime) | Hardened managed staging / RLS / OIDC / API | [Issue #221](https://github.com/hamedonassar95/Devobs/issues/221) |
| P02 | WAITING—P01 | OpenTelemetry and observability | [Issue #222](https://github.com/hamedonassar95/Devobs/issues/222) |
| P03 | WAITING—P02 | Topology and incident memory | [Issue #223](https://github.com/hamedonassar95/Devobs/issues/223) |
| P04 | WAITING—P03 | Evaluation and measurable accuracy | [Issue #224](https://github.com/hamedonassar95/Devobs/issues/224) |
| P05 | WAITING—P04 | Tamper-evident governance | [Issue #225](https://github.com/hamedonassar95/Devobs/issues/225) |
| P06 | WAITING—P05 | Versioned models and agent safety | [Issue #226](https://github.com/hamedonassar95/Devobs/issues/226) |
| P07 | WAITING—P06 | Approval-bound tools and MCP | [Issue #227](https://github.com/hamedonassar95/Devobs/issues/227) |
| P08 | WAITING—P07 | Recovery and backup | [Issue #228](https://github.com/hamedonassar95/Devobs/issues/228) |
| P09 | WAITING—P08 | DevSecOps and privacy | [Issue #229](https://github.com/hamedonassar95/Devobs/issues/229) |
| P10 | WAITING—P09 | Multi-tenant SaaS and billing | [Issue #230](https://github.com/hamedonassar95/Devobs/issues/230) |
| P11 | WAITING—P10 | Operational readiness and support | [Issue #231](https://github.com/hamedonassar95/Devobs/issues/231) |
| P12 | WAITING—P11 | Private pilot and production gate | [Issue #232](https://github.com/hamedonassar95/Devobs/issues/232) |
| P13 | PLANNED ONLY | Tenant-scoped, redacted telemetry | [Future plan](P01_REGION_BUDGET_SECURITY.md) |
| P14 | PLANNED ONLY | Predictive monitoring | [Future plan](P01_REGION_BUDGET_SECURITY.md) |
| P15 | PLANNED ONLY | Human-reviewed incident remediation | [Future plan](P01_REGION_BUDGET_SECURITY.md) |
| P16 | PLANNED ONLY | AI security and governance | [Future plan](P01_REGION_BUDGET_SECURITY.md) |
| P17 | PLANNED ONLY | AI-driven FinOps | [Future plan](P01_REGION_BUDGET_SECURITY.md) |
| P18 | PLANNED ONLY | Code and infrastructure copilots | [Future plan](P01_REGION_BUDGET_SECURITY.md) |
| P19 | PLANNED ONLY | Continuous AI feedback loop | [Future plan](P01_REGION_BUDGET_SECURITY.md) |

## Signed decisions vs acceptance

- [x] P00 **limited repository-governance GO** signed by owner (not full P00 task certification).
- [ ] P01 **managed staging GO** — blocked; cap / region / provider / security evidence missing.
- [ ] AI-9 **independent quality approval** — no holdout score or release authorization.
- [ ] SaaS **production release GO** — dependent gates not accepted.

## Exact canonical acceptance tasks: T01–T72

### P00 — Baseline audit and release controls

[Source Issue #220](https://github.com/hamedonassar95/Devobs/issues/220) · **LIMITED GO (governance only; individual T acceptance unverified)** · 6 acceptance items.

- [ ] **T01: Inventory actual implemented components.** For each subsystem capture current main path, test, SHA and VERIFIED/PARTIAL/BLOCKED status.
- [ ] **T02: Reconcile docs after merged PR 218 and 219.** Remove outdated pending-PR claims; link actual merge commits.
- [ ] **T03: Audit GitHub Pages, Vercel and cloud deploy triggers.** Demonstrate draft PR cannot trigger prod and document the main-push publication path.
- [ ] **T04: Enforce reviewed, passing changes.** Verify PR review, validate, security and CodeQL requirements, no direct unreviewed main push.
- [ ] **T05: Record reproducible CI and test baseline.** Capture exact SHA, test inventory, skips, PostgreSQL RLS and negative-security results.
- [ ] **T06: Set risk register and go/no-go ownership.** Record cost/privacy/security decision owners, blockers and no-spend/no-prod policy.

### P01 — Hardened managed staging / RLS / OIDC / API

[Source Issue #221](https://github.com/hamedonassar95/Devobs/issues/221) · **BLOCKED (all-in budget/provider/identity/runtime)** · 9 acceptance items.

- [ ] **T07: Threat model trust boundaries.** Identify service, tenant, DB, network and connector trust zones with abuse-case test matrix.
- [ ] **T08: Choose region, provider and enforce cost budget.** Compare deployment alternatives, assess data residency and require externally configured cost caps.
- [ ] **T09: Prepare reviewable reproducible IaC.** IaC plan/lint tests must not provision from PR or include credentials.
- [ ] **T10: TLS and access-protected staging ingress.** Verify HTTPS-only, deny-by-default, rate limits and separation from production.
- [ ] **T11: Hosted PostgreSQL with restricted roles.** Separate migrator/runtime, forced RLS, encrypted connections and no BYPASSRLS.
- [ ] **T12: Hosted RLS negative tests.** Cross-tenant read/write/list/search and pooled connection switching all deny.
- [ ] **T13: Real OIDC discovery, JWKS and refresh.** Validate issuer/audience/token kind, key rotation and invalid-key failure.
- [ ] **T14: Staging API, OpenAPI and health.** Serve scoped API with predictable 401, 403, 429, 503, health probes and body bounds.
- [ ] **T15: Managed secrets, staging kill switch and teardown.** No secret values in repo/log; smoke tests and documented rollback/teardown.

### P02 — OpenTelemetry and observability

[Source Issue #222](https://github.com/hamedonassar95/Devobs/issues/222) · **WAITING—P01** · 6 acceptance items.

- [ ] **T16: Authenticated OTLP collector.** Accept only allowed trusted senders, reject others; disable public exposure.
- [ ] **T17: Metric schema adapter and provenance.** Map allowlisted OTel signals to tenant/source-SHA/timestamp safe contract; reject unknowns.
- [ ] **T18: Privacy-safe traces and logs.** Redact secrets and PII before durable storage; verify with adversarial fixtures.
- [ ] **T19: Deployment/config event timeline.** Correlate immutable SHA and change events; reject conflicting or stale IDs.
- [ ] **T20: Retention, quotas and cardinality safeguards.** Enforce per-tenant limits, max batches and evidence TTL with tests.
- [ ] **T21: MTTD/MTTR observability prerequisites.** Record clock quality, onset/detection/resolution timestamps and denominator coverage.

### P03 — Topology and incident memory

[Source Issue #223](https://github.com/hamedonassar95/Devobs/issues/223) · **WAITING—P02** · 6 acceptance items.

- [ ] **T22: Discover authorized service dependency topology.** Ingest signed/verified service metadata, exact tenant scope and source freshness.
- [ ] **T23: Detect graph drift and cycles.** Bound traversal, handle cycles/orphans and mark unverifiable edges.
- [ ] **T24: Correlate impacted services.** Explain ranked hypothesis from evidence without claiming causal proof.
- [ ] **T25: Encrypt and isolate durable incident metadata.** Delete/export/retention policies; deny cross-tenant and raw private logs.
- [ ] **T26: Evaluate optional vector retrieval safely.** Require consent, scoped embeddings, poisoning tests and baseline comparison.
- [ ] **T27: Strengthen abstention and provenance checks.** Reject replay, missing evidence, stale SHA, unknown services and wrong tenant.

### P04 — Evaluation and measurable accuracy

[Source Issue #224](https://github.com/hamedonassar95/Devobs/issues/224) · **WAITING—P03** · 5 acceptance items.

- [ ] **T28: Curate consented human-labeled incidents.** Record inclusion policy, anonymization, label provenance and review split.
- [ ] **T29: Create versioned golden benchmark.** At least 30 labeled cases for initial review; segment classes; no synthetic-to-production claim.
- [ ] **T30: Gate top-1/top-3 and abstention in CI.** Measure denominators, prevent regressions against approved baseline; no spurious score.
- [ ] **T31: Evaluate false positives, confidence and drift.** Publish calibration, class errors, fresh data comparisons and human escalation triggers.
- [ ] **T32: Measure operational value.** Define and collect MTTD/MTTR, noise, override and cost/incident only when actual observations exist.

### P05 — Tamper-evident governance

[Source Issue #225](https://github.com/hamedonassar95/Devobs/issues/225) · **WAITING—P04** · 5 acceptance items.

- [ ] **T33: Design append-only external audit retention.** Specify write-once privileges, schema, actor and tenant/time/event binding.
- [ ] **T34: Anchor ledger hashes externally.** Signed checkpoints independent of app DB and test privileged rewrite detection.
- [ ] **T35: Capture per-action identity and provenance.** Record policy/model/tool version, request/parameters digest, approver, outcome and failure.
- [ ] **T36: Create privacy-safe auditor export.** Tenant-scoped export, legal hold/retention and integrity verification; reject unauthorized reads.
- [ ] **T37: Build crosswalk evidence report.** Map verified artifacts to SOC 2/ISO/NIST controls without claiming certification.

### P06 — Versioned models and agent safety

[Source Issue #226](https://github.com/hamedonassar95/Devobs/issues/226) · **WAITING—P05** · 5 acceptance items.

- [ ] **T38: Lock versioned AI-BOM and system cards.** Record snapshot, dataset, dependencies, tools, prompt template and accountable owner.
- [ ] **T39: Provider interface with deterministic fallback.** Default read-only/offline; timeouts, provider unavailability and no secret leakage.
- [ ] **T40: Evaluate manager and specialized advisers.** No speculative action privileges; provenance, consistency and same-tenant tests.
- [ ] **T41: Enforce inference budgets and loop ceilings.** Token/request/iteration ceilings, circuit breakers and actual billed usage reconciliation.
- [ ] **T42: Human-reviewed promotion and rollback rules.** Versioned eval thresholds and canary/reversal evidence; model changes never silently promote autonomy.

### P07 — Approval-bound tools and MCP

[Source Issue #227](https://github.com/hamedonassar95/Devobs/issues/227) · **WAITING—P06** · 5 acceptance items.

- [ ] **T43: Define least-privilege action tool registry.** Allowlist exact operations, validate parameters, ban general-purpose shell access.
- [ ] **T44: Bind one-time approvals to authenticated reviewers.** Verify actor, request digest, expiry, action, target, tenant and prevent replay.
- [ ] **T45: Separate reviewer from execution service.** Model output cannot grant auth; deny unauthorized/expired/ambiguous approvals.
- [ ] **T46: Exercise nonproduction action and rollback.** Canary low-risk fixture, fault-injection, postcondition, independent rollback checks.
- [ ] **T47: Level-2/3 promotion with emergency kill switch.** High-risk stays manual; prove kill switch, blast-radius ceiling and audited override.

### P08 — Recovery and backup

[Source Issue #228](https://github.com/hamedonassar95/Devobs/issues/228) · **WAITING—P07** · 5 acceptance items.

- [ ] **T48: Set documented RPO/RTO targets.** Risk-based recovery targets and retention with accountable operator.
- [ ] **T49: Configure encrypted scheduled backups.** Verify access isolation, expiry, integrity and separate backup keys.
- [ ] **T50: Restore a full staged tenant from backup.** Prove record counts, app auth, RLS and data consistency, no production overwrite.
- [ ] **T51: Test failover and degraded provider mode.** Controlled outage and recovery drills with measured downtime.
- [ ] **T52: Automate repeatable disaster recovery rehearsals.** Versioned runbook, evidence log and accountable review at each exercise.

### P09 — DevSecOps and privacy

[Source Issue #229](https://github.com/hamedonassar95/Devobs/issues/229) · **WAITING—P08** · 5 acceptance items.

- [ ] **T53: Extend pipeline security scanners.** SAST, SCA, secret scan, container and IaC checks with reproducible failures.
- [ ] **T54: Produce SBOM and artifact provenance.** Document transitive deps, signed release image and reproducible build.
- [ ] **T55: Pen-test auth, tenant data and approval paths.** Independent or authorized security review, prioritized remediation tracked to tests.
- [ ] **T56: Complete privacy and legal gap assessment.** Data map, DPA, processors, residency, retention and EU AI Act applicability.
- [ ] **T57: Establish compliance readiness evidence pack.** SOC 2/ISO 27001/42001 gap ownership, proofs and external review boundaries.

### P10 — Multi-tenant SaaS and billing

[Source Issue #230](https://github.com/hamedonassar95/Devobs/issues/230) · **WAITING—P09** · 5 acceptance items.

- [ ] **T58: Self-service onboarding and RBAC.** Tenant signup, invite/revoke, project scopes and SSO restrictions proven by tests.
- [ ] **T59: Integrate tenant-managed read-only connectors.** GitHub/GitLab and opt-in monitoring sources with credential revocation.
- [ ] **T60: Implement authenticated dashboard and OpenAPI.** Incident evidence, quota and audit UI, API key hashing/rotation and access tests.
- [ ] **T61: Measure billable usage and per-tenant quotas.** Atomic usage ledger, idempotency, reconciliation and budget/fairness ceilings.
- [ ] **T62: Implement billing behind commercial release gate.** Verified processor/legal eligibility, signed webhooks, cancellation/refunds, never bill test users.

### P11 — Operational readiness and support

[Source Issue #231](https://github.com/hamedonassar95/Devobs/issues/231) · **WAITING—P10** · 5 acceptance items.

- [ ] **T63: Define SLIs/SLOs and actionable alerts.** Measure uptime, latency, errors, error budget and paging ownership.
- [ ] **T64: Run authorized load and tenant isolation tests.** Realistic staging capacity, p95/p99, rate limiting, noisy-neighbor and queue exhaustion.
- [ ] **T65: Set runbooks and escalation/incident management.** On-call ownership, incident severity, communications and postmortem template.
- [ ] **T66: Implement FinOps monitoring.** Tags, budget alerts, forecast, per-tenant inference/storage usage and cutoff.
- [ ] **T67: Run end-to-end release and rollback rehearsal.** Artifact promotion, signed approvals, smoke and recovery, without production rollout.

### P12 — Private pilot and production gate

[Source Issue #232](https://github.com/hamedonassar95/Devobs/issues/232) · **WAITING—P11** · 5 acceptance items.

- [ ] **T68: Build verified production release checklist.** Fail closed on unknown statuses; include budget, identity, RLS, restore, audit and security.
- [ ] **T69: Provision private consented pilot under human control.** Document authorization and isolate pilot users/data; default read-only.
- [ ] **T70: Measure genuine pilot benefit and harms.** Real MTTD/MTTR/accuracy/cost with baseline, missing-data counts and adverse events.
- [ ] **T71: Review human-signed production launch decision.** No automated go-live: documented security, privacy, cost, reliability and support approval.
- [ ] **T72: Controlled launch, rollback, post-launch watch.** Execute only with separate account configuration; verify post-launch SLO and emergency stop.

## P13–P19 future planning (not 2027 T01–T72 acceptance tasks)

- [ ] **P13 — Tenant-scoped, redacted telemetry**: Planned only; requires defined scope, prerequisite acceptance, owner approval, measurable tests, and separate release gates.
- [ ] **P14 — Predictive monitoring**: Planned only; requires defined scope, prerequisite acceptance, owner approval, measurable tests, and separate release gates.
- [ ] **P15 — Human-reviewed incident remediation**: Planned only; requires defined scope, prerequisite acceptance, owner approval, measurable tests, and separate release gates.
- [ ] **P16 — AI security and governance**: Planned only; requires defined scope, prerequisite acceptance, owner approval, measurable tests, and separate release gates.
- [ ] **P17 — AI-driven FinOps**: Planned only; requires defined scope, prerequisite acceptance, owner approval, measurable tests, and separate release gates.
- [ ] **P18 — Code and infrastructure copilots**: Planned only; requires defined scope, prerequisite acceptance, owner approval, measurable tests, and separate release gates.
- [ ] **P19 — Continuous AI feedback loop**: Planned only; requires defined scope, prerequisite acceptance, owner approval, measurable tests, and separate release gates.

## Next executable workflow, subject to boundaries

1. Re-check the exact latest main SHA and required `validate`/Security/CodeQL. Read `AGENTS.md`, `STATE.md`, [durable ledger](MILESTONE_LEDGER.json), and existing PRs before proposing duplicated work.
2. Execute **one** earliest permitted acceptance item at a time on an isolated branch. Candidate offline-only increments are P01 T07 threat-model review or T09 reproducible IaC validation; cite real tests and open a reviewed PR.
3. P01 T08 is an absolute provisioning stop until the selected provider/region and **enforceable all-in USD 100 monthly cap** have evidence and separate owner authorization. Alerts and pre-tax limits are not sufficient.
4. Do not mark hosted P01 T10–T15, P02–P12, or P13–P19 complete without permissioned real service/runtime, tenant isolation, authentication, negative-case tests, and evidence-based signoff.
5. After review and owner merge, document actual final PR head SHA, merge SHA, required CI run, specific acceptance proof and remaining limits. Update only the applicable checkboxes on a new review branch; never auto-approve your own work.
6. If the **B** series has a distinct specification, add a separately reviewed B↔P crosswalk before acting on its tasks.

**Nonclaims:** This audit is not proof of completed P01–P19, B0–B19, live OTel, SaaS billing, external identity, deployed PostgreSQL, AI-9 production quality, or independent certification.
