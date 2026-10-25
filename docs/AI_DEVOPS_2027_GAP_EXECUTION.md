# DevObs AI DevOps Intelligence — 2027 target gap plan

**Canonical project:** `hamedonassar95/Devobs`. **Historical base main when authored:** `230712b060e2969b55be8812e00d5cf961952d6a`. **Historical branch:** `feat/devobs-intelligence-context-eval-2027`. As of 2026-10-25, current `main` is `85956696df6f8722e2c8d7d1d88f7a03653c2d56`. This plan did not transfer repositories, mutate `main`, deploy production, configure secrets/billing, or enable autonomous remediation.

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
