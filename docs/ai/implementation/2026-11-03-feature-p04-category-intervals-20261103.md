---
phase: implementation
title: Per-category descriptive Wilson intervals
description: Show interval bounds for per-category precision and recall in the offline scorecard
---

# Implementation

## Intended change

- Add nominal 95% Wilson intervals for per-category precision and recall using the existing scorecard counts.
- Preserve interval successes/trials so each bound has an explicit denominator.
- Return `null` for an interval when that metric has a zero denominator.
- Record PR #408 merge evidence without changing roadmap or readiness decisions.

## Lifecycle progress

- [x] Checked P04 requirements and confirmed the scorecard already records class supports and predicted counts.
- [x] Added failing tests before implementation.
- [x] Reused the existing Wilson calculation and preserved scalar precision/recall values.
- [x] Full local verification completed and final diff reviewed.

## Limits

These intervals summarize counts from five deterministic synthetic cases. They are descriptive, not calibrated model confidence or reliable population estimates. No real labels or model calls are used.

## Verification

- `/tmp/devobs-p04-category-validation-20261103/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -v` — 16 tests passed.
- `/tmp/devobs-p04-category-validation-20261103/bin/python -m unittest discover -s tests -p 'test_milestone_ledger.py' -v` — 39 tests passed.
- `/tmp/devobs-p04-category-validation-20261103/bin/python -m unittest discover -s tests -v` — 805 tests passed, 22 skipped.
- `/tmp/devobs-p04-category-validation-20261103/bin/python -m compileall -q scripts tests` — passed.
- `/tmp/devobs-p04-category-validation-20261103/bin/python -m bandit -r scripts/devobs_intelligence/evaluation.py` — no issues across 259 lines.
- `python3 scripts/check_action_pins.py` — passed for 40 workflow and template files.
- `/tmp/devobs-p04-category-validation-20261103/bin/python scripts/milestone_ledger.py --summary` — latest PR #408, 84 merged milestones, 3 open gates.
- `PYTHONPATH=scripts /tmp/devobs-p04-category-validation-20261103/bin/python -m devobs_intelligence.evaluation` — passed; per-category precision and recall intervals include successes/trials.
- `git diff --check` — passed.
- The runner image lacked `psycopg` and PyYAML; the full suite passed in an isolated temporary environment installed from the hash-locked API and dev requirements. Hosted checks were not run because this branch remains local.
