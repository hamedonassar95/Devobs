---
phase: testing
title: Offline scorecard coverage and denominator tests
description: Check coverage, unknown-output, and selective accuracy counts for abstaining and non-abstaining cases
---

# Testing

## Coverage

- Existing five-case fixture reports coverage and unknown-output rates with explicit counts over all cases.
- Selective accuracy retains its existing scalar output and reports numerator/denominator counts separately.
- A fixture whose every prediction is `unknown` reports zero coverage, a 100% unknown-output rate, and undefined selective accuracy with denominator zero.
- These tests describe the deterministic synthetic evaluator; they do not measure safe refusal or model behavior.

## Test-first evidence

The new assertions initially failed because the scorecard had no `coverage` field. They passed after implementation.

## Verification results

- Focused evaluator suite: 16 tests passed.
- Milestone ledger suite: 38 tests passed and the summary reports latest PR #407, 83 merged milestones, and 3 unchanged gates.
- Full Python suite: 804 tests passed, 22 skipped, using the existing temporary validation environment with `psycopg` installed.
- `compileall`, Bandit for the changed evaluator, action-pin check, evaluator CLI, and `git diff --check`: passed.
- Hosted checks: not run; this local branch has not been pushed.
