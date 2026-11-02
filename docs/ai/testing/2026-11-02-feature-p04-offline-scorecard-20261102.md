---
phase: testing
title: Offline scorecard tests
description: Verify category denominators, Wilson interval, and privacy on synthetic cases
---

# Testing

## Coverage

- Wilson interval method, nominal confidence level, numerator, denominator, and bounds on the five-case fixture.
- One-vs-rest counts and precision/recall for categories with true positives, false positives, and false negatives.
- `null` precision/recall with an explicit zero denominator when a category is absent.
- No raw case IDs or signal fields in the report.
- Existing target, invalid input, abstention, and aggregate behavior remains covered.

## Test-first evidence

The new scorecard assertions initially failed because `accuracy_interval_95` and `per_category` were absent. The focused suite passed after implementing those fields.

## Verification results

- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -q` — 10 passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_milestone_ledger.py' -q` — 37 passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -q` — 797 passed, 22 skipped.
- `/tmp/devobs-p01-ac02-validation/bin/python -m compileall -q scripts tests` — passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m bandit -r scripts -x scripts/check_site.py` — no issues across 9,113 lines.
- `/tmp/devobs-p01-ac02-validation/bin/python scripts/milestone_ledger.py --summary` — latest PR #405, 81 merged milestones, 3 open gates; gate values unchanged.
- `git diff --check` — passed.
- Hosted checks on this feature branch — not run yet.
- Hosted checks on this feature branch — not run yet.

The cases are synthetic and five in number. These tests verify deterministic arithmetic and report boundaries only; they do not establish live model inference or real-world quality.
