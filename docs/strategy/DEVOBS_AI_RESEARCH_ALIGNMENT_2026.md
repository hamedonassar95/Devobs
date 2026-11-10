# Devobs AI research alignment — 2026

**Review status:** `READY_FOR_REVIEW` — repository evidence audit only. This is not production completion, a gate approval, or an implementation of future roadmap tasks.

**Repository:** `hamedonassar95/Devobs`
**Audited base:** `main` at `2ea1f58a6323f4ccc0e6553be4b2fb61e6017c99`
**Audit date:** 2026-11-10 UTC
**Change scope:** this document, [`DEVOBS_AI_ROADMAP_2026.md`](DEVOBS_AI_ROADMAP_2026.md), and the README links only.

## Research input and confidence

The request names `DEVOBS_AI_CODEX_HANDOFF_2026.md` as a source of truth, but that file was not present in the repository tree or available workspace at audit time. A full Deep Research report was not attached either. **UNVERIFIED:** the research report's claims, proposed components, citations, licensing, and recommendations. This file is therefore a repository-grounded interim alignment, not a claim that unavailable research was reviewed. Reconcile its recommendations in a later documentation PR after the source is supplied.

All status claims below are limited to the inspected source revision, existing documents, and named GitHub runs. Source code, CI, a local smoke test, and a static Pages publish do not independently prove a hosted service, customer safety, or production readiness.

## Evidence baseline

| Evidence | Result | Boundary |
| --- | --- | --- |
| Exact `main` revision | `2ea1f58a6323f4ccc0e6553be4b2fb61e6017c99`, merge of PR #509 | Verified with GitHub API and `git fetch origin main`. |
| Main CI | [Run 42805723188](https://github.com/hamedonassar95/Devobs/actions/runs/42805723188) succeeded on the exact SHA | PostgreSQL RLS, security, container/Trivy, Terraform, Python validation, `validate`, Pages publish and static-site verification passed. `node-tests` and incident/recovery jobs were skipped by existing path/condition rules. |
| Main CodeQL | [Run 42805723573](https://github.com/hamedonassar95/Devobs/actions/runs/42805723573) succeeded on the exact SHA | Python, JavaScript/TypeScript, and Actions analyses passed. |
| PR #509 | [Merged](https://github.com/hamedonassar95/Devobs/pull/509), head `015f8b84d1e4233beb2cb7e03082267cd4dba5ed` | Its push CI [42804796252](https://github.com/hamedonassar95/Devobs/actions/runs/42804796252) ran Python, Node, PostgreSQL RLS, security, container/Trivy, Terraform and `validate`; all passed. The new revocation, pooled-connection context, and partial-DDL rollback cases passed in CI. |
| Milestone ledger | `python3 scripts/milestone_ledger.py --summary` reports `latest_pr: 508`, `merged_milestones: 165`, and three open gates | The ledger on this main SHA has not recorded merged PR #509. PR #510 proposes that documentation update but remains an open Draft; its contents are not main evidence. |
| Current readiness | [`docs/DEVOBS_READINESS_CURRENT.md`](../DEVOBS_READINESS_CURRENT.md) | The latest recorded state is AI-9 blocked, P01 blocked, and Codex runtime acceptance open. Its top checkpoint predates PR #509; use the exact GitHub run above for the newer CI result. |

## Capability inventory

“Implemented” means the implementation exists in the repository. “Verified” means the specific source, tests, or run named here passed. Neither term implies that a hosted product is operating.

| Capability | Classification | Existing evidence | What is not established |
| --- | --- | --- | --- |
| AI-1 event intake and validation | **Implemented; locally verified** | Local schema and JSONL ingestion in [`scripts/ai_intelligence/event_ingest.mjs`](../../scripts/ai_intelligence/event_ingest.mjs); [`docs/AI_EVENT_INGESTION.md`](../AI_EVENT_INGESTION.md) and tests | Authenticated, continuously running production event ingestion. |
| AI-2 anomaly detection | **Implemented; experimental/offline** | Statistical detector and synthetic inputs in [`scripts/ai_intelligence/anomaly_detector.mjs`](../../scripts/ai_intelligence/anomaly_detector.mjs); [`docs/AI_ANOMALY_DETECTION.md`](../AI_ANOMALY_DETECTION.md) | Live telemetry coverage, calibrated alert quality, or service-level SLOs. |
| AI-3 incident analysis | **Implemented; advisory/offline** | Local log grouping and incident hypotheses in [`scripts/ai_intelligence/incident_analysis.mjs`](../../scripts/ai_intelligence/incident_analysis.mjs); [`docs/AI_INCIDENT_ANALYSIS.md`](../AI_INCIDENT_ANALYSIS.md) | An independently confirmed root cause from production incidents. |
| AI-4 recommendations | **Implemented; advisory** | Static runbook matching in [`scripts/ai_intelligence/recommendations.mjs`](../../scripts/ai_intelligence/recommendations.mjs); [`docs/AI_RECOMMENDATIONS.md`](../AI_RECOMMENDATIONS.md) | Automatic or model-approved remediation. Human approval remains separate. |
| AI-5 trends | **Implemented; local/experimental** | Local trend report and forecast code; [`docs/AI_TREND_REPORTS.md`](../AI_TREND_REPORTS.md) | Forecast quality on production workloads or a measured operational benefit. |
| AI-6 feedback | **Implemented; local/limited** | Opt-in local accept/reject preference ledger; [`docs/AI_FEEDBACK_LEARNING.md`](../AI_FEEDBACK_LEARNING.md) | Model training, calibrated quality improvement, or a production feedback loop. |
| AI-7 dashboard/API | **Implemented; local, read-only** | Local dashboard and API; [`docs/AI_LOCAL_DASHBOARD.md`](../AI_LOCAL_DASHBOARD.md) | Public hosting, multi-customer operations, or a production API. |
| AI-8 | **Not defined/approved** | No approved AI-8 phase in the current project plan | Do not invent an AI-8 feature to fill a numbering gap. |
| AI-9 detector and evaluator | **Experimental; FAIL/BLOCKED** | Synthetic and injected-fault experiments, frozen synthetic holdout, preregistrations and results in [`docs/AI9_V3_INDEPENDENT_EVAL_GATE.md`](../AI9_V3_INDEPENDENT_EVAL_GATE.md) and [`docs/AI9_EXTERNAL_DATASET_ASSESSMENT.md`](../AI9_EXTERNAL_DATASET_ASSESSMENT.md) | Natural, independently labeled production incidents with provenance/privacy approval and a valid evaluation of the Devobs detector. The four frozen synthetic seeds are already consumed. RCAEval's reported supplemental baseline is not a Devobs production-detector result. |
| P01 staging / SaaS gate | **Partially implemented; NO-GO/BLOCKED** | OIDC verification, PostgreSQL tenant/RLS code and CI tests, exact-SHA-bound evidence checking, manual evidence gate, and staging smoke contract. PRs #236/#238/#240 and #509 address repository-side controls; Issue [#237](https://github.com/hamedonassar95/Devobs/issues/237) remains open. | A healthy current hosted API, complete provider-enforced spend cap, live OIDC, hosted tenant isolation, accepted network/TLS posture, restore proof, and owner GO. The recorded Render deployment used an older SHA and failed startup; no successful `/readyz` is recorded. |
| Local OpenTelemetry metrics | **Implemented; local-only** | PRs #500/#501; [`docs/integrations/opentelemetry.md`](../integrations/opentelemetry.md), existing Collector profile and Prometheus scrape job; one optional request-duration histogram | Production traces/logs, public ingest, tenant-bound instrumentation, durable retention, or P01/AI-9 evidence. Do not add another Collector, Prometheus, Grafana, or Alertmanager. |
| CI and supply-chain checks | **Implemented; verified on audited main SHA** | Existing [`ci.yml`](../../.github/workflows/ci.yml), CodeQL, Gitleaks, Bandit, `pip-audit`, Trivy on one locally built image, PostgreSQL RLS, Terraform validation, and Pages validation/publish. | A green pipeline proves only the jobs that ran. It does not prove API deployment, model quality, P01, or a completed recovery exercise. |
| Optional model/provider integrations | **Present as guarded options** | Ollama/LocalAI local profiles; separate OpenAI/Gemini diagnosis adapters; Vertex and other workflow integrations are documented/configured behind existing controls | Default inference, paid calls, or a live customer path. Local Ollama/LocalAI do not automatically feed AI-1 through AI-7. |
| K8sGPT / HolmesGPT / MLflow | **Documented examples or candidate only** | [`k8s/`](../../k8s/README.md), [`mlops/README.md`](../../mlops/README.md) | Installed production agents, a model registry, training pipeline, or deployed MLOps service. |
| Model registry/training lifecycle | **Missing** | The repository's 2027 gap assessment says there is no model registry or training pipeline; the current AI system is primarily deterministic/offline. | Model artifact provenance, registry, training/retraining, model-specific rollback and live drift/cost monitoring. Do not create empty scaffolding. |
| Codex agent runtime | **Configured; runtime acceptance OPEN** | [`docs/CODEX_AGENT_OPERATING_MODEL.md`](../CODEX_AGENT_OPERATING_MODEL.md) and repository agent configuration | Live subagent discovery/execution or a trusted production agent boundary. Configuration is not runtime evidence. |

## P01 and AI-9 are separate release gates

- **P01** is an environment and operations decision: complete cost enforcement, selected provider/region, identity, tenant boundaries, network/TLS, service acceptance, recovery, and explicit owner approval. Passing RLS CI is valuable evidence for one part of Issue #237; it does not substitute for hosted evidence.
- **Issue #237's repository-side acceptance** covers fail-closed policy drift, the PostgreSQL predicate contract, cross-tenant and missing-context denials, connection context/revocation, schema-owner review, `/readyz` measurement, and SHA-bound CI plus independent staging evidence. PRs #236/#238/#240/#509 implement or test parts of this contract; the merged CI evidence does not close the live staging, load, provider, recovery, or owner-decision gaps.
- **AI-9** is an evaluation and data-governance decision: real naturally occurring incidents, independently reviewed labels/root causes, provenance and privacy permission, a preregistered method, and per-slice results under unchanged thresholds. Synthetic or injected-fault scores remain supplementary.
- One gate can progress without the other. A P01 staging pass does not prove AI-9 quality; an AI-9 dataset result does not prove P01 operations.

## Reuse and non-duplication decisions

1. Reuse AI-1 through AI-7 and their existing local contracts; do not create parallel incident pipelines, dashboards, recommenders, or feedback stores.
2. Reuse the current CI, CodeQL, Trivy, Gitleaks, PostgreSQL RLS and approval/evidence checks; do not add duplicate security workflows or weaken any gate.
3. Reuse the existing optional OpenTelemetry Collector and Prometheus deployment. The single local histogram is the current instrumentation scope; do not add another monitoring stack or send production data.
4. Keep local models optional and explicit. Do not enable paid inference, provider credentials, auto-remediation, or workflow dispatch as a side effect of this roadmap.
5. Do not create empty model registry, retraining, drift, trace-backend, or SaaS scaffolding without a reviewed, measurable use case and the required owner decisions. The existing 2027 gap plan already identifies these as unestablished.

## Existing versions and official-reference check

No new action, image, package, model, or provider is proposed by this audit. Existing pins are recorded here to prevent accidental duplicate or floating-tag work in a later task.

| Existing component | Pin in main | Audit treatment | Official reference |
| --- | --- | --- | --- |
| OpenTelemetry Collector Contrib | `0.165.0@sha256:e40d61f10c9a617cca1ffd1be4d7e2b3a4b0f0001798ff07e58cabe82e618cea` | Reuse for optional local metrics only; no new collector | [Official image](https://hub.docker.com/r/otel/opentelemetry-collector-contrib), [v0.165.0 license](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/LICENSE), [Collector configuration](https://opentelemetry.io/docs/collector/configuration/) |
| Prometheus / Grafana / Alertmanager | `3.15.1`, `13.2.4`, `0.34.2`, each image pinned by digest in `monitoring/compose.yml` | Reuse current local stack; no duplicate service | [Prometheus project](https://prometheus.io/docs/introduction/overview/), [Grafana documentation](https://grafana.com/docs/) |
| Ollama / LocalAI | `v0.40.15` and `v4.12.1`, immutable image digests in [`models/README.md`](../../models/README.md) | Optional local runtimes only; model weights require their own license/resource review | [Ollama Docker guide](https://docs.ollama.com/docker), [LocalAI container guide](https://github.com/mudler/LocalAI/blob/v4.12.1/docs/content/getting-started/containers.md) |
| GitHub Actions | Full commit-SHA pins with version comments in workflows | Reuse current jobs; every future action must remain full-SHA pinned and least-privilege | [GitHub action pinning guidance](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-third-party-actions) |
| Render staging | Existing free service/database; not a proposed production provider | No redeploy or settings change. The current configuration and pricing do not satisfy the accepted P01 evidence by themselves. | [Render billing FAQ](https://render.com/docs/faq), [Free service limits](https://render.com/docs/free), [Postgres backups](https://render.com/docs/postgresql-backups) |

For any future component proposal, its task must cite the publisher's official release/install documentation, exact version, immutable action SHA or OCI digest, applicable source and model licenses, supported security controls, and official billing terms before code is added. Mutable `latest` tags and unverified price claims are not acceptable evidence. The image digests above are repository pins; they are not a new live registry lookup in this PR.

## Unresolved evidence and next source needed

- **BLOCKED:** content-level comparison with `DEVOBS_AI_CODEX_HANDOFF_2026.md` and the full research report until those source files are supplied.
- **BLOCKED:** P01 until an eligible provider demonstrates the approved all-in ceiling and the remaining runtime/security/recovery controls, followed by owner GO.
- **BLOCKED:** AI-9 until authorized natural incidents and independent evaluation evidence exist. Do not consume old seeds or relabel a benchmark as production evidence.
- **OPEN:** Codex runtime acceptance requires a real trusted-runtime check, not a config-file claim.

The next task is to reconcile the missing research handoff against this inventory. No feature implementation is approved by this alignment record.
