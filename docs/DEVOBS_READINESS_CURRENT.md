# Devobs production readiness — current evidence

**Assessment time:** 2026-10-26 12:23 UTC
**Repository:** [`hamedonassar95/Devobs`](https://github.com/hamedonassar95/Devobs)
**Evidence revision:** `4fc78b8f696d2fd78bf729e8792441ba3f032b46` ([main commit](https://github.com/hamedonassar95/Devobs/commit/4fc78b8f696d2fd78bf729e8792441ba3f032b46))
**Scope:** Read-only GitHub metadata, PR/check evidence and repository documents/source. This report does not alter source, workflows, infrastructure, settings, secrets, cloud resources or billing.

## Executive summary

**VERIFIED:** The current main SHA passed CI `validate`, built and scanned the static-site container, ran Python, Node, PostgreSQL RLS and security checks, and completed the GitHub Pages publish and production verification jobs in [CI run 40321639857](https://github.com/hamedonassar95/Devobs/actions/runs/40321639857). Pages deployment [7331660361](https://github.com/hamedonassar95/Devobs/deployments/7331660361) targets this SHA and has status `success` at <https://hamedonassar95.github.io/Devobs/>.

**UNVERIFIED:** This proves the static Pages path and its workflow health check for one SHA. It does not prove a deployed multi-tenant API, managed staging/database, Kubernetes workload, SaaS customer service, ongoing availability/SLO, or commercial readiness. No production readiness certification or go-live approval is claimed.

**VERIFIED:** PR #259's initial Python-test failure was real on its earlier head and remains part of history. The fix passed on a later exact head; #259 was merged as `4fc78b8…`. The current blocker queue is now #262, then #253. The authoritative [P00–P12 roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md) remains the execution plan; this report only refreshes evidence and status.

## Evidence labels and scope

- **VERIFIED:** directly observed in source at the evidence SHA or in the linked GitHub API/workflow/deployment record.
- **UNVERIFIED:** not established by the evidence available here; absence from a repository or run does not prove a capability is absent elsewhere.
- **ASSUMED:** interpretation or future recommendation, not a fact about a live system.

Historical findings in [the repository audit](REPO_AUDIT.md), [governance audit](DEVOBS_MAIN_GOVERNANCE_AUDIT.md), [commercial readiness document](PRODUCT_SAAS_READINESS.md), and [roadmap evidence snapshots](plans/2026-10-26-devobs-production-execution-roadmap.md) retain their original SHAs and dates. This report supersedes their stale current-status statements only; it does not rewrite those historical records or replace the canonical P00–P12 sequence.

## Pull request reconciliation

**VERIFIED at the assessment time:** states and heads below were refreshed from GitHub's PR API. GitHub documents the [pull-request REST fields](https://docs.github.com/en/rest/pulls/pulls).

| PR | Current state | Evidence and disposition |
| --- | --- | --- |
| [#259](https://github.com/hamedonassar95/Devobs/pull/259) | **MERGED** into main | Updated `anthropics/claude-code-action` from 1.0.252 to 1.0.261 and added a pin-contract test. The final head `2b4a086f57a05aac98073fa6cae2e7f1727f3d37` passed Python validation and `validate` in [run 40321419362](https://github.com/hamedonassar95/Devobs/actions/runs/40321419362); merge commit is the current evidence SHA. |
| [#262](https://github.com/hamedonassar95/Devobs/pull/262) | **OPEN**, unmerged, not Draft; dirty against main | Head `b5a1b9ea27ef2b26c9bbcfe1b7a218b705c8ffe0`. Its added report uses an earlier main snapshot (`22237c9…`) and describes #259 as blocked after failed tests at older head `4ce9efe…`. The old report and its CI result are historical, not current. This new report is a replacement candidate; leave #262 open until the owner approves this replacement. Close #262 as superseded only after that approval. |
| [#253](https://github.com/hamedonassar95/Devobs/pull/253) | **OPEN**, unmerged, dirty against main | Head `78483b69ca8a61eef32c787a982e08520b1264cc`. Its Trivy change overlaps merged [#255](https://github.com/hamedonassar95/Devobs/pull/255). Its earlier passing checks do not resolve the present dirty merge state or authorize merge/closure. |
| [#264](https://github.com/hamedonassar95/Devobs/pull/264) | **MERGED** | Added offline synthetic staging-smoke acceptance tests and documentation. These do not establish live OIDC/JWKS, managed PostgreSQL RLS, hosted TLS, service uptime or SaaS readiness. |
| [#265](https://github.com/hamedonassar95/Devobs/pull/265) | **MERGED** | Added the canonical P00–P12 roadmap. The merge-time Pages publish step succeeded, but production verification/restoration steps in that run were canceled; see the dated deployment note below. |

### #259 failure history and successful correction

**VERIFIED:** the older #259 head `4ce9efe90f4e631b59d419d5185dd83821770f50` failed `Run configured tests` and aggregate `validate` in both [push run 40299895746](https://github.com/hamedonassar95/Devobs/actions/runs/40299895746) and [PR run 40299897608](https://github.com/hamedonassar95/Devobs/actions/runs/40299897608). The precise failing test output is not asserted here. A later corrected head passed Python validation and `validate` in [run 40321419362](https://github.com/hamedonassar95/Devobs/actions/runs/40321419362), then merged to main. The failed runs remain historical evidence; they are not the current CI state.

**VERIFIED in current source:** `.github/workflows/claude-code-assistant.yml` pins the action to full commit `16f9f71ab9c490faf367f94dd294897edc25be33` with version comment `v1.0.261`; `tests/test_claude_code_assistant_workflow.py` checks that pin and the workflow's trust/permission boundaries. The successful current-main CI also ran the repository's pinned-action checker.

## Current main CI and Pages evidence

- **VERIFIED:** main is `4fc78b8f696d2fd78bf729e8792441ba3f032b46`. [CI run 40321639857](https://github.com/hamedonassar95/Devobs/actions/runs/40321639857) has conclusion `success` on that exact SHA. Its `validate`, Python validation, Node, PostgreSQL RLS, security, container build, Trivy scan, Terraform validation and site-contract jobs succeeded. The controlled incident drill was skipped.
- **VERIFIED:** in that same run, `production-release / Publish production site` and `production-release / verify / verify-production` both succeeded. Pages deployment [7331660361](https://github.com/hamedonassar95/Devobs/deployments/7331660361) reports `success` for the same SHA. GitHub documents [workflow-run fields](https://docs.github.com/en/rest/actions/workflow-runs) and [deployment statuses](https://docs.github.com/en/rest/deployments/statuses).
- **VERIFIED:** an earlier run after the #265 merge, [40320845306](https://github.com/hamedonassar95/Devobs/actions/runs/40320845306), completed the Pages publish job but canceled the later production-verification and restoration jobs. The later full success on `4fc78b8…` is newer evidence; neither run proves continuous availability between checks. No new availability probe was performed for this report.
- **VERIFIED:** the CI workflow validates Terraform but does not run `terraform apply`; its Docker image is built/scanned, not pushed by this CI path. The Kubernetes manifests and local monitoring configuration are repository artifacts, not deployment records.

## Deployed product versus unverified services

- **VERIFIED:** README describes the published product as a static HTML site on GitHub Pages. Current successful Pages evidence above is for that static site.
- **VERIFIED:** repository source contains a narrow read-only tenant/project CI API contract, signed-token checks, PostgreSQL RLS schema/integration tests, an operator-triggered smoke verifier, and a proposed Render Blueprint. CI PostgreSQL tests use a disposable fixture; `render.yaml` is explicitly proposed with auto-deploy off.
- **UNVERIFIED:** a live Devobs API or managed staging deployment, configured identity provider/JWKS lifecycle, hosted database/role/RLS state, Kubernetes cluster deployment, Artifact Registry contents, live telemetry, backup restore, production SLOs or incident staffing. A green CI run, Vercel PR preview, or deployment manifest is not evidence of those services.
- **VERIFIED:** the merged staging acceptance suite uses synthetic offline responses. Its own [scope document](STAGING_ACCEPTANCE.md) distinguishes those checks from live OIDC/JWKS rotation, hosted TLS, PostgreSQL RLS and uptime.

## Security, AI governance, and commercial gaps

- **VERIFIED:** current CI includes pinned GitHub Actions checks, Bandit/dependency/security scanning, Gitleaks, Trivy image scanning and disposable PostgreSQL RLS tests. Passing these jobs is not an exhaustive independent security audit or guarantee of no vulnerabilities.
- **VERIFIED:** repository AI workflows are advisory and budget-gated; a successful workflow conclusion may mean inference was skipped. No AI review status is represented here as human approval.
- **VERIFIED:** the [AI review status comment](https://github.com/hamedonassar95/Devobs/pull/266#issuecomment-6416038140) says `DEVOBS_AI_BUDGET_APPROVED` is required to authorize potentially billable inference. **UNVERIFIED:** that approval signal does not establish a dollar-denominated hard cap, provider-account quota, cost telemetry or attribution, or per-tenant budget enforcement; these safeguards require separate provider- and tenant-specific owner review before paid inference is enabled.
- **UNVERIFIED:** managed identity and tenant lifecycle, isolation across future write/search/export/background-work paths, durable externally anchored audit, real backup/restore RPO/RTO, tested SLO/on-call, payment/billing/metering, lawful commercial eligibility, customer terms/DPA, deletion/export operations, license reconciliation, penetration test and independent assurance.
- **VERIFIED:** existing [commercial readiness guidance](PRODUCT_SAAS_READINESS.md) states there is no billing system and blocks external customer onboarding pending these controls. The narrow authenticated read path must not be described as a complete customer-facing auth/RBAC or subscription product.
- **VERIFIED:** no SOC 2, ISO or other compliance certification is claimed by source files, tests or this report.

## Governance and P00 status

**VERIFIED:** the current effective `main` rules response requires a pull request and strict `validate`, blocks deletion and non-fast-forward updates, and reports zero required approving reviews and Code Owner review disabled. The repository ruleset API is documented at [GitHub REST rules](https://docs.github.com/en/rest/repos/rules?apiVersion=2022-11-28) and [available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets). **UNVERIFIED:** policies outside the returned repository-level rules response.

**VERIFIED status reconciliation:** P00 remains **ACTIVE**. #259 now has a merged disposition; #262 remains the next owner decision, followed by #253, then P00 owner signoff. P01–P12 remain **BLOCKED** until the canonical roadmap's preceding gates and signoffs are met. This status report does not mark any phase complete or authorize infrastructure, spend, production changes or customer onboarding.

**Next single task:** owner reviews this replacement candidate and decides whether to approve it as the current report for #262. Only after approval should #262 be closed as superseded; then review/resolve #253 separately. Do not close #262 from this documentation PR.

## Cost, privacy, and assessment limits

- **VERIFIED:** no cloud/provider settings, deployment environments, secrets, credentials, billing or external customer data were accessed or changed for this report. No deployment, migration, Terraform plan/apply/destroy or model inference was initiated.
- **UNVERIFIED:** provider/account ownership, hosting region and budget, data residency/classification/retention, secret-management design, IdP, billing eligibility, live service controls and current operational availability beyond the linked Pages workflow check.
- **ASSUMED:** any future staging or commercial work requires explicit owner approval of provider, scope, region, budget, data handling and rollback before provisioning or customer-data use. This report is not a go-live approval.

## Official references

- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [GitHub REST pull requests](https://docs.github.com/en/rest/pulls/pulls)
- [GitHub Actions workflow runs](https://docs.github.com/en/rest/actions/workflow-runs)
- [GitHub deployment statuses](https://docs.github.com/en/rest/deployments/statuses)
- [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Trivy verification](https://trivy.dev/latest/docs/verification/)
- [OWASP Agent Control Standard project](https://owasp.org/www-project-agentic-ai-threats/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
