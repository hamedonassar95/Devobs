---
phase: testing
title: Evidence-labeled abstention metric tests
description: Verify labeled denominators, missed abstentions, empty slices, and fail-closed labels
---

# Testing

## Coverage

- Only cases labeled `insufficient` contribute to the new abstention rate.
- A sufficient-evidence case that returns `unknown` does not inflate the metric.
- An insufficient-evidence case that returns a category counts as a missed abstention.
- Empty and invalid labels fail closed; zero denominators return `null`, not zero.
- Versioned fixture digest, report privacy, and synthetic-only manifest checks remain in force.

## Test-first evidence

The two new metric tests initially failed because the evaluator rejected the added label with `EvaluationError("invalid_case")`. They passed after implementing the v2 contract and scorecard field.

## Verification results

- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -v` — 21 tests passed.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_milestone_ledger.py' -v` — 40 tests passed.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests` — 811 tests passed, 22 skipped.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m compileall -q scripts tests` — passed.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m bandit -r scripts/devobs_intelligence/evaluation.py` — no issues across 284 lines.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_intelligence_bom.py' -v` — 2 tests passed.
- `PYTHONPATH=scripts /tmp/devobs-p04-refusal-validation-20261103/bin/python -m devobs_intelligence.evaluation` — passed; reports dataset v2 digest `6ae90bdb0d5091d580d61b4f9b0356a4e6bb6c8bcdf408ca0e92deeb059afe23`, with 1/1 insufficient-evidence abstentions and zero live model calls.
- `git diff --check` and the v2 fixture SHA-256 check — passed.
- The environment lacked `psycopg`; the full suite passed in a temporary environment installed from the hash-locked API and dev requirements. No repository dependency files changed.
- Hosted CI and CodeQL evidence for the change is reported on its PR; no deployment or model inference was run locally.
