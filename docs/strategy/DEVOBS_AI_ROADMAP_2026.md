# Devobs AI Intelligence roadmap — 2026

**Status:** `READY_FOR_REVIEW`, not `PRODUCTION_COMPLETE`
**Base:** `main` at `67e03118c14a19d0cb6ef1c86b9abcaf1eb2a07a` (observed 2026-11-13 UTC)
**Scope:** phased, evidence-based work for `hamedonassar95/Devobs`. This is a plan; it does not authorize services, costs, data transfer, deployments, inference, workflow dispatch, or gate changes.

Read the [repository alignment and capability inventory](DEVOBS_AI_RESEARCH_ALIGNMENT_2026.md) first. The owner supplied a curated research-to-Codex handoff on 2026-11-13; this documentation update reconciles its recommendations against the current repository. The complete original Deep Research report/export was not found in the workspace or connected Google Drive, so P0 remains partial. Research-derived claims absent from the supplied handoff remain unverified.

## Outcome and guardrails

Move from the existing local DevOps intelligence and repository checks toward a bounded service only when each independent evidence gate passes. The near-term target is **verified, owner-approved staging**, not an unconditional commercial launch.

- Preserve AI-1 through AI-7, the AI-9 thresholds, Issue #237 acceptance criteria, P01 NO-GO, and the Phase 8 human-approval boundary.
- Keep existing GitHub Actions, CodeQL, Trivy, Gitleaks, Bandit, `pip-audit`, PostgreSQL RLS tests, Prometheus, Grafana, Alertmanager, and local OpenTelemetry. Add no duplicate pipelines or monitoring services.
- Make each future implementation one small feature branch and one independent PR against the latest verified `main`. Review and merge are separate human decisions tied to the exact head SHA.
- Never put raw incidents, private logs, customer data, credentials, or model outputs in Git. Use external controlled storage for restricted evaluation input; commit only approved, minimized evidence.
- Do not change thresholds, source contracts, public exposure, billing, secrets, IAM, repository rules, or deployment configuration to manufacture a pass.
- Mark unknown evidence `UNVERIFIED` or `BLOCKED`; a successful test proves only the behavior it exercised.

## Priority sequence

| Priority | Milestone | Dependency | Exit result |
| --- | --- | --- | --- |
| P0 | Reconcile the available 2026 research handoff | Curated handoff supplied; the complete original Deep Research export remains unavailable | This PR maps the supplied recommendations to repository evidence and dispositions. P0 becomes **partial**, not complete, until the full report/bibliography is supplied or confirmed unavailable by the owner. No implementation is authorized. |
| P1 | Resolve P01 provider and hosted-staging evidence | P0 handoff reconciliation plus owner decision on provider, region, data scope, and enforceable all-in cap | Every unchanged P01 and Issue #237 criterion is backed by SHA-bound test/runtime evidence plus explicit owner GO. If cost enforcement cannot be proven, stop and keep NO-GO. |
| P2 | Conduct AI-9 natural-incident evaluation | Source provenance, license/privacy approval, independent labels/root causes, preregistration | A valid independent evaluation reports per-source/per-seed or per-slice results against unchanged thresholds; a failed or unsupported slice remains failed/inconclusive. Human release approval remains separate. |
| P3 | Validate bounded staging operations and observability | P1 provider approval and secure staging; AI-9 can remain a separate gate | Measured health, tenant isolation, restore, SLO/alert and data-retention evidence on one exact candidate SHA; no public telemetry or automated remediation. |
| P4 | Consider a restricted pilot | P01 GO, AI-9 decision, security/privacy review, support and rollback ownership | A one-service, one-tenant, advisory-only pilot with explicit owner scope and documented rollback. Not a general production release. |
| P5 | Reassess further research capabilities | P0 complete; demonstrated user need and cost/security review | Add only one validated capability per PR; keep agents, training, traces, and autonomous actions deferred until their separate gates pass. |

P1 and P2 are distinct gates. P01 infrastructure evidence does not validate model quality; a dataset score does not prove safe hosted operations. Their order is a scheduling choice, not a technical dependency.

## Future Codex tasks

The tasks below are intentionally not implemented in this PR. Each task gets its own branch and PR. File lists are planned scopes; a future task must re-inspect current `main` and narrow them further before editing.

### Task 0 — Complete reconciliation if the full research export becomes available

**Priority/dependency:** P0 remains partial after the limited reconciliation in this documentation PR. Continue only if the owner supplies the full Deep Research export or an immutable source link.
**Future branch:** `docs/devobs-ai-research-source-supplement`.

**Proposed files:** `docs/strategy/DEVOBS_AI_RESEARCH_ALIGNMENT_2026.md`, `docs/strategy/DEVOBS_AI_ROADMAP_2026.md` only; update README only if the links or public summary change.

**Work:** Compare the newly supplied export against the current capability inventory and this PR's reconciliation. Add only additional source-supported recommendations/citations. For any proposed tool/provider, verify official release/version, license for code and model separately, immutable action SHA or OCI digest, price/billing terms, data path, security boundary, duplicate overlap, and testable acceptance. Classify as adopt, research-only, defer, or reject with a cited reason. Do not install packages or import code.

**Acceptance:** Every source-backed recommendation has a source section/page, repository overlap, decision, owner decision if needed, and one-task implementation plan. Unsupported claims are marked `UNVERIFIED`; unresolved licensing or costs block that proposal. `git diff --check`, internal Markdown-link check, and documentation CI pass on the exact PR head.

**Human approval:** Required before any new dependency, provider, external data transfer, paid inference, resource creation, or execution.
**Evidence:** Source/report hash or immutable URL; official vendor documentation URLs; reviewed diff and exact CI run. No service or workflow is started.

### Task 1 — P01 owner/provider evidence packet

**Priority/dependency:** P1; after provider and scope decisions. The existing Render deployment failed startup on an older SHA, its current records do not establish a healthy API, and its Free database is temporary. Do not treat Render's pipeline-minute spend control as a complete invoice cap.
**Future branch:** `docs/p01-owner-evidence-packet`.

**Proposed files:** `docs/P01_ACTIVATION_READINESS.md`; update `docs/P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md` only if a new official provider answer changes the comparative evidence; add a sanitized `docs/evidence/p01/<approved-record>.md` only after evidence is received. Reuse `scripts/check_p01_evidence.py`, `tests/test_p01_evidence.py`, and `.github/workflows/p01-evidence-gate.yml`; do not duplicate or weaken them.

**Preconditions:** The owner names an eligible provider and region, authorizes a narrowly scoped staging test, confirms synthetic-only data, and accepts the provider's official contract/pricing only after all-in cap, overrun, taxes/fees, storage, backups, egress, logs, and retention are understood. No owner-supplied credentials belong in the PR.

**Acceptance evidence:**

1. Provider-enforced ceiling covers every in-scope resource and charge. Any excluded or unbounded amount is a fail/stop, not a caveat that can be waived by a repository setting.
2. OIDC issuer, audience, client claims, key rotation and token expiry are exercised against an owner-approved nonproduction identity; no token or secret is committed.
3. Issue #237's PostgreSQL predicate contract and fail-closed policy-drift behavior are verified; cross-tenant, missing-context, revocation, connection reuse, schema-owner review and rollback evidence are reported on the exact SHA.
4. TLS certificate identity, ingress/egress restrictions, measured `/readyz` latency under an agreed bounded load, backup retention, restore drill, RPO/RTO, and rollback are demonstrated in the approved staging environment.
5. The exact head SHA, run IDs, sanitized evidence references, failures, skipped checks, and owner GO/NO-GO are recorded. Existing CI green alone is not a P01 pass.

**Tests/files if a code defect is actually demonstrated:** First choice is targeted coverage in `tests/test_intelligence_staging_app.py`, `tests/test_intelligence_api_security.py`, `tests/test_postgres_rls_integration.py`, or `tests/test_p01_evidence.py`, with a minimal corresponding fix in the source module that failed. Amend `scripts/check_p01_evidence.py` only for a concrete evidence-contract defect; preserve fail-closed acceptance rules. No new workflow is planned.

**Security/cost/approval:** No secrets access by Codex, no publicly exposed telemetry, no production data, no paid services, no provider settings change, and no deploy until the owner approves exact provider, region, cap, test, and SHA. The test must stop if live account evidence is missing or billing categories are not bounded.

### Task 2 — AI-9 natural-incident preregistration

**Priority/dependency:** P2; requires a lawful source with natural incidents, independently reviewed root causes, and privacy/retention permission. It is not blocked on P01, but a P01 pass cannot replace it.
**Future branch:** `docs/ai9-real-incident-preregistration`.

**Proposed files:** new `docs/AI9_REAL_INCIDENT_PREREGISTRATION.md`; update `docs/AI_EVALUATION_DATASETS.md` with source rights and suitability. Do not edit consumed holdout artifacts, frozen seeds, thresholds, or the production detector.

**Acceptance:** Freeze source/version/hash, eligibility and exclusion rules, service/metric mapping, cadence/missingness handling, independent label review, evaluator/comparator revision, exact metrics, sample-size rationale, holdout boundaries, and stop conditions before scores are seen. State explicitly whether the source supports every current AI-9 criterion. A source that cannot test a required metric is `NOT EVALUABLE`, not a pass.

**Tests:** Documentation/internal-link and existing fixture-integrity checks; add only a narrowly scoped preregistration contract test if it checks a real machine-readable format that will actually be consumed. No raw evidence is added to the repository and no holdout run occurs in this task.

**Security/cost/approval:** Obtain data-owner permission and independent privacy review. Use offline processing only; no raw log or customer-data upload and no paid inference. A separate exact one-time human authorization is required before any sealed evaluation.

### Task 3 — AI-9 evaluator compatibility and independent run

**Priority/dependency:** after Task 2 is reviewed and an approved dataset is available.
**Future branches/PRs:** `feat/ai9-eval-adapter` for any justified adapter; `docs/ai9-independent-results` for the later result record. These are separate tasks/PRs.

**Proposed files:** Reuse [`scripts/ai_intelligence/ai9_coherent_onset_v3.mjs`](../../scripts/ai_intelligence/ai9_coherent_onset_v3.mjs) only if the approved data natively satisfies its unchanged input contract. If not, first propose a separately reviewed adapter with exact files and tests; do not interpolate timestamps, invent labels, alter thresholds, or silently substitute a different detector. Store no private dataset in Git. For the result-only PR, add a sanitized `docs/AI9_REAL_INCIDENT_RESULTS.md` and only aggregate metadata needed to independently verify it.

**Tests/acceptance:** Positive and negative fixtures, source/hash integrity, split/holdout leakage prevention, per-incident or per-source denominators, false positives, missed incidents, detection delay, RCA Top-3 where labels support it, and abstention on missing evidence. Report each preregistered slice independently; any invalid source, test failure, or gate miss remains `FAIL`/`INCONCLUSIVE`. Record evaluator SHA, detector SHA, run ID, authorized seeds or run identifier, exact metrics, and independent reviewers. Do not rerun consumed synthetic seeds.

**Security/cost/approval:** Local/offline, no model API keys or cloud upload. Owner authorizes the exact source, evaluator SHA, test command, and one-time run before execution. Independent reviewers decide whether the evidence supports the gate; the evaluator cannot approve itself.

### Task 4 — Bounded staging operations and telemetry

**Priority/dependency:** after Task 1's approved staging and privacy design; separate from AI-9 scoring.
**Future branch:** `feat/devobs-staging-operations-evidence`.

**Proposed files:** Reuse `.github/workflows/devobs-staging-smoke.yml`, `.github/workflows/p01-evidence-gate.yml`, `scripts/devobs_intelligence/staging_smoke.py`, and `docs/integrations/opentelemetry.md`. Change `scripts/devobs_intelligence/otel_metrics.py`, `tests/test_otel_api_metrics.py`, or Collector configuration only if an approved operational question cannot be answered by the already implemented local histogram and existing Prometheus target. No traces or log payload pipeline is in the current proposal.

**Acceptance:** One named service, bounded metric allowlist, tenant-safe identity, no sensitive attributes, retention/deletion owner, tested scrape/alert behavior, and measured resource/cost impact. Existing Collector image, Prometheus, and dashboards are reused. Any hosted endpoint requires a separate privacy, identity, budget, and explicit deploy approval.

**Tests:** Existing OTel contract and local synthetic smoke tests; Compose and Collector validation; exact-head CI. Tests remain local unless the owner explicitly authorizes a controlled hosted staging run.

### Task 5 — Restricted pilot decision

**Priority/dependency:** after P01, AI-9, and the relevant security/privacy/operational evidence are accepted.
**Future branch:** `docs/devobs-restricted-pilot-decision`.

**Proposed files:** a new `docs/PRODUCTION_PILOT_READINESS.md` and narrowly scoped updates to `docs/DEVOBS_READINESS_CURRENT.md` and `STATE.md` only after fresh exact-SHA evidence exists. This task is not part of the present audit and cannot change gate thresholds.

**Acceptance:** named owner/operator, one bounded service/tenant, SLO and alert thresholds, support/on-call, rollback/restore rehearsal, data retention/deletion, incident escalation, cost ceilings, abuse controls, and explicit human GO tied to the reviewed SHA. Automated remediation, autonomous merge, and broad SaaS availability remain out of scope.

**Human approval:** Explicit decision for that exact pilot scope and SHA. A green PR, static Pages publish, document, or configured workflow is not approval.

## Evidence and release discipline for every future task

Every PR description and result record must include:

- exact base SHA, head SHA, workflow/run ID, command, exit code, and last relevant output;
- pass/fail/skip/block status for each acceptance check, with the reason for every skip;
- dataset source/version/hash, preregistration/run ID/seed only when a run is explicitly authorized; no invented or reused seed evidence;
- owner and independent reviewer decisions, each bound to the exact scope and SHA;
- changed files, cost/privacy/security effects, and a rollback description.

PRs stay separate: no bundling a provider decision, evaluation, code change, and production activation into one approval. The owner reviews and merges each verified PR. This roadmap itself leaves every release gate unchanged.

## Rollback and stop conditions

- Documentation-only tasks: revert the documentation commit/PR; no runtime rollback applies.
- Code tasks: define a minimal reversible commit and test rollback before merge; do not delete databases, volumes, evidence, or secrets as rollback.
- Stop on missing data rights, unverified price/cap, failed CI, failed negative isolation tests, unknown TLS/identity behavior, absent recovery evidence, untrusted source content, or missing human approval.
- Do not bypass a blocked check by editing fixtures, thresholds, allowed paths, workflow conditions, ledger state, or provider claims.

## Immediate next task

Review this handoff-reconciliation PR against exact base/head evidence. If the full Deep Research export is available later, use Task 0 to supplement the source map before selecting any new tool, provider, image, or implementation. For staging, the next evidence prerequisite remains an owner decision on provider, region, data scope, and an enforceable all-in cap, followed by separately authorized staging evidence; **P01 stays NO-GO/BLOCKED** until all acceptance criteria and owner GO are met. **AI-9 remains separately BLOCKED** until lawful natural incidents, independent root-cause labels, preregistration, and valid evaluation evidence are available. Neither gate is changed by this roadmap or a green CI run.
