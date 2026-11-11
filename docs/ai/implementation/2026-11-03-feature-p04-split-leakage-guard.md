---
phase: implementation
title: P04 evaluation split leakage guard
description: Validate opaque incident-group assignments and emit aggregate split counts
---

# Implementation

## Behavior

- `scripts/devobs_intelligence/evaluation_splits.py` validates metadata-only case assignments for development, calibration, and holdout splits.
- Duplicate case tokens, invalid split/category values, unexpected fields, malformed tokens, and cross-split incident groups fail closed with fixed diagnostics.
- The result reports aggregate case/group/category counts only. The contract does not open files, inspect incident content, call a model, or establish consent or anonymization.

## Lifecycle progress

- [x] Checked P04 T28/T29 and confirmed no split-leakage contract existed in the evaluator package.
- [x] Added the focused tests first; they failed with `ModuleNotFoundError` before implementation.
- [x] Implemented the bounded metadata contract and aggregate-only summary.
- [x] Recorded merged PR #411 evidence without changing any readiness gate.
- [x] Ran focused and full local verification: 7 new tests and 822 repository tests passed; 22 repository tests skipped by their existing conditions.
- [x] Validated the milestone ledger: 87 merged milestones and 3 unchanged open gates; compiled `scripts/` and `tests/` and passed `git diff --check`.

## Limits

The contract is only a split-assignment check. It cannot validate token generation, anonymization, consent, human review, labels, representativeness, or evaluator quality. The repository still has no approved human-labeled incident dataset. The addition is partial development evidence; it does not complete T28 or T29.

## Design and tests

- [Design](../design/2026-11-03-feature-p04-split-leakage-guard.md)
- [Testing](../testing/2026-11-03-feature-p04-split-leakage-guard.md)
