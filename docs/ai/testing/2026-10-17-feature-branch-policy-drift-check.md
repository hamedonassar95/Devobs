---
phase: testing
title: Default-Branch Policy Drift Audit
description: Unit and operational verification for repository governance auditing
---

# Default-Branch Policy Drift Audit — Testing

## Automated tests

Run the focused suite:

    python3 -m unittest discover -s tests -p 'test_check_repo_policy.py' -v

Coverage includes:

- Current baseline passes with no findings.
- Unprotected default branch and absent validate status check are reported.
- Disabled ruleset and configured bypass actor are reported.
- Missing ruleset is reported without trying to fetch detail.
- Invalid owner/name input is rejected.

The API client uses an injected fixture in unit tests, so tests are deterministic and make no network calls. The project CI also compiles Python sources, runs the unittest suite, checks action SHA pins, and runs Bandit.

## Live verification

The first hosted run is an operational check that the public GitHub API still exposes these ruleset endpoints to the runner. After merge, use Actions → Repository policy audit → Run workflow, then confirm a passing run. Subsequent runs are scheduled weekly. A successful local fixture test does not replace this live API check.

## Failure-mode review

If an expected control is removed, disabled, excluded from the default branch, or weakened, the command exits 1 and names the missing rule. If the API is unavailable, rate-limited, or returns an invalid payload, it exits 2. Neither case is treated as success. No integration test mutates GitHub settings; restoring settings remains a reviewed human operation.
