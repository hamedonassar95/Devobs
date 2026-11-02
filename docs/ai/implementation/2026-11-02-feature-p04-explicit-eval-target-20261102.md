---
phase: implementation
title: Explicit evaluation target implementation
description: Implementation and verification record for optional scorecard targets
---

# Implementation

## Lifecycle progress

- [x] Phase 2: requirements reviewed against the P04 roadmap.
- [x] Phase 3: minimal optional-target design recorded.
- [x] Phase 4: test-first plan recorded.
- [x] Phase 7: implementation reviewed against design.
- [x] Phase 8: full tests and checks recorded.
- [x] Phase 9: final code review complete.

## Intended change

- Make `target_accuracy` optional with no default threshold.
- Preserve strict range/type checks for explicit values.
- Emit `null` for both target fields when no target is supplied.
- Keep all other metrics and report keys unchanged.

## Limits

This is a deterministic, synthetic evaluation utility. No model call, live incident corpus, or owner-approved acceptance target is established.

## Verification

- Red phase: the new target-free assertion failed because the previous default emitted `0.85`.
- `python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -q` — 6 passed.
- `python -m unittest discover -s tests -p 'test_milestone_ledger.py' -q` — 37 passed.
- `python -m unittest discover -s tests -q` — 793 passed, 22 skipped.
- `python -m compileall -q scripts/devobs_intelligence` — passed.
- `python -m bandit -r scripts -x scripts/check_site.py` — no issues identified across 9,059 lines.
- `npx --yes ai-devkit@latest lint --feature p04-explicit-eval-target-20261102` — 16 checks passed.
- `python3 scripts/milestone_ledger.py --summary` — latest PR #404, 80 merged milestones, 3 open gates; gate values unchanged.
- `git diff --check` — passed. Repository search found no other consumers of the target fields.
