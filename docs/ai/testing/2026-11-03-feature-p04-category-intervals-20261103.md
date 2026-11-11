---
phase: testing
title: Per-category precision and recall interval tests
description: Verify descriptive Wilson interval denominators and undefined intervals for empty classes
---

# Testing

## Coverage

- Per-category precision intervals use true positives over predicted positives.
- Per-category recall intervals use true positives over actual support.
- Interval records preserve successes and trials and contain the point estimate when the denominator is positive.
- Empty precision/recall denominators produce a `null` interval rather than an invented bound.

## Test-first evidence

The new assertions initially failed because per-category interval fields were absent. They passed after implementation.

## Verification results

- Focused evaluator suite: 16 tests passed.
- Milestone ledger suite: 39 tests passed; latest recorded merge is PR #408.
- Full Python suite: 805 tests passed, 22 skipped.
- `compileall`, Bandit on the changed evaluator, action-pin check, evaluator CLI and `git diff --check`: passed.
- Hosted checks: not run; this branch has not been pushed.
