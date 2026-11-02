---
phase: requirements
title: Bind the adviser scorecard to a versioned fixture
description: Report exact synthetic fixture identity and reject provenance drift before scoring
---

# Requirements

## Problem

The P04 scorecard evaluates a five-case synthetic adviser fixture, but its report does not identify the exact file bytes. The repository's existing fixture policy covers a different Decisions triage JSONL dataset and cannot identify this fixture.

## Goals

- Add a versioned manifest for the canonical adviser evaluation fixture.
- Validate the manifest's fixed offline/synthetic scope, category set, count/size bounds, and dataset SHA-256 before scoring.
- Provide a local runner that includes dataset ID, version, digest, label status, and synthetic-only disposition in the bounded report.
- Reject duplicate JSON keys, hash drift, invalid policy, missing files, and oversized fixture content with fixed diagnostics.
- Keep raw case IDs and signal values out of the report.

## Non-goals

- Modifying cases or labels, evaluating a model, introducing a default threshold, or claiming real-world quality.
- Reusing the unrelated Decisions triage manifest as if it described this adviser fixture.
- Adding network/cloud access, workflow jobs, paid inference, migrations, secrets, deployment, or gate changes.

## Acceptance criteria

1. The runner validates the exact fixture file against a versioned SHA-256 manifest and returns dataset provenance metadata.
2. Digest drift, malformed/duplicate JSON keys, invalid source policy, and count mismatch fail closed.
3. The report includes aggregate and per-category scorecard metrics but no raw IDs or signal values.
4. Tests show the runner is deterministic and offline; documentation gives the exact command and states all evidence limits.

## Constraints

Use only the checked-in five-case synthetic fixture. Dataset labels stay `synthetic_unreviewed`; the manifest must explicitly keep `production_gate` false.
