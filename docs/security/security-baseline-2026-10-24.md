# Devobs security baseline — 2026-10-24

Status: preliminary evidence-backed review; **not** a security certification.

## Scope and immutable evidence
- Repository: https://github.com/hamedonassar95/Devobs
- Reviewed base commit: `9e7f61dd522b0622005c9699deff511d49c97614` on `main`.
- Ruleset: https://github.com/hamedonassar95/Devobs/rules/24507159 (active at review time).
- Successful main CI: https://github.com/hamedonassar95/Devobs/actions/runs/40054121578
- Successful PR CI: https://github.com/hamedonassar95/Devobs/actions/runs/40054007120
- Successful AI code review: https://github.com/hamedonassar95/Devobs/actions/runs/40054007124
- Failed AgentDust Doctor Sandbox: https://github.com/hamedonassar95/Devobs/actions/runs/40049074799
- Later successful AgentDust Doctor Sandbox: https://github.com/hamedonassar95/Devobs/actions/runs/40049721946

## Verified baseline
1. Default branch `main` is protected by active `Protect main` ruleset.
2. Ruleset requires `validate` status check with strict up-to-date branch policy and enables a CodeQL code-scanning rule.
3. Ruleset has `required_approving_review_count: 0`, `require_code_owner_review: false`, and `required_review_thread_resolution: false`. PR workflow alone therefore does **not** ensure human approval.
4. Inspected CI, AI code review, incident response and deployment workflows pin several third-party actions by commit SHA and use `persist-credentials: false` on inspected checkout steps.
5. These observations do not prove every workflow or every run is secure.

## Recommended work, in order (NOT applied)
- **P1 — Review gate:** decide on a human-review policy (at least one approval and stale-review dismissal if operationally feasible); verify how solo-maintainer approval will work before changing ruleset. Require resolution of review threads where practical.
- **P1 — Incident boundary:** inspect `workflow_run` trust boundary, artifact provenance, token permissions, and whether untrusted PR artifacts can influence privileged jobs. Do not execute untrusted code with write tokens.
- **P1 — Failure analysis:** compare failed and passing AgentDust Doctor Sandbox logs and commit SHAs; do not claim root-cause resolution based only on a later green run.
- **P2 — Permissions:** audit all workflows for minimum `GITHUB_TOKEN` permissions, use of secrets, `pull_request_target`, external downloads, and third-party actions; inspect deployment environment protections and rollback approval gates.
- **P2 — CI coverage:** check that `validate` reliably exists for all required PR paths and cannot be bypassed by conditional skips.
- **P2 — Evidence:** run an approved, read-only repository audit and attach results to a follow-up PR. No credentials should be copied into issues or logs.

## Change-control policy
- No direct writes to `main`.
- No deployment, rollback, automatic merge, or ruleset modification in this PR.
- Any workflow changes must be separate, minimally scoped PRs with reviewed diffs and explicit approval.
- This file is a planning artifact, not evidence of tests executed by this PR.
