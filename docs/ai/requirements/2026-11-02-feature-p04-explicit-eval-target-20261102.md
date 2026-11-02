---
phase: requirements
title: Explicit evaluation acceptance target
description: Prevent the offline evaluator from implying an unapproved accuracy threshold
---

# Requirements

## Problem

`evaluate_cases(...)` currently defaults to an accuracy target of 0.85 and emits `meets_target` even when no owner-approved acceptance target was supplied. The P00–P12 roadmap says targets must be approved and measured, not invented in advance.

## Goals

- Report deterministic synthetic metrics without assigning a default pass/fail threshold.
- Compare against a target only when the caller explicitly provides a finite numeric value from 0 through 1.
- Return `null` for `target_accuracy` and `meets_target` when no comparison target was supplied.
- Preserve the current explicit-target comparison and all non-target metrics.
- State that an explicit function argument is not proof of owner approval or real-world model quality.

## Non-goals

- Changing the synthetic cases, adviser, AI-9 detector, model calls, production thresholds, or gate status.
- Claiming owner approval, dataset representativeness, statistical confidence, or model calibration.
- Adding network access, cloud resources, deployment, or live inference.

## Acceptance criteria

1. A default evaluation reports its current case count, accuracy, abstentions, and selective accuracy while setting `target_accuracy` and `meets_target` to `null`.
2. An explicitly supplied target is range/type checked and compared truthfully.
3. Boolean, non-finite, and out-of-range targets fail closed.
4. Existing report keys remain stable and the summary continues to omit case identifiers and raw signals.
5. Documentation states that target approval is external to the evaluator and that this synthetic run is not an AI quality claim.

## Constraints

Use only the existing deterministic adviser and synthetic fixtures. No provider, token, network, customer incident, or cloud service is involved.
