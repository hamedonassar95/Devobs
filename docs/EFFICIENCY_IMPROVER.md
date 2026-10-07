# Devobs Efficiency Improver pilot

## Purpose and scope

A measurement-driven agentic workflow adapted from GitHub Next's
[Efficiency Improver](https://github.com/githubnext/agentics/blob/main/docs/efficiency-improver.md).
This is a repository automation capability, not a widget added to the public site.
The first pilot focuses on `index.html` and `assets/**`; observations about CI or
recovery efficiency stay in the run summary for a separate reviewed change.

The manual trigger, 15-minute agent timeout, one draft PR per run, read-only
agent permissions, protected-file blocking and exclusive patch allowlist are
configured in `.github/workflows/efficiency-improver.md`. Safe-output jobs receive
the write permissions needed to create the PR. The agent cannot merge it.
A dedicated repo-memory job has contents: write to retain progress on its memory
branch; this is separate from the allowlisted site patch. No monthly summary
issue is enabled in this pilot. Routine issue/comment output is not enabled;
gh-aw also supplies its standard incomplete-run diagnostics. Daily scheduling and existing-PR updates are
deferred until manual acceptance passes. No guaranteed improvement is promised.

## Verified baseline on 2026-10-07

Repository: `hamedonassar95/Devobs`.
Base commit: `4c8fbf20efd5de79756bdabb0913bc17b9d79845` (PR #54).

- Hosted CI run `37632424881`: success.
- Hosted Deploy Pages run `37632459834`: success.
- Hosted Deployment Health Check run `37635385730`: success.
- Local Python discovery: 84 tests passed.
- Local Node incident guard suite: 22 tests passed.
- Local page contract / HTTP smoke check: passed.
- Existing active Protect main ruleset requires `validate`, CodeQL and PRs;
  its required approving review count is currently zero. Draft status and the
  absence of merge/auto-merge outputs preserve human control for this pilot;
  the ruleset itself does not enforce a reviewer approval.

## Compile and review

The source and compiled lock workflow must be committed together. The compiler
version is `v0.89.21`, matching the existing incident investigator. Its official
Linux release SHA256 checksum was verified before use.

```sh
gh extension install github/gh-aw --pin v0.89.21
gh aw compile efficiency-improver --strict --no-check-update --action-mode action --action-tag 924af5fdc64061cfbf66fb584c8b07e2ac230c60
python3 -m unittest discover -s tests -v
node --test tests/incident_guard.test.cjs
python3 scripts/check_site.py
```

Only compile this workflow; do not regenerate the existing investigator as part
of this change. Review the compiled write jobs and patch restrictions before merge.

## Activation and acceptance

1. Review this installation PR and its required hosted checks, then merge through
   the normal protected-branch process when approved.
2. Verify Copilot authentication using the repository's existing engine setup.
   This pilot uses `copilot` / `gpt-4.1`, matching the incident investigator, and
   requires a valid `COPILOT_GITHUB_TOKEN` with Copilot access. Secret presence,
   validity, model access and quota have NOT been verified by this installation.
   Never paste tokens into PRs, issues, reports or chat.
3. Verify that GitHub Actions is allowed to create pull requests under repository
   and organization policy. Do not broaden settings preemptively.
4. In Actions select the new Efficiency Improver workflow and Run workflow on main,
   or use `gh aw run efficiency-improver`. It has no automatic schedule.
5. Inspect the run: no direct main write or deployment, no guardrail changes,
   at most one draft PR, factual memory and reproducible measurements. A justified
   noop when no worthwhile optimization exists is also a successful outcome.
6. If a draft PR is created, confirm every changed path matches `index.html` or
   `assets/**`, reproduce its before/after evidence, and verify accessibility and
   behavior. Required `validate` and CodeQL checks must actually appear and pass.
7. PRs written with `GITHUB_TOKEN` generally do not trigger other workflows. Do not
   mistake local tests or a manual CI run on main for PR-associated required checks.
   If checks are absent, leave the PR unmerged and configure the documented
   `GH_AW_CI_TRIGGER_TOKEN` handoff with a suitably scoped credential or GitHub App
   after reviewing access; then validate that checks run on the PR's actual SHA.
   No new credential is added by this installation.
8. Keep the outcome **PENDING HUMAN APPROVAL** until a maintainer reviews the PR.
   Enable a daily schedule only in a later reviewed change after these checks pass.

Compilation and local tests do not prove a live agent run succeeded. The first
authenticated manual run remains an explicit acceptance step after installation.

## Disable

Use Actions > Efficiency Improver > Disable workflow to pause manual runs, or
revert this installation PR through the normal protected-branch process. No
existing deployment, investigator or recovery configuration is changed here.

## References

- https://github.com/githubnext/agentics/blob/main/workflows/efficiency-improver.md
- https://github.github.com/gh-aw/reference/safe-outputs-pull-requests/
- https://github.github.com/gh-aw/reference/engines/
- https://github.github.com/gh-aw/reference/safe-outputs-triggering-ci/

## First manual acceptance run and correction

Run [37643815861](https://github.com/hamedonassar95/Devobs/actions/runs/37643815861)
proved engine authentication and agent execution. It proposed whitespace-only
minification (claimed 345 raw bytes / 56 gzip bytes saved). That proposal was
not accepted as a worthwhile trade-off for this hand-maintained site.

The detection job appeared successful, but its logs showed HTTP 429 and no
detection_result.json. The compiler defaults to continue-on-error=true; strict
compilation alone does not make this runtime gate fail closed. The workflow now
sets safe-outputs.threat-detection.continue-on-error=false explicitly, so a
detection failure blocks both safe outputs and memory persistence. Tracking
issues for detection are disabled; diagnostics remain in the run logs.

GitHub then rejected PR creation because the repository disables Actions-created
PRs. The framework pushed branch efficiency/minify-index-html-41921c72efec71d4
and created fallback Issue #56 despite fallback-as-issue=false. No actual PR was
created; the agent's noop text claiming creation was premature. The prompt now
distinguishes requested safe output from a confirmed GitHub PR and excludes
whitespace-only HTML minification. Repository permissions have not been expanded.

Live acceptance remains incomplete. Before another write-capable run, obtain
explicit approval for the repository-wide Actions create/approve-PR setting,
resolve or allow the inference rate limit to clear, and verify an actual detector
result and PR-associated CI checks. Do not infer success from a green job badge.
