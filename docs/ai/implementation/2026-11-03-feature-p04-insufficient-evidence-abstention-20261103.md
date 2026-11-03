---
phase: implementation
title: Evidence-labeled abstention metric for the offline scorecard
description: Score unknown outputs only against explicitly labeled synthetic insufficient-evidence cases
---

# Implementation

## Intended behavior

- Add `evidence_sufficiency` labels to a new v2 synthetic fixture and preserve the original v1 fixture and manifest.
- Report `insufficient_evidence_abstention_rate` with its numerator, denominator, and descriptive Wilson interval. A zero denominator yields `null` values.
- Keep the metric distinct from a general safe-refusal rate; do not infer safety or model quality from five synthetic examples.
- Record verified PR #409 merge evidence without changing readiness decisions.

## Lifecycle progress

- [x] Checked P04 requirements and confirmed the existing unknown-output rate had no explicit evidence-sufficiency denominator.
- [x] Added behavioral tests before implementation; the focused suite first failed because the evaluator rejected the new evidence label as `invalid_case`.
- [x] Implemented the strict v2 case contract and descriptive metric while retaining v1 artifacts.
- [x] Ran focused and full local verification and reviewed the final diff.

## Limits

The v2 labels are synthetic and unreviewed. The result is not a general safe-refusal measure, independent evidence, calibrated model confidence, or real-world quality. No model provider is called.

## Verification

See [the testing report](../testing/2026-11-03-feature-p04-insufficient-evidence-abstention-20261103.md) for commands and results.
