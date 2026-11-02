---
phase: planning
title: Approval replay guard implementation plan
description: Ordered, test-first tasks for bounded process-local replay prevention
---

# Plan

## Tasks

- [x] 1. Record the P03/T27 scope and explicit process-local limitation.
- [x] 2. Add a failing test for the required registry and repeat consumption.
- [x] 3. Implement bounded atomic consumption and adapt existing import callers.
- [x] 4. Add batch-atomicity, capacity, and concurrent-replay tests.
- [x] 5. Update contract/system-card text and feature lifecycle notes.
- [x] 6. Run focused and full offline verification; review the final diff.

## Dependencies

Uses existing canonical JSON digests, Ed25519 approval verification, and `ContextError`. No database, network, data download, model API, or CI workflow change is required.

## Risks and mitigation

- Callers may instantiate a fresh registry per import: require the registry argument and document one shared instance per process.
- Restart or multi-worker replay remains possible: state this limitation prominently; do not claim durable or production one-time consumption.
- Memory exhaustion: hard capacity, no eviction, and fail-closed behavior.
- Races: protect replay check and batch claim with one lock and verify using concurrent tests.

## Status

Focused approval and demo suites pass; the full Python suite passes with 22 expected skips; Bandit, AI DevKit lint, milestone-ledger validation, compileall, and diff checks pass. Review found no blocking implementation issue. Implementation remains on this isolated feature branch, with no deployment or service activation.
