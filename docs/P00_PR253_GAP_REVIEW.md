# P00 PR #253 Docker image scan gap review

**Assessment time:** 2026-10-26 13:18 UTC
**Repository:** [`hamedonassar95/Devobs`](https://github.com/hamedonassar95/Devobs)
**Main evidence SHA:** [`56961b7764ed50204f0f065edb9e8ed12b58b81d`](https://github.com/hamedonassar95/Devobs/commit/56961b7764ed50204f0f065edb9e8ed12b58b81d)

## Recommendation

**REWORK — do not merge PR #253 as submitted, and do not close it as wholly superseded.** Its workflow and Dockerfile edits duplicate the scan already on main and conflict with current main. Its scanner evaluator, behavioral tests, and MEDIUM/LOW reporting add useful coverage that main does not currently provide. If the owner chooses to continue it, carry those unique parts into the existing `container-image-scan` job in one reviewed PR, keeping a single scan job and the existing `validate`/rollback safeguards.

This is a technical recommendation, not human approval. PR [#253](https://github.com/hamedonassar95/Devobs/pull/253) remains **OPEN**, head `78483b69ca8a61eef32c787a982e08520b1264cc`, base `main`, `mergeable_state=dirty`; no merge or close was attempted.

## Current state and P00

- **VERIFIED:** PR [#255](https://github.com/hamedonassar95/Devobs/pull/255) merged as `22237c9a8d02f1e42230f4e9fbf200e7e2d55b20`. Main already contains its Dockerfile digest update and the Trivy scan job.
- **VERIFIED:** PR [#262](https://github.com/hamedonassar95/Devobs/pull/262) was closed unmerged at 13:09:54 UTC; PR #267 was merged at the same time. This refreshes the earlier P00 disposition snapshot, which still described #262 as open.
- **VERIFIED:** the previously open P1 review thread on #253's older commit `4b4dd20…` is marked `isResolved=true` and `isOutdated=true` by GitHub. It reported malformed vulnerability collections being accepted. The current PR head includes explicit list validation and regression cases for dictionary/string collections; the current-head Codex summary reports no findings. The older P1 is therefore not an outstanding current-head finding.
- **VERIFIED:** no human approval is recorded. The only submitted PR review is a bot `COMMENTED` review on the older commit. The Codex review summary for current head reports no findings; the GitHub Actions AI-review comment says inference was skipped because explicit budget approval was absent. These are not human review or AI inference evidence.
- **VERIFIED:** P00 remains **ACTIVE** until the owner records a disposition of #253 and P00 signoff. P01–P12 remain **BLOCKED**. P01 additionally needs explicit owner approval for hosting/provider, region/residency, budget and data handling, IdP/secret policy, restricted database identity, TLS/JWKS, live RLS tests and recovery evidence, as detailed in the [roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md). No infrastructure or AI action is authorized here.

## What is already on main

**VERIFIED in current main `.github/workflows/ci.yml` and `Dockerfile`:**

- The root application target is the static-site `Dockerfile`; it uses the pinned `nginxinc/nginx-unprivileged:1.31-alpine3.24-slim` digest already introduced by #255.
- `container-image-scan` already checks out `${{ inputs.source_ref || github.sha }}`, requires the root Dockerfile, builds `devobs-web:${{ github.sha }}`, installs Trivy CLI 0.76.1 with a SHA-256 checksum check and exact version-output assertion, and scans the locally built image.
- The existing scan uses `--scanners vuln`, `--ignore-unfixed=false`, and blocks HIGH/CRITICAL with nonzero Trivy exit status. The scan job is required by the existing `validate` job; rollback profile requires it to be skipped. Workflow permissions are read-only for contents and CI does not push the image.
- JSON output is uploaded for seven days. Upload uses `if-no-files-found: ignore`; when Trivy fails before producing a report, the required scan job still fails and blocks `validate`, but the artifact can be absent, reducing failure evidence.
- Main filters the scan output to HIGH/CRITICAL, so MEDIUM/LOW findings are not currently included in the report. This is the clearest reporting gap addressed by #253's evaluator.

The current [CI guide](CI.md) documents the existing Trivy gate. Main has `tests/test_docker_workflow_contract.py` and `tests/test_terraform_workflow_contract.py`, which assert that image build/scan and Terraform validation are required by `validate` and that rollback skips optional jobs. Main does **not** have `tests/test_container_image_scan.py` or a standalone scanner evaluator.

## PR #253 delta and overlap

**VERIFIED from the PR files API and exact-head contents:** #253 changes eight files (286 additions, 11 deletions): `.github/workflows/ci.yml`, `Dockerfile`, `README.md`, `docs/CI.md`, `scripts/container_image_scan.py`, `tests/test_container_image_scan.py`, and the Docker/Terraform workflow-contract tests.

| Area | Already on main | Distinct PR #253 contribution / concern |
|---|---|---|
| Workflow job and gate | Same `container-image-scan` job ID, local build, Trivy CLI, JSON artifact and `validate` dependency already exist from #255. | Adds a second definition of the same job ID, causing a conflict/duplication. Its gate and rollback logic largely repeat existing behavior. |
| Dockerfile | Main already has the exact Nginx base digest from #255. | Dockerfile change is duplicate. |
| Findings policy | HIGH/CRITICAL block; scanner errors fail the job. | Evaluator also reports MEDIUM/LOW counts without blocking, and rejects malformed report/result shapes. Useful unique capability. |
| Report | JSON artifact, seven-day retention. Missing report is ignored by upload, although scan failure still blocks `validate`. | Adds severity-count job summary and makes missing artifact an upload error after the target check succeeds. |
| Tests | Workflow contract checks gate wiring and rollback profile; no scan-parser behavior test exists on main. | Adds focused cases for clean, HIGH/CRITICAL, MEDIUM/LOW, malformed collections, missing image config, scanner failures, report/summary, and gate wiring. |
| Documentation | `docs/CI.md` describes Trivy; README does not summarize its policy. | Adds a concise README security-scan summary and more detailed failure/report behavior. Keep the useful documentation, reconciled to the final integrated workflow. |

The PR installs a versioned Trivy 0.76.1 archive and checks its checksum, but only runs `trivy --version`; main also asserts the exact version output. Both obtain archive and checksum from the same release origin, so the checksum detects corruption but is not independent signature verification. The existing main scan uses `--severity HIGH,CRITICAL`; the PR passes CRITICAL/HIGH/MEDIUM/LOW to its parser and blocks only HIGH/CRITICAL.

Both workflow versions check out `inputs.source_ref || github.sha` but tag the built image with `github.sha`. The scan still runs on the local image just built in that job; when `source_ref` differs, however, the tag/report label can misidentify the source revision. Rework should preserve `source_ref` behavior while recording the actual checked-out SHA in the image tag or report. GitHub documents that reusable workflows use the caller's `github` context in [reusable workflow documentation](https://docs.github.com/en/actions/sharing-automations/reusing-workflows#github-context).

The container smoke-test and scan jobs are separate CI jobs, so the scan job rebuilds the image rather than scanning the exact image digest that passed the smoke test. The Dockerfile's base image is digest-pinned and both jobs use the selected source revision, but no artifact digest currently binds those two builds. This is source-equivalent CI evidence, not proof of one identical image artifact being smoke-tested and scanned; no image is published by this CI path.

PR #253's `NOT_CONFIGURED` branch reports no scan if there is no root Dockerfile. A Dockerfile does exist on assessed main. The existing main workflow fails if it is missing, and `container-build` also requires it; any rework must preserve the current fail-closed `validate` behavior for this configured application target.

## Review and CI evidence

- **VERIFIED:** exact-head [PR run 40298656486](https://github.com/hamedonassar95/Devobs/actions/runs/40298656486) used PR head `78483b69ca8a61eef32c787a982e08520b1264cc` and completed successfully, including Python validation, container build, Trivy scan, Terraform, PostgreSQL RLS, security, and required `validate`. Production release was skipped. This passing run predates the current main SHA and does not remove the current merge conflict.
- **VERIFIED:** the malformed-report review thread is [resolved and outdated](https://github.com/hamedonassar95/Devobs/pull/253#discussion_r4373042509); the final PR head contains the corresponding parser validation and tests. GitHub's [pull request and review APIs](https://docs.github.com/en/rest/pulls/pulls) expose the PR head and submitted review evidence; the GraphQL review-thread result was `isResolved=true`, `isOutdated=true`.
- **VERIFIED in this review:** existing main tests ran: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_docker_workflow_contract tests.test_terraform_workflow_contract tests.test_ci_release_gate tests.test_ci_trigger_contract tests.test_shared_staging -v` — **10 tests passed**. `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_action_pins.py` — **39 workflow/template files passed**.
- **VERIFIED in this review:** PR diff was inspected without executing PR code; Markdown links in this report and README were checked; `git diff --check` passed.
- **UNVERIFIED locally:** the PR-only `scripts/container_image_scan.py` and `tests/test_container_image_scan.py` were not executed. Root `AGENTS.md` prohibits executing code from a PR target. GitHub's exact-head Python validation above did run the PR's configured tests, but that is CI evidence, not a local independent rerun. No live Trivy scan was run for this audit.

## Safest disposition and remaining gates

**REWORK:** retain the parser/tests and MEDIUM/LOW reporting only if the owner wants that additional observability; integrate them into the existing job rather than adding a duplicate job. Keep the exact-version assertion, checksum verification, root image target, `validate` dependency, rollback skip, least permissions, nonzero scanner/DB error behavior, and no-push policy. Bind image/report identity to the checked-out revision and ensure a missing/malformed report cannot pass. Carry the README summary if it accurately describes the integrated behavior. Do not merge or close #253 under this report.

P00's remaining gate is the owner's disposition of #253, followed by P00 signoff. P01 remains blocked until that signoff and its explicit provider, cost, privacy, identity, database-isolation and recovery approvals/evidence. No production deployment, image publication, paid model inference, or external provider action is claimed or authorized.

## Official references

- [Trivy image CLI](https://trivy.dev/latest/docs/references/configuration/cli/trivy_image/)
- [Trivy artifact verification](https://trivy.dev/latest/docs/verification/)
- [GitHub reusable workflow context](https://docs.github.com/en/actions/sharing-automations/reusing-workflows#github-context)
- [GitHub pull request REST API](https://docs.github.com/en/rest/pulls/pulls)
