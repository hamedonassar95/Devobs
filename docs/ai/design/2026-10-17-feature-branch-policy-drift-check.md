---
phase: design
title: Default-Branch Policy Drift Audit
description: Architecture and API contract for a read-only repository governance check
---

# Default-Branch Policy Drift Audit

## Architecture

    Weekly schedule or manual dispatch
                    |
                    v
        GitHub-hosted runner
                    |
                    v
        check_repo_policy.py
          |       |       |
          v       v       v
       repository  branch  ruleset APIs
          \       |       /
           \      v      /
            pass or named findings
                    |
                    v
           Actions run log

The workflow checks out the repository with the existing SHA-pinned checkout action. The Python standard library performs HTTPS GET requests to public GitHub endpoints; no third-party package, token, secret, external AI provider, or write endpoint is used.

## Data and API contract

The script reads:

1. GET /repos/{owner}/{repo} for default_branch.
2. GET /repos/{owner}/{repo}/branches/{default_branch} for the branch's protected state.
3. GET /repos/{owner}/{repo}/rulesets?includes_parents=true to locate the named ruleset.
4. GET /repos/{owner}/{repo}/rulesets/{ruleset_id} for enforcement, ref conditions, bypass actors, and rule parameters.

Only the repository/default-branch scope, pass status, or a list of missing/weakened controls is emitted. Raw API payloads and response headers are never printed.

## Policy baseline

- Ruleset name Protect main, target branch, enforcement active, scoped to a pattern that includes the default branch and has no matching exclusion (including ~DEFAULT_BRANCH and refs/heads globs).
- No bypass actors.
- deletion, non_fast_forward, and pull_request rules are present.
- required_status_checks includes validate and requires the branch to be up to date.
- CodeQL blocks high_or_higher security alerts and errors alert threshold.

## Failure behavior and security

The audit is fail-visible: drift exits 1; a malformed response, unavailable API, or unusable input exits 2. It does not retry indefinitely or mutate settings. API access is bounded by a 15-second timeout per request. Only fixed API paths are constructed from URL-encoded repository/branch values. The scheduled workflow is informational and independent of PR validation and deployment.

## Design decision

The reference [DevOps-Bash-tools protected-branch audit](https://github.com/hamedonassar95/DevOps-Bash-tools/blob/master/github_repos_without_branch_protections.sh) provides a read-only audit pattern. Devobs uses Python to match its standard-library unit-test suite and expands the check to the exact ruleset that currently protects the default branch. The reference repository's branch-protection writer is not reused because a full settings update can erase unspecified existing requirements.
