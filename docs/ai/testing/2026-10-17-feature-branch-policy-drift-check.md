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
- A null or empty bypass-actor list passes as no configured bypass; missing and wrongly typed fields are inconclusive errors.
- Missing ruleset is reported without trying to fetch detail.
- Invalid owner/name input is rejected.

The API client uses an injected fixture in unit tests, so tests are deterministic and make no network calls. The project CI also compiles Python sources, runs the unittest suite, checks action SHA pins, and runs Bandit.

## Live verification

The first hosted run (run [39041619309](https://github.com/hamedonassar95/Devobs/actions/runs/39041619309)) exposed that the runner received `bypass_actors: null` for an empty list. The follow-up run on current `main` ([39043609586](https://github.com/hamedonassar95/Devobs/actions/runs/39043609586)) reproduced it. The local public API returned `[]` during diagnosis, so the test now covers both valid empty representations and invalid/missing data. After this fix merges, use Actions → Repository policy audit → Run workflow and confirm a passing hosted run. Subsequent runs are scheduled weekly. Local fixture tests and a local API check do not replace the post-merge hosted check.

## Failure-mode review

If an expected control is removed, disabled, excluded from the default branch, or weakened, the command exits 1 and names the missing rule. If the API is unavailable, rate-limited, or returns an invalid payload, it exits 2. Neither case is treated as success. No integration test mutates GitHub settings; restoring settings remains a reviewed human operation.
