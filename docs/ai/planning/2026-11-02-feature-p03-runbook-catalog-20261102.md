---
phase: planning
title: Category-bound runbook catalog implementation plan
description: Ordered test-first tasks for exact category/runbook validation
---

# Plan

## Milestones

- [x] M1: Regression tests reproduce mismatched runbook acceptance.
- [x] M2: A single immutable catalog drives both adviser output and memory validation.
- [x] M3: Offline verification, P03 contract documentation, and merged-evidence records are current.

## Task breakdown

### Phase 1: Demonstrate the gap

- [x] 1. Add tests for valid category/ID pairs, known cross-category IDs, and unknown syntactically valid IDs. Expected evidence: the rejection tests fail before the fix.
- [x] 2. Add serialized-record and trusted, correctly re-signed envelope tests. Recomputed content hashes and signatures must not bypass category/catalog validation.

### Phase 2: Share and enforce the catalog

- [x] 3. Add one immutable category-to-ID/test-instruction catalog and route `adviser.propose(...)` through it without changing current outputs.
- [x] 4. Validate exact category/ID membership in `IncidentRecord` construction so direct, bundle, and signed-envelope paths reject unsupported/mismatched IDs.

### Phase 3: Integrate and review

- [x] 5. Update incident-memory contract and this feature's implementation/testing records with observed results and compatibility limits.
- [x] 6. Add evidence for merged PRs #401–#403 to the current readiness report and milestone ledger in this same feature PR; preserve all existing gate values. Run the ledger validator and review exact GitHub evidence.
- [x] 7. Run focused adviser/memory/approval suites, full Python suite, compileall, security checks, AI DevKit feature lint, milestone-ledger validation, and `git diff --check`; perform final source review.

## Dependencies and validation trace

- Task 1 maps to acceptance criteria 1, 2, and 4.
- Task 2 maps to criteria 2 and 3.
- Tasks 3–4 map to criteria 1, 2, 3, and 4.
- Tasks 5–7 map to criteria 5 and 6 and preserve the offline-only boundary.
- No database, API, external incident data, paid model, network runtime, resource provisioning, or migration is required.

## Risks and mitigation

- Existing callers may have used a custom ID matching only the old regex. Search all repository call sites; the fixed catalog is intentional and any future new runbook requires an explicit catalog change and test.
- Duplicated catalog mappings could drift. Keep IDs and deterministic adviser text in one shared module.
- Hashes/signatures must not obscure the semantic validation gap. Recompute both in the adversarial test and show parsing still rejects the record.
- Merged evidence may be stale or incomplete. Query PR merge SHAs and exact PR/main check runs from GitHub; do not infer model calls from workflow status.

## Resources and estimates

- One local feature worktree, Python standard library, existing cryptography test dependency, GitHub CLI for read-only evidence, and existing hash-locked validation environment.
- Estimated effort: one short implementation task plus verification/review; no schedule dependency.

## Progress

Tasks 1–7 are complete. New regression tests failed on the pre-change implementation for category mismatch, unsupported IDs, rehashed wire records, and a trusted signature over a mismatched record; focused suites pass after the shared catalog and record validation were added. The full suite passed 793 tests with 22 expected skips; compileall, Bandit, AI DevKit feature lint, milestone-ledger validation, and `git diff --check` passed. Final review confirms the shared catalog is the only mapping and valid adviser output is unchanged. The incident-memory contract, current readiness report, state summary, and ledger record verified PR #401–#403 evidence without changing gate values.
