---
phase: planning
title: Explicit evaluation target implementation plan
description: Test-first change to remove the implicit accuracy cutoff
---

# Plan

## Milestones

- [x] M1: Regression test demonstrates the implicit 0.85 target.
- [x] M2: Evaluator uses an optional target and preserves explicit comparisons.
- [x] M3: Roadmap-aligned documentation, merged evidence, full checks, and review are complete.

## Tasks

- [x] 1. Add a test requiring `null` target fields on an evaluation without an explicit target; confirm it fails against current behavior.
- [x] 2. Update target validation and output while preserving the existing report keys.
- [x] 3. Add explicit permissive/strict target comparisons and invalid-target coverage.
- [x] 4. Update evaluator docs and record PR #404 merge evidence without changing any gate state.
- [x] 5. Run focused/full tests, compileall, security checks, feature lint, ledger validation, and final review.

## Risks

- A report consumer might assume `meets_target` is always Boolean. Retaining its key but returning `null` in the absence of a target makes that state explicit; check current repository callers and document the semantic correction.
- A caller-supplied threshold is not necessarily approved. Documentation must make that limitation explicit; no target is described as approved by this change.
- Synthetic metrics remain illustrative and cannot establish model quality.

## Boundaries

Local/offline only. No model API, external data, cloud resource, deployment, secrets, or migration.

## Progress

All tasks are complete. The regression assertion failed against the previous 0.85 default, then passed with the optional target implementation. PR #404 merge evidence is recorded with the existing gate states unchanged. The full suite passed 793 tests with 22 skips; compileall, Bandit, feature lint, ledger validation, and `git diff --check` passed.
