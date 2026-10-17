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

## Follow-up verification — 17 October 2026

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` — 162 tests passed.
- `python3 scripts/check_action_pins.py` — passed for 31 workflow and template files.
- `npx --yes ai-devkit@latest lint --feature branch-policy-drift-check` — all 16 checks passed.
- `git diff --check` and the local Markdown-link check passed.

## Live verification

The hosted runs [39041619309](https://github.com/hamedonassar95/Devobs/actions/runs/39041619309) and [39043609586](https://github.com/hamedonassar95/Devobs/actions/runs/39043609586) exposed the valid `bypass_actors: null` representation; PR #167 added regression coverage and support for both `null` and `[]`. After PR #169 added optional `POLICY_AUDIT_TOKEN` authentication, manual run [39048544142](https://github.com/hamedonassar95/Devobs/actions/runs/39048544142) still failed inconclusively because the response omitted `bypass_actors`. Set the repository secret to a fine-grained token with `Administration: read`, then run **Actions → Repository policy audit → Run workflow** on `main`. The first passing hosted run remains outstanding; local fixture tests do not replace it.

## Failure-mode review

If an expected control is removed, disabled, excluded from the default branch, or weakened, the command exits 1 and names the missing rule. If the API is unavailable, rate-limited, or returns an invalid payload, it exits 2. Neither case is treated as success. No integration test mutates GitHub settings; restoring settings remains a reviewed human operation.
