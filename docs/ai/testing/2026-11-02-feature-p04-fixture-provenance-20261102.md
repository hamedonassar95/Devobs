---
phase: testing
title: Adviser fixture provenance tests
description: Verify hash binding, strict policy, and bounded report output
---

# Testing

## Coverage

- Canonical runner returns fixture ID/version/SHA-256 and synthetic-only metadata.
- Changed fixture bytes fail with a digest mismatch.
- Policy attempting to mark the fixture production eligible fails closed.
- Duplicate JSON keys fail closed even when the manifest digest is changed to match.
- Report output omits raw case IDs, labels, and signals while retaining the scorecard.
- Existing in-memory evaluator and explicit-target behavior remain covered.

## Test-first evidence

The new tests initially failed to import `evaluate_fixture`, which did not exist. They passed after adding the manifest-bound runner.

## Verification results

- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -q` — 14 passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_ai_eval_fixture_guard.py' -q` — 6 passed; the existing separate dataset validator remains intact.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_milestone_ledger.py' -q` — 37 passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -q` — 801 passed, 22 skipped.
- `/tmp/devobs-p01-ac02-validation/bin/python -m compileall -q scripts tests` — passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m bandit -r scripts -x scripts/check_site.py` — no issues across 9,210 lines.
- `/tmp/devobs-p01-ac02-validation/bin/python scripts/milestone_ledger.py --summary` — latest PR #406, 82 merged milestones, 3 unchanged gate records.
- `PYTHONPATH=scripts /tmp/devobs-p01-ac02-validation/bin/python -m devobs_intelligence.evaluation` — passed; report identifies dataset `devobs-adviser-synthetic` v1 with SHA-256 `0a9c73c281834de399952222ac28ff1580cd5fcbb61b760a4f0557109b00b0ad` and no raw rows.
- `git diff --check` — passed.
- Hosted checks are reported by [PR #407](https://github.com/hamedonassar95/Devobs/pull/407) on its exact current head. Re-check after each commit; an earlier green run does not validate a later SHA.

All input data is the checked-in synthetic fixture. Passing tests show hash/schema behavior only; they do not establish independent labels or model quality.
