---
phase: requirements
title: Offline evaluation slice metrics and interval
description: Add interpretable per-category counts and a descriptive interval without inventing acceptance targets
---

# Requirements

## Problem

The P04 offline evaluator reports aggregate accuracy only. It does not show which fixed category contributes false positives or false negatives, and it does not report an interval around the observed accuracy.

## Goals

- Report one-vs-rest confusion counts, precision, and recall for every fixed category.
- Include each metric's numerator and denominator; return `null` for undefined precision or recall while preserving a zero denominator.
- Report a nominal 95% Wilson score interval for the observed correct/incorrect proportion.
- Keep the report bounded and free of raw case IDs and signal values.
- State the limits of applying these descriptive statistics to five synthetic examples.

## Non-goals

- Adding or approving an accuracy target, changing the fixtures or adviser, or changing AI-9/P01/Codex runtime gate states.
- Claiming safe-refusal rate, calibrated model confidence, representative data, real-world quality, latency, or inference cost.
- Calling a model/provider, accessing external data, or using cloud resources.

## Acceptance criteria

1. The scorecard returns per-category TP/FP/TN/FN, support, predicted count, precision, and recall.
2. Precision and recall expose numerator and denominator; a zero denominator yields a `null` value.
3. Overall accuracy includes a deterministic Wilson score interval with its method, nominal level, successes, and trials.
4. Tests prove the interval and slice metrics on known fixture outcomes and prove raw IDs/signals remain absent.
5. Documentation says the interval and category metrics are descriptive for the small synthetic set and do not satisfy P04's approved-data or model-quality gate.

## Constraints

Use only the existing offline deterministic adviser and synthetic fixtures. Preserve all prior aggregate fields and optional explicit-target behavior. No inference, secrets, migration, deployment, or cloud spend.
