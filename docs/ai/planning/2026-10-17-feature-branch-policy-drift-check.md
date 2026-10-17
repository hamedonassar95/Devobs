---
phase: planning
title: Default-Branch Policy Drift Audit
description: Reviewed implementation plan for repository governance auditing
---

# Default-Branch Policy Drift Audit

## Milestones

- [x] Confirm the current GitHub policy and identify a safe read-only reference pattern.
- [x] Implement the API audit and deterministic unit tests.
- [x] Add weekly/manual workflow triggers and least permissions.
- [x] Document scope, recovery steps, and verification evidence.
- [x] Merge the read-only audit implementation to `main`.
- [x] Treat the hosted `bypass_actors: null` representation as an empty list, with regression coverage (PR #167).
- [x] Add optional read-only ruleset authentication (PR #169).
- [ ] Configure or verify `POLICY_AUDIT_TOKEN` with `Administration: read` and record a passing hosted audit run.

## Task breakdown

### Baseline and design

- [x] Verify the default branch and active ruleset against the GitHub API.
- [x] Select read-only audit behavior; reject the reference repository's mutating branch-protection script for this use.
- [x] Set acceptance checks and error behavior before implementation.

### Implementation and verification

- [x] Add scripts/check_repo_policy.py using only the Python standard library.
- [x] Add unit coverage for pass, drift, missing ruleset, and invalid repository input.
- [x] Add a scheduled/manual workflow with contents: read, optional policy-audit token, and pinned checkout.
- [x] Update the DevOps roadmap and automation hub.
- [x] Run targeted tests, repository checks, and AI DevKit lifecycle lint.
- [x] Review and merge the initial implementation; inspect the first hosted run.
- [x] Treat `bypass_actors: null` as empty while failing closed for missing or malformed values; add regression tests.
- [x] Fall back to `GITHUB_TOKEN` and provide a clear diagnostic when the ruleset API omits `bypass_actors`.
- [ ] Set or validate the fine-grained `POLICY_AUDIT_TOKEN` secret and confirm a successful hosted audit.

## Dependencies and risks

- GitHub Actions and public GitHub REST API must be reachable on the runner.
- The weekly audit performs four GET requests. GitHub may omit protected ruleset fields from the workflow default token; `POLICY_AUDIT_TOKEN` must be limited to `Administration: read` for this repository.
- The hosted API may return `bypass_actors` as `null` or `[]` for no actors; the audit accepts both but rejects missing or malformed fields.
- API shape or repository visibility changes must fail closed and be fixed through reviewed code changes.
- This feature checks branch governance; it does not provision infrastructure or add AI model behavior.

## Resources and rollback

- No cloud account, external service, or paid runner is required. The hosted ruleset audit needs a repository-scoped, read-only Actions secret to expose protected ruleset details.
- To disable only the recurring check, remove the schedule trigger or revert the workflow in a reviewed change. The script can remain available for manual/local audit.
- If the audit reports drift, inspect and restore the expected rules in GitHub repository Settings; do not let the workflow edit them.

## Current follow-up status

The `null` response handling, regression coverage, and optional authentication are merged. Requirements, design, runbooks, and roadmap now describe the same token behavior and setup path. No application behavior or deployment configuration changed. The only outstanding task is external GitHub configuration: verify `POLICY_AUDIT_TOKEN` has repository-scoped `Administration: read`, manually run the audit, and record a passing hosted run. Until then, the latest hosted result remains inconclusive.
