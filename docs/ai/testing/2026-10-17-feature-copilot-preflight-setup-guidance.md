---
phase: testing
title: Copilot preflight remediation
description: Regression tests for safe and actionable credential guidance
---

# Testing

## Scenarios

- [x] The test fails before workflow wiring because the preflight does not invoke the separately testable checker.
- [x] A missing secret fails with the exact secret name, account permission, repository settings link, and no-model-call statement.
- [x] An unsupported token prefix fails and neither the summary nor test output includes the supplied token fixture.
- [x] An accepted prefix passes format validation while stating that provider permission and inference were not checked and reminding the maintainer to keep the policy-audit token separate.
- [x] The workflow passes the secret only as an environment variable and uses a 40-character pinned checkout action.
- [x] The command writes the remediation to `GITHUB_STEP_SUMMARY` and exits nonzero for an unsupported token.

## Commands and results

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ai_provider_preflight -v` — 7 passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` — 169 passed.
- `node --test tests/incident_guard.test.cjs` — 22 passed.
- `python3 scripts/check_action_pins.py` — 31 workflow/template files passed.
- `python3 scripts/check_site.py` — page contract and HTTP smoke checks passed.
- `python3 -m bandit -r scripts -x scripts/check_site.py` — no findings.
- `npx ai-devkit@latest lint --feature copilot-preflight-setup-guidance` — 16 checks passed.

The preflight test suite is fully local and makes no API or model request. Hosted provider activation is deliberately not included in this test suite.

## Limits

Unit tests prove summary behavior and secret non-disclosure for test fixtures; they cannot prove GitHub account token permissions. The next manual preflight checks only presence and prefix. An actual investigator evaluation requires owner-managed credentials and can consume AI quota, so it remains a separate operational decision.
