---
phase: design
title: P04 metadata-only evaluation split leakage guard
description: Prevent related incident cases from crossing development, calibration, and holdout splits
---

# Design

## Goal

Provide a small local contract for checking that cases linked to the same incident remain in one evaluation split. This is preparatory support for P04's review-split requirement; it does not provide an incident dataset or complete T28/T29.

## Contract

- Accept only a bounded list of metadata records with four exact fields: an opaque case token, an opaque incident-group token, a split name, and a category slug.
- Recognize `development`, `calibration`, and `holdout` splits. Set no proportions, minimum per-class counts, or quality thresholds.
- Reject duplicate case tokens and any incident-group token assigned to more than one split.
- Return case, group, and class counts only; never return tokens or source content.
- Reject extra fields so raw incident payloads cannot enter this contract.

## Trust and privacy limits

Tokens must be random, opaque identifiers assigned by an authorized data curator; the format check cannot prove randomness or anonymization. This function does not establish consent, label provenance, label correctness, representativeness, or independence. No real incident data is included or read. A future benchmark still needs the approvals and at least 30 reviewed human-labeled cases required by the roadmap.
