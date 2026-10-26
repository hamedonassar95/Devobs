# Devobs production-readiness status — current evidence

**Assessment date:** 2026-10-26 (UTC)  
**Repository:** [`hamedonassar95/Devobs`](https://github.com/hamedonassar95/Devobs)  
**Evidence revision:** `22237c9a8d02f1e42230f4e9fbf200e7e2d55b20` (main; Trivy integration PR #255)  
**Scope:** Read-only reconciliation of GitHub state and repository contents. No code, workflow, cloud, production, secrets, or branch-protection changes were made for this assessment.

## Executive summary

**VERIFIED — limited production readiness:** the static HTML site is deployed through a guarded GitHub Pages pipeline, and the latest main validation and Pages deployment verified here passed on the evidence SHA. The Docker image is built and scanned in CI; Terraform configuration is validated without applying infrastructure; Kubernetes and local monitoring manifests exist. These are repository/CI capabilities, not evidence that the API, Kubernetes workload, managed database, or a multi-tenant SaaS service is deployed.

**UNVERIFIED — cloud/API/SaaS production:** no live API or managed tenant service deployment was verified. No Kubernetes cluster deployment, production Artifact Registry, production telemetry endpoint, backup restore drill, customer onboarding, or billing system was evidenced. This assessment is not a security certification or go-live approval.

## Evidence basis and classification

- **VERIFIED:** directly observed in GitHub API/CLI output, a successful workflow/deployment record, or files at the evidence revision.
- **UNVERIFIED:** not confirmed by available evidence; this does not imply the capability is absent everywhere.
- **ASSUMED:** an explicitly stated interpretation, not direct runtime evidence.

The repository's prior security/readiness assessments retain their historical dates and SHAs. In particular, [the security baseline dated 2026-10-24](security/security-baseline-2026-10-24.md), [AI Core status dated 2026-10-25](AI_INTELLIGENCE_CORE.md), and [AI roadmap evidence dated 2026-10-25](AI_DEVOPS_2027_GAP_EXECUTION.md) are not rewritten here. This document records the newer snapshot separately.

## Pull request reconciliation

**VERIFIED:** GitHub API state observed 2026-10-26; PRs #246–#252 and #254–#258 are merged. PRs #253 and #259 remain open and unmerged.

| PR | State / base | Current finding |
|---|---|---|
| [#246](https://github.com/hamedonassar95/Devobs/pull/246) | Merged → main | Audit atomic append and readiness paths. |
| [#247](https://github.com/hamedonassar95/Devobs/pull/247) | Merged → main | CI on pushes and pull requests. |
| [#248](https://github.com/hamedonassar95/Devobs/pull/248) | Merged (stacked) | Static-site Docker image; its original base was #247's branch. |
| [#249](https://github.com/hamedonassar95/Devobs/pull/249) | Merged (stacked) | Artifact Registry Terraform baseline; its original base was #248's branch. |
| [#250](https://github.com/hamedonassar95/Devobs/pull/250) | Merged (stacked) | Hardened optional Kubernetes manifests; its original base was #248's branch. |
| [#251](https://github.com/hamedonassar95/Devobs/pull/251) | Merged → main | Local Prometheus/Grafana starter. |
| [#252](https://github.com/hamedonassar95/Devobs/pull/252) | Merged → main | Historical readiness audit; its prior evidence remains historical. |
| [#254](https://github.com/hamedonassar95/Devobs/pull/254) | Merged → main | Docker image health check. |
| [#255](https://github.com/hamedonassar95/Devobs/pull/255) | Merged → main | Pinned Trivy image vulnerability scanning. |
| [#256](https://github.com/hamedonassar95/Devobs/pull/256) | Merged → main | GCS remote-state backend placeholder. |
| [#257](https://github.com/hamedonassar95/Devobs/pull/257) | Merged → main | Prometheus self-scrape alerts. |
| [#258](https://github.com/hamedonassar95/Devobs/pull/258) | Merged → main | Cosign installer action update. |

**VERIFIED — open PR #253:** head `78483b69ca8a61eef32c787a982e08520b1264cc`, base `main`, open, merge state `DIRTY`. It duplicates the already merged Trivy integration from #255; leave both PR states unchanged. Its most recent observed checks included passing `validate`, image scan, Docker build, Terraform validation, CodeQL, and Vercel preview, but the branch is reported conflicting. Do not treat those checks as authority to merge it.

**VERIFIED — open PR #259:** head `4ce9efe90f4e631b59d419d5185dd83821770f50`, base `main`, open and unmerged. Two CI runs on that SHA (push and pull request, run IDs [40299895746](https://github.com/hamedonassar95/Devobs/actions/runs/40299895746) and [40299897608](https://github.com/hamedonassar95/Devobs/actions/runs/40299897608)) failed in `python-tests / Python validation` at “Run configured tests”; `validate` consequently failed. The observed Docker build, Trivy scan, Terraform validation, PostgreSQL RLS, Node, CodeQL, and preview checks passed in those runs; production-release was skipped. **UNVERIFIED:** the downloadable job log was unavailable during this assessment, so the precise failing test name/output is not asserted. Keep this as a merge blocker until the owner reviews the failure and a new run passes. No code or tests were changed here.

## Completed capabilities (source and CI, not cloud deployment)

- **VERIFIED:** CI checks `validate`, static-site contract/HTTP behavior, Python and Node checks as selected, security checks, Docker build/smoke, Trivy scan, Terraform validation, and disposable PostgreSQL RLS integration as configured in the current workflow. Latest main CI run [40299822021](https://github.com/hamedonassar95/Devobs/actions/runs/40299822021) on evidence SHA completed successfully. Its `production-release / verify-production` job succeeded; automatic restoration jobs were skipped because they were not needed.
- **VERIFIED:** the CI Docker image is an Nginx-based static-site image; `Dockerfile` exists, is built in CI, and is vulnerability-scanned by the merged #255 workflow. The scan does not publish this image to a container registry.
- **VERIFIED:** `infra/terraform` defines Artifact Registry and a GCS backend placeholder. CI runs formatting, backend-disabled init and validate. The workflow does not run `terraform plan` or `apply`; the backend bucket placeholder is not provisioned evidence.
- **VERIFIED:** `k8s/` contains a two-replica Deployment, internal Service and ConfigMap with non-root/read-only filesystem controls, probes and resource limits. No cluster was provisioned or deployment observed.
- **VERIFIED:** `monitoring/compose.yml` binds Prometheus and Grafana to loopback, uses a private Compose network and pinned image digests. Prometheus self-scrape/alerts exist. No monitoring containers or external service metrics endpoint were verified live.
- **VERIFIED:** AI intelligence source contains offline evidence/adviser, tenant-scoped API and data contracts, synthetic evaluation, and governance gates. Existing docs explicitly distinguish those source/test implementations from deployed model inference or a hosted SaaS service.

## CI and Pages deployment evidence

- **VERIFIED:** latest main CI: [run 40299822021](https://github.com/hamedonassar95/Devobs/actions/runs/40299822021), event push, SHA `22237c9a8d02f1e42230f4e9fbf200e7e2d55b20`, conclusion success, created 2026-10-26 09:28 UTC. Container build, Trivy scan, Terraform validation and `validate` succeeded.
- **VERIFIED:** GitHub Pages deployment ID `7328347162` targets ref `main` and the same SHA; deployment status is `success`, updated 2026-10-26 09:29:56 UTC. URL: <https://hamedonassar95.github.io/Devobs/>. CI's production verification passed.
- **VERIFIED:** this proves the static Pages deployment and its workflow health check for that SHA. It does not prove availability/SLOs beyond that check, API deployment, Kubernetes deployment, Artifact Registry provisioning, or hosted SaaS readiness.
- **VERIFIED:** PR-triggered `production-release` jobs for #253/#259 were skipped; that is consistent with the workflow's push-to-main safeguard. A successful Vercel status on a PR is a preview, not production deployment evidence.

## Open readiness blockers and risks

### Deployment and cloud

- **VERIFIED:** Pages is deployed; CI builds but does not publish the Docker image to a registry.
- **VERIFIED:** Terraform uses a placeholder GCS state bucket; no `apply` was executed or observed. Creating managed resources requires owner authorization and may incur charges.
- **UNVERIFIED:** provisioned Artifact Registry, GKE/other cluster, Render/Supabase services, production API, or live OTel collector. Manifests and staging proposal documents are not deployment evidence.
- **UNVERIFIED:** current branch protection, deployment environment reviewer settings, and manual approval requirements were not re-read from repository settings in this task. Older assessments must not be substituted for current settings evidence.
- **VERIFIED:** latest #259 CI failure is an open merge blocker, even though the current main CI and Pages deploy succeeded.

### Security and AI governance

- **VERIFIED:** workflow permissions and pinned actions are checked in CI; this does not establish a complete independent security review of every integration or provider.
- **VERIFIED:** AI guidance keeps model output advisory and requires deterministic CI/human decisions. Repository inventory and cost gates are present.
- **UNVERIFIED:** external audit anchoring, live signed/action-bound human approval, production kill switch, calibrated evaluation, independently reviewed customer-data redaction, and current provider-specific cost ceilings.
- **VERIFIED:** NIST/ISO/OWASP mappings in existing documents are design/control mappings, not certifications. No SOC 2, ISO 27001/42001 or legal compliance assessment is claimed.
- **VERIFIED:** do not submit raw customer logs, prompts, traces, credentials, ticket text, or embeddings to the offline prototype without an approved privacy architecture and explicit purpose/retention controls.

### Multi-tenant SaaS gaps

- **VERIFIED:** the source has tenant-boundary and PostgreSQL RLS tests, but they run against a disposable CI database and do not prove isolation in a managed hosted service.
- **UNVERIFIED:** production identity-provider configuration, tenant onboarding and lifecycle, hosted database authorization against malicious/direct SQL access, tenant-scoped secret storage, rate/size limits under live load, backups and restore RPO/RTO, SLO/on-call operations, billing/metering, support, customer terms/DPA, deletion/export, licensing reconciliation, and penetration testing.
- **VERIFIED:** the prior [commercial readiness gate](PRODUCT_SAAS_READINESS.md) explicitly blocks external customer onboarding until these controls are evidenced.

### Cost and privacy approvals

- **VERIFIED:** AI budget approval switches are operator gates, not dollar caps. Provider billing, quota, cost attribution, and per-tenant limits need separate review before enabling billable inference.
- **VERIFIED:** Terraform/cloud apply, paid service tiers, production identity/database setup, or external telemetry transfer require owner-approved scope, region, budget, privacy/retention, and security review. None was performed in this documentation task.

## Prioritized roadmap

1. **P0 — resolve PR #259 regression:** inspect the failing Python test output, reproduce on exact head SHA, fix implementation/test legitimately, and rerun full required CI. Do not weaken tests to make checks green.
2. **P0 — reconcile PR #253:** keep it open pending owner decision; it overlaps merged #255 and has a dirty merge state. Close/rebase only under explicit maintainer direction; no action taken here.
3. **P1 — verify live governance settings:** read-only confirm required checks, review approvals/Code Owners, bypass actors, Pages environment restrictions, and protected deployment reviewers. Record date and evidence links.
4. **P1 — define staging target and approval:** choose whether API/SaaS staging is actually in scope, then obtain explicit provider, region, data class, budget, and privacy approvals before provisioning.
5. **P1 — prove hosted tenant controls:** deploy only to approved staging; test cross-tenant authorization, OIDC/JWKS rotation/revocation, non-admin DB roles, concurrency/connection-pool safety, rate limits, audit retention, backup restore, and failure recovery.
6. **P2 — instrument and measure:** add approved service metrics/OTel pipeline, define SLOs and cost/quality denominators, then collect real data before making ROI or availability claims.
7. **P2 — independent assurance:** threat model and penetration test, legal/privacy and licensing review, incident response exercise, then reassess whether external SaaS onboarding is justified.

## Official references

- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [Trivy artifact signature verification](https://trivy.dev/latest/docs/verification/)
- [OWASP Agent Control Standard](https://owasp.org/www-project-agentic-ai-threats/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
- [GitHub Actions workflow runs REST API](https://docs.github.com/en/rest/actions/workflow-runs)
- [GitHub deployments REST API](https://docs.github.com/en/rest/deployments/statuses)

## Assessment limits

**UNVERIFIED:** GitHub ruleset/environment settings were not queried in this assessment. PR #259 failed logs were not downloadable through the available API session; only failing job/step metadata was verified. No cloud console, cluster, managed database, live API, external customer, or SaaS account was accessed. Historical documents retain their original scope and timestamps.
