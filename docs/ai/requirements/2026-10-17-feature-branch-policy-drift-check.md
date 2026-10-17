---
phase: requirements
title: Default-Branch Policy Drift Audit
description: Requirements for detecting changes to GitHub branch governance
---

# Default-Branch Policy Drift Audit

## Problem

GitHub repository settings can change outside the code review history. Devobs already requires the validate check and applies a branch ruleset, but the existing checks do not periodically confirm that these account-level controls remain active. The reference DevOps-Bash-tools repository has a read-only protected-branch audit; Devobs needs a check that also verifies its own required rules and CodeQL thresholds.

## Goals

- Check the current default branch and the Protect main ruleset through GitHub's REST API.
- Report a missing or weakened policy in a weekly GitHub Actions run and in manual runs.
- Keep the audit read-only, deterministic, dependency-free, and limited to this repository.
- Make the finding visible in the workflow log and summary so a maintainer can restore settings in GitHub.

## Non-goals

- Do not create, update, or delete branch protection, rulesets, collaborators, or repository settings.
- Do not make this scheduled audit a required status check for pull requests.
- Do not add Docker, Kubernetes, Terraform, Ansible, cloud infrastructure, paid monitoring, or an LLM call for a static Pages site.
- Do not claim that the audit proves external AI credentials, billing, model quality, or runtime observability.

## User stories

- As the repository maintainer, I want a weekly check of the required default-branch rules so that accidental policy drift is visible.
- As a maintainer investigating a failed audit, I want the exact missing or weakened rule named so that I can repair it in GitHub Settings.
- As a contributor, I want the check to use only a dedicated read-only credential when GitHub hides protected ruleset fields, and never write repository settings or print credentials.

## Acceptance criteria

- The check reads repository metadata, the default branch, the named ruleset, and its details from the GitHub API.
- It verifies active branch scope, default-branch inclusion, no bypass actors, deletion and force-push blocks, the strict validate required check, a pull-request rule, and CodeQL thresholds.
- It interprets a null or empty `bypass_actors` value as no configured bypass actors; a missing field or any other non-list value is an inconclusive API response and exits 2.
- If GitHub omits `bypass_actors` for the workflow's default token, the audit reports an inconclusive result and directs the maintainer to configure `POLICY_AUDIT_TOKEN` with fine-grained `Administration: read` access for this repository.
- It exits 0 when the baseline is intact, 1 when policy drift is found, and 2 when the audit cannot complete.
- Unit tests cover a passing policy and representative missing, weakened, and invalid-input cases.
- A weekly schedule and manual dispatch run the audit with read-only permissions; the regular CI/deployment path is not changed.

## Constraints and assumptions

- The target repository is public, but GitHub may omit protected ruleset fields from the default `GITHUB_TOKEN` response. The workflow uses the optional `POLICY_AUDIT_TOKEN` secret for the audit when configured and otherwise falls back to `GITHUB_TOKEN`; the dedicated token is limited to `Administration: read` for this repository.
- The policy baseline is the current Protect main ruleset on the default branch; changing the expected baseline should be reviewed as a code change.
- GitHub API, repository visibility, or rate-limit errors must fail visibly rather than being reported as a successful audit.

## Open items

- Configure or verify `POLICY_AUDIT_TOKEN` using [the repository audit setup guide](../../REPOSITORY_POLICY_AUDIT.md), then run the workflow manually and confirm it passes. If the API still omits `bypass_actors`, inspect token scope and repository access; do not broaden permissions beyond `Administration: read`.
