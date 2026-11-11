---
phase: planning
title: Offline evaluation scorecard extension
description: Test-first implementation plan for category metrics and Wilson interval
---

# Plan

## Milestones

- [x] M1: Add failing tests for interval, category metrics, denominator behavior, and report privacy.
- [x] M2: Implement deterministic calculations without introducing thresholds or external calls.
- [x] M3: Document synthetic-data limits and synchronize evidence for merged PR #405.
- [x] M4: Run focused and full local verification, inspect final diff, and prepare a review PR.

## Tasks

1. Confirm the evaluator has no existing per-category or confidence-interval implementation.
2. Add test-first assertions using the existing five-case fixture.
3. Add one-vs-rest confusion counts, precision/recall denominators, and a Wilson interval.
4. Update evaluator documentation and P04 implementation records; record only verified PR #405 merge evidence in the main readiness snapshot and ledger.
5. Run relevant tests/security checks and review the resulting diff; leave merge to the owner.

## Progress

The evaluator search found no existing category scorecard or confidence interval. Test-first assertions failed on the absent report fields, then passed after the implementation. Local verification passed 796 tests with 22 expected skips; the exact results are in the testing record.

## Risks

- A nominal interval on five fixed synthetic examples can be mistaken for a calibrated model confidence or population estimate. The report and documentation must label its limitations.
- Per-category rates are unstable on small or absent categories; zero denominators must produce `null`, never zero or a pass result.
- The `unknown` class and abstention count do not establish safe refusal.

## Boundaries

Local/offline and reviewable. Do not add targets, change gate status, invoke AI inference, read secrets, provision resources, migrate, or deploy.
