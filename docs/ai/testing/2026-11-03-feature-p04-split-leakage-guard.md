---
phase: testing
title: P04 evaluation split leakage tests
description: Check disjoint incident groups, strict metadata shape, and aggregate-only output
---

# Testing

## Coverage

- Repeated cases from one incident may share a split; the same incident group cannot appear in different splits.
- Duplicate case tokens and malformed group tokens are rejected.
- Failure diagnostics do not disclose incident-group tokens.
- Split and category values are validated; unexpected fields are rejected.
- Summary contains counts only and omits case and incident-group tokens.
- Empty and oversized assignments fail closed.

## Test-first evidence

Before implementation, the focused suite failed to import the not-yet-created `evaluation_splits` module. After adding the contract, all seven focused tests passed.

## Verification results

- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation_splits.py' -v` — 7 tests passed, including the diagnostic-redaction assertion.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_milestone_ledger.py' -v` — 42 tests passed.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests` — 822 tests passed, 22 skipped, 0 failures. Output from tests exercising readiness gates included expected `BLOCKED` diagnostics; the test process completed successfully.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python scripts/milestone_ledger.py --summary` — valid ledger, 87 merged milestones, 3 open gates (`AI-9` and `P01` blocked; Codex runtime open).
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m compileall -q scripts tests` — passed.
- `git diff --check` — passed.
- Bandit was not run because it is not installed in this environment.

All test rows contain synthetic metadata only. No incident source, live service, model provider, network, or paid resource was used.
