---
phase: testing
title: Optional evaluation target tests
description: Offline tests proving target-free reporting and explicit comparison
---

# Testing

## Coverage

- Default evaluation reports metrics and `null` for target and target decision.
- Explicit permissive and stricter targets produce truthful comparisons.
- Boolean, NaN, and out-of-range target values are rejected.
- Summary remains free of raw case IDs and signal data.

## Test-first evidence

The new default-target assertion failed before implementation because the evaluator emitted `0.85`. After the implementation change, all 6 tests in `test_intelligence_evaluation.py` passed.

## Verification results

- `python -m unittest discover -s tests -q` — 793 passed, 22 skipped.
- `python -m compileall -q scripts/devobs_intelligence` — passed.
- `python -m bandit -r scripts -x scripts/check_site.py` — no issues identified.
- AI DevKit feature lint — 16 checks passed.
- `python3 scripts/milestone_ledger.py --summary` — passed; latest PR #404, 80 merged milestones, 3 open gates.
- `git diff --check` — passed.

Tests are synthetic and offline; they do not establish model performance or target approval.
