---
phase: implementation
title: Compare abstention rates across evidence-sufficiency labels
description: Add the complementary descriptive rate for unknown outputs on cases labeled sufficient
---

# Implementation

## Intended behavior

- Report `sufficient_evidence_abstention_rate` beside the existing insufficient-evidence rate.
- Count only cases with the matching explicit synthetic evidence-sufficiency label; include numerator, denominator, and descriptive Wilson interval.
- Return `null` and a zero denominator when a label slice is empty; keep strict case validation.
- Version the scorecard output as schema 3 and document that neither rate is a general safe-refusal metric.
- Record merged PR #410 in the milestone ledger, `STATE.md`, and the current readiness snapshot without changing gate dispositions.

## Lifecycle progress

- [x] Compared the existing P04 metrics and confirmed the earlier scorecard measured abstention only on insufficient-evidence labels.
- [x] Added tests first; the focused suite failed before implementation because the new report field was missing.
- [x] Added the sufficient-label numerator, denominator, interval, empty-slice handling, and schema-version change.
- [x] Updated metric scope documentation and recorded verified PR #410 merge evidence.
- [x] Ran focused and full local verification; no model/provider or hosted API was used.

## Limits

The five evidence-sufficiency labels remain synthetic and unreviewed. This metric is not independent evidence, label validation, a general safe-refusal measure, calibrated model confidence, or real-world quality. No AI model call, external service, migration, deployment, or paid resource was used. AI-9, P01, and Codex runtime dispositions did not change.

## Verification

See [the testing report](../testing/2026-11-03-feature-p04-abstention-tradeoff-20261103.md) for commands and results.
