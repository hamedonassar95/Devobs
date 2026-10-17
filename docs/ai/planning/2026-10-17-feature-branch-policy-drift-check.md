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
- [ ] Fix the hosted API response case where an empty bypass list is returned as `null`, then confirm a passing hosted audit.

## Task breakdown

### Baseline and design

- [x] Verify the default branch and active ruleset against the GitHub API.
- [x] Select read-only audit behavior; reject the reference repository's mutating branch-protection script for this use.
- [x] Set acceptance checks and error behavior before implementation.

### Implementation and verification

- [x] Add scripts/check_repo_policy.py using only the Python standard library.
- [x] Add unit coverage for pass, drift, missing ruleset, and invalid repository input.
- [x] Add a scheduled/manual workflow with contents: read, no token passed to the audit, and pinned checkout.
- [x] Update the DevOps roadmap and automation hub.
- [x] Run targeted tests, repository checks, and AI DevKit lifecycle lint.
- [x] Review and merge the initial implementation; inspect the first hosted run.
- [ ] Treat `bypass_actors: null` as empty while failing closed for missing or malformed values; add regression tests and rerun the hosted audit.

## Dependencies and risks

- GitHub Actions and public GitHub REST API must be reachable on the runner.
- Public unauthenticated API access is rate-limited; this weekly audit performs only four GET requests.
- The hosted run can serialize an empty `bypass_actors` field as `null`; the audit must accept that documented empty representation without accepting missing or malformed fields.
- API shape or repository visibility changes must fail closed and be fixed through reviewed code changes.
- This feature checks branch governance; it does not provision infrastructure or add AI model behavior.

## Resources and rollback

- No cloud account, external service, secret, or paid runner is required.
- To disable only the recurring check, remove the schedule trigger or revert the workflow in a reviewed change. The script can remain available for manual/local audit.
- If the audit reports drift, inspect and restore the expected rules in GitHub repository Settings; do not let the workflow edit them.
