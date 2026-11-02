---
phase: planning
title: Adviser evaluation fixture provenance
description: Test-first plan to bind offline scorecards to the exact fixture version
---

# Plan

## Milestones

- [x] M1: Confirm the existing Decisions triage manifest is for a different dataset and the adviser fixture has no manifest binding.
- [x] M2: Add failing tests for runner output, digest drift, policy scope and duplicate JSON keys.
- [x] M3: Add the strict synthetic-only manifest and fixture runner.
- [x] M4: Document PR #406 merge evidence, run final checks, review diff, and prepare a review PR.

## Tasks

1. Bind `tests/fixtures/intelligence_eval_cases.json` to a stable dataset ID, version, label status, categories, and SHA-256.
2. Add `evaluate_fixture()` to validate the exact manifest/data paths and then use the existing `evaluate_cases()` implementation.
3. Attach only dataset metadata to the report; keep rows and signal values private to the process.
4. Add a module CLI for reproducible local output and document use/limits.
5. Record verified PR #406 merge evidence in `STATE.md`, the current readiness snapshot, and the milestone ledger without changing gate dispositions.
6. Run focused/full local tests, security checks, ledger validation, and exact-head CI; leave merge to the owner.

## Progress

The focused suite first failed because the runner did not exist; it now passes with digest-drift, invalid-policy, duplicate-key, and privacy assertions. Local full-suite and security results are recorded in the testing document. The manifest remains synthetic and unreviewed.

## Risks

- A manifest is only reviewable provenance metadata, not independent label review or a proof of data ownership.
- Changing both fixture and manifest digest requires PR review and a dataset version decision; a matching digest alone does not make the data representative.
- The score remains synthetic and deterministic; it makes no model-inference or production claim.

## Boundaries

Local/offline only. No new workflow, cloud resource, model/provider call, data download, secret access, deployment, or migration.
