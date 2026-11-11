---
phase: implementation
title: Offline scorecard coverage denominators
description: Report bounded fixture coverage and unknown-output rates with explicit denominators
---

# Implementation

## Intended change

- Add coverage and unknown-output rates to the existing deterministic adviser scorecard with explicit numerators and denominators.
- Preserve the existing `selective_accuracy` number and add its numerator and denominator as a sibling field for compatibility.
- Keep `unknown` semantically distinct from safe refusal; retain the synthetic-only, non-production scope.
- Record PR #408 merge evidence while leaving roadmap and gate dispositions unchanged.

## Lifecycle progress

- [x] Requirements checked against P04; source fixture remains synthetic and unreviewed.
- [x] Tests added first and confirmed failing before implementation.
- [x] Scorecard fields implemented without changing existing scalar fields.
- [x] Full local verification completed; final diff reviewed.
- [x] Owner merged PR #408; merge evidence is recorded in the next local development change.

## Limits

These rates describe only the five checked-in synthetic cases. `unknown_output_rate` is not a safe-refusal measurement, and the work does not establish representative labels, model quality, model inference, latency, per-request cost, or P04 exit acceptance.

## Verification

- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -v` — 16 tests passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_milestone_ledger.py' -v` — 38 tests passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -v` — 804 tests passed, 22 skipped.
- `/tmp/devobs-p01-ac02-validation/bin/python -m compileall -q scripts tests` — passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m bandit -r scripts/devobs_intelligence/evaluation.py` — no issues across 244 lines.
- `python3 scripts/check_action_pins.py` — passed for 40 workflow/template files.
- `/tmp/devobs-p01-ac02-validation/bin/python scripts/milestone_ledger.py --summary` — latest PR #407, 83 merged milestones, 3 unchanged gates.
- `PYTHONPATH=scripts /tmp/devobs-p01-ac02-validation/bin/python -m devobs_intelligence.evaluation` — passed; fixture reports coverage 4/5 and unknown-output rate 1/5, with no raw rows.
- `git diff --check` — passed.
- The default system Python lacks `psycopg`; the full suite passed using the existing temporary validation environment. PR #408's exact-head CI and CodeQL passed; its advisory inference step was skipped. The post-merge CI and CodeQL runs passed on merge SHA `8d4c1875aafb321f4b6a874ac748e6cae471f0eb`.
