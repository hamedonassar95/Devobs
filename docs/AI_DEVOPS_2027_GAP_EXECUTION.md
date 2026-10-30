# DevObs AI DevOps Intelligence — 2027 target gap plan

**Canonical project:** `hamedonassar95/Devobs`. **Historical base main when authored:** `230712b060e2969b55be8812e00d5cf961952d6a`. **Historical branch:** `feat/devobs-intelligence-context-eval-2027`. As of 2026-10-25, current `main` is `85956696df6f8722e2c8d7d1d88f7a03653c2d56`. This plan did not transfer repositories, mutate `main`, deploy production, configure secrets/billing, or enable autonomous remediation.

> The section below is the historical plan baseline. The 2026-10-30 status update supersedes any current-state statement below when the two differ.

## Current status update — 2026-10-30

**Verified main:** `b29b4b2d7d2db1cc81c50b85d5eb3b0cb7f8a4c4`. PR [#292](https://github.com/hamedonassar95/Devobs/pull/292) added a CI check for the pinned synthetic Decisions fixture. PR [#293](https://github.com/hamedonassar95/Devobs/pull/293) added an offline prompt-injection request-boundary regression test. CI run [40982044145](https://github.com/hamedonassar95/Devobs/actions/runs/40982044145), CodeQL run [40982043480](https://github.com/hamedonassar95/Devobs/actions/runs/40982043480), static-site publication, and post-publication verification succeeded. These repository checks do not verify live AI quality or SaaS readiness.

**Decision boundary:** AI-9 remains **FAIL**, based on the owner-provided synthetic report. Its reported branch and source files are not available in this checkout, so those results have not been independently reproduced. P01 remains **NO-GO / BLOCKED**; the owner activation record in [`P01_ACTIVATION_READINESS.md`](P01_ACTIVATION_READINESS.md) is unsigned and its provider, region, spend cap, data, identity, and operational decisions remain blank. No model, real data, provider call, or managed staging resource was used in PRs #292 or #293.

### MLOps component evidence matrix

| Component | Repository status | Evidence and boundary |
| --- | --- | --- |
| Secrets and software dependency scanning | Present for repository code/dependencies and the static image | [CI security jobs](../.github/workflows/ci.yml) run Bandit, pip-audit, Gitleaks, and Trivy. No model artifact is scanned. |
| Data validation | Partial | [Synthetic fixture validator](../scripts/validate_ai_eval_fixtures.py) checks digest, provenance label, schema and policy version in CI; it does not validate live or training data. |
| Data-poisoning detection | Not present | [Evaluation dataset limits](AI_EVALUATION_DATASETS.md) explicitly distinguish fixture integrity from semantic poisoning detection. |
| Model-file safety and signing | Not present | No common ML artifact file was found in the repository file scan. The Cosign check in CI verifies the Trivy release, not a model. |
| Adversarial and prompt-injection tests | Partial | [Request-boundary test](../tests/test_openai_decisions_triage.py) verifies synthetic text remains untrusted input. It does not measure model resistance. |
| SBOM and model card | Partial | [AI-BOM](ai/ai-bom-2027.json) and [system card](AI_INTELLIGENCE_2027_SYSTEM_CARD.md) describe an offline module, not a deployed model artifact and its provenance. |
| Model registry | Not present | No model/version registry implementation was found in the source search. |
| Retraining pipeline | Not present | No model-training pipeline was found in the source search. |
| Model-quality evaluation gate | Partial | Offline evaluators exist; fixture integrity runs in CI. No model-output quality threshold is enforced by CI. |
| Model canary and rollback | Partial | Static Pages has a guarded rollback workflow and runbook; no model rollout or model rollback exists. |
| Drift monitoring | Partial | [Local anomaly detector](../scripts/ai_intelligence/anomaly_detector.mjs) and tests use offline signals; this is not live model/data-drift monitoring. |
| Performance and cost monitoring | Partial | [AI governance](AI_GOVERNANCE_2027.md) documents request caps and an explicit inference-approval variable; its live setting is unverified, and measured per-model latency and dollar cost are absent. |
| Alert grouping | Partial | [Deterministic correlation](../scripts/devobs_intelligence/correlation.py) and tests cover offline evidence; there is no live model-alert pipeline. |
| Kill switch | Partial | `DEVOBS_AI_BUDGET_APPROVED` gates hosted inference workflows; it is not an emergency switch for a deployed model service. |
| Runbooks | Partial | [Incident response](INCIDENT_RESPONSE.md) and [rollback](ROLLBACK_RUNBOOK.md) runbooks exist for repository and static-site operations, not model lifecycle operations. |

### Safe sequence for remaining work

1. Recover and review the exact AI-9 branch and commit; keep its reported measurements separate from any new run.
2. Obtain an owner-completed P01 decision before creating staging resources, moving data, or enabling hosted inference.
3. Once an actual model and authorized data source exist, define artifact provenance and signing, dataset poisoning controls, registry and retraining ownership, and a pre-registered evaluation gate together.
4. Only after those gates pass, design a model canary and rollback plus live drift, performance, cost, alert, kill-switch, and model-operation runbooks.

Do not represent the remaining rows as implemented by adding empty scaffolding. Without an actual model, reviewed evaluation data, and the required owner decisions, doing so would not provide verifiable MLOps controls.

## Evidence baseline, October 25 2026
VERIFIED in source: `scripts/devobs_intelligence` implements bounded GitHub/GitLab CI evidence, an offline adviser, deterministic policies, local audit, tenant scope, offline evaluation, a token-verified read API contract and SQLite demo. `docs/AI_EVALUATION_DATASETS.md` contains offline incident-investigator scoring datasets. `docs/AI_GOVERNANCE_2027.md` describes AI approval and cost controls. PRs #213, #216, #218 and #219 are merged as [`b93f4de`](https://github.com/hamedonassar95/Devobs/commit/b93f4de23e9c9049a0d773a1e1148417050281b6), [`a060412`](https://github.com/hamedonassar95/Devobs/commit/a06041290ceeb43a313b6ab5a405e55340bf2e11), [`d9adfb0`](https://github.com/hamedonassar95/Devobs/commit/d9adfb06ee2ef4609e0a6910e404fb60ee24619b) and [`35108f1`](https://github.com/hamedonassar95/Devobs/commit/35108f1fd8ac64326c80ab7b75d2a38e4295cb72). PR #218's RLS integration tests use an ephemeral PostgreSQL service in CI and do **not** prove hosted database isolation or production readiness.

**Gap:** no live OTLP ingestion, service dependency graph, trusted incident retrieval, topology-aware incident narratives, objectively measured top-1/top-3 RCA, durable cross-service trace export, authentic reviewer-bound approval, externally anchored audit, working SaaS or certification.

## Source evidence and uncertainty
- Gartner 2025-06-25 **forecasts** over 40% agentic AI project cancellations by end 2027, not a recorded outcome.
- OpenTelemetry semantic conventions v1.44 (2026) provide conventions for observability; some agent/GenAI conventions are development-stage or moved. Never invent guaranteed agent signal interoperability.
- NIST AI RMF is voluntarily applicable; ISO/IEC 42001 defines management-system requirements. No audit or certification is earned by file changes.
- OWASP requires trust separation, user/tenant isolation, bounded tools, explicit approvals, kill switches and evidence evaluation.

## Planned incremental work

### Phase A: structured context (offline only)
1. Implement bounded allowlisted numeric telemetry with source SHA, tenant and service IDs, no raw log/trace/prompt payloads.
2. Topology graph with validated tenant-specific service dependencies, bounded neighbor expansion and deterministic impacted-services queries.
3. Closed vocabulary incident-memory retrieval by tenant/service/category and approved runbook ID. Do not embed private incidents, and block cross-tenant retrieval. No vector service provisioned.
4. Tests: malformed/mixed-tenant telemetry, topo cycles, missing nodes, limits, stale SHA, and memory poisoning isolation; Python full suite as acceptance.

### Phase B: deterministic correlation and evaluation
1. Feed only parsed signal aggregates to the preexisting adviser; return minimal causal hypotheses and SHA-bound evidence, no model tools/actions.
2. Rank candidate root services through bounded topology/context. Avoid claiming learned probabilities. Confidence labels explicitly uncalibrated.
3. Golden synthetic top-1/top-3 and false-action, override/cost metrics; require documented minimal dataset size before claiming enterprise acceptance.
4. Tests for mismatched tenant, SHA and evidence staleness, insufficient evidence, replayed/invalid events, and review-only decisions.

### Phase C: governance evidence package
1. Machine-readable AI-BOM/system card/controls evidence schema, clearly separating implemented, unverified, and future components.
2. Governance and KPI/SLI scorecard specification with trustworthy numerators and denominator; no invented live values.
3. Level 0 evidence-only and Level 1 proposals permitted by policy; L2+ and deploy/rollback/scale blocked until approved execution service and independent authorization.
4. CI/security on the exact candidate SHA, no auto merge.

## Deferred until independently configured and funded
True OTel Collector/OTLP endpoints, actual production graph metadata, embeddings and vector privacy controls, remote AI model, delegated MCP tools, Slack/Teams actor verification, durable immutable cloud audit anchoring, PostgreSQL hosted tenant isolation, on-call/SLO measurement, cloud IaC application, Kubernetes, backups and restore exercises, SOC 2/ISO certifications, EU-specific legal assessments, payment provider, enterprise customer contracts.

**Acceptance:** nonzero behavioral tests, all existing tests, security and CI validate on exact PR; failure = hold PR Draft. No arbitrary shell/action access, no per-action human approval implementation via model text alone.

## Official links
- https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027
- https://opentelemetry.io/docs/specs/semconv/
- https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html
- https://www.nist.gov/itl/ai-risk-management-framework
- https://www.iso.org/standard/81230.html
