---
phase: implementation
title: Offline scorecard extension
description: Add category metrics and a nominal Wilson interval to the offline evaluator
---

# Implementation

## Intended change

- Add per-category one-vs-rest confusion counts and precision/recall with explicit denominators.
- Add a descriptive nominal 95% Wilson interval for overall accuracy.
- Preserve existing aggregate metrics and optional explicit-target behavior.
- Keep identifiers and signal values out of the report and explain statistical limitations.

## Lifecycle progress

- [x] Requirements checked against the P00–P12 roadmap.
- [x] Existing evaluator searched for duplicate metrics before change.
- [x] Test-first assertions added and confirmed red before implementation.
- [x] Scorecard implementation and documentation completed.
- [x] Full local tests, compile check, security scan, and ledger validation passed.
- [ ] Hosted feature-branch CI and final owner review remain.

## Limits

This remains a deterministic evaluation of five synthetic cases. No real model call, safe-refusal metric, approved incident corpus, latency/cost measurement, or P04 exit evidence is established.

## Verification

- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -q` — 10 passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -q` — 797 passed, 22 skipped.
- `/tmp/devobs-p01-ac02-validation/bin/python -m compileall -q scripts tests` — passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m bandit -r scripts -x scripts/check_site.py` — no findings across 9,113 lines.
- `/tmp/devobs-p01-ac02-validation/bin/python scripts/milestone_ledger.py --summary` — latest merged PR #405; 81 milestones; 3 gate records unchanged.
- `git diff --check` — passed.

Hosted feature-branch checks will be recorded when available. The implementation does not claim P04 exit acceptance.
