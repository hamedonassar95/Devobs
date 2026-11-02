---
phase: implementation
title: Adviser fixture provenance runner
description: Bind the offline P04 scorecard to an exact synthetic fixture revision
---

# Implementation

## Intended change

- Add the fixed synthetic-only fixture manifest and SHA-256.
- Add a fail-closed runner/CLI that checks policy, byte/case limits, JSON uniqueness, and digest before scoring.
- Add dataset identity to the report without returning raw cases.
- Record PR #406 post-merge evidence while leaving gate records unchanged.

## Lifecycle progress

- [x] Requirements checked against the P04 roadmap and existing dataset tooling.
- [x] Existing manifest audited; confirmed it describes a different dataset.
- [x] Tests added first and confirmed failing before implementation.
- [x] Manifest-bound runner, report metadata, and CLI implemented.
- [x] Full local suite, focused tests, security scan, and ledger validation passed.
- [x] Hosted feature-branch checks completed on the then-current PR head; the current head must be rechecked after any commit.
- [ ] Final owner review remains.

## Limits

The manifest labels are synthetic and unreviewed. This does not satisfy real-data provenance, independently reviewed labels, model inference, or P04 release acceptance.

## Verification

- Full suite: 801 passed, 22 skipped; focused evaluator: 14 passed; existing fixture guard: 6 passed; ledger tests: 37 passed.
- `compileall`, Bandit (9,210 lines, no findings), ledger summary (latest PR #406; 82 milestones; 3 gates unchanged), module CLI, and `git diff --check` passed.
- The current exact-head CI and CodeQL disposition is attached to [PR #407](https://github.com/hamedonassar95/Devobs/pull/407); verify again after any commit because hosted results are SHA-specific.
