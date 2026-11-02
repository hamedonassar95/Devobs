---
phase: implementation
title: Approval replay guard implementation record
description: Implementation evidence and lifecycle progress
---

# Implementation

## Lifecycle progress

- [x] Phase 2: requirements review complete
- [x] Phase 3: design review complete
- [x] Phase 4: initial plan created after reviews
- [x] Phase 7: implementation checked against design
- [x] Phase 8: tests completed or documented as not applicable
- [x] Phase 9: final code review complete

## Planned source changes

- `scripts/devobs_intelligence/incident_memory_approval.py`: bounded, thread-safe, process-local registry.
- `scripts/devobs_intelligence/incident_memory.py`: require a shared registry for signed memory imports.
- Approval/demo tests: ensure repeat import rejection and preserve signed provenance behavior.
- Incident-memory contract and system card: describe the process-local guarantee and restart/multi-process limits.

## Implemented changes

- `IncidentMemoryApprovalRegistry` validates each complete signed batch, builds the memory object, then atomically claims approval IDs under a thread lock. The default capacity is 10,000 and can only be lowered; there is no eviction.
- `IncidentMemory.from_approved_envelopes` now requires this registry. Test and demo call sites pass an explicit instance.
- Approval tests cover first-use/replay, a reissued payload with a consumed ID, invalid-batch atomicity, capacity failure, and 8 concurrent consumers. Contract and system-card docs distinguish this from durable replay protection.

## Focused verification

- `python3 -m unittest discover -s tests -p 'test_intelligence_incident_memory_approval.py' -v` — 14 tests passed.
- `python3 -m unittest discover -s tests -p 'test_intelligence_demo.py' -v` — 9 tests passed.
- `python3 -m compileall -q scripts/devobs_intelligence/incident_memory.py scripts/devobs_intelligence/incident_memory_approval.py` — passed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -q` — 790 tests passed, 22 skipped, 0 failed. The temporary environment contains the hash-locked API and development dependencies; no dependency files changed.
- `/tmp/devobs-p01-ac02-validation/bin/python -m bandit -r scripts -x scripts/check_site.py` — no issues identified.
- `python3 scripts/milestone_ledger.py --summary` — passed; the existing ledger structurally validates, but its latest recorded PR is #400.
- `npx --yes ai-devkit@latest lint --feature p03-memory-replay-guard-20261102` — 16 checks passed.
- `git diff --check` — passed.
- Optional task tracing probe `npx --yes ai-devkit@latest task list --json` exited 1: `unknown command 'task'`; lifecycle work proceeded without task events.

## Implementation notes

No persistent storage or global singleton is planned. The caller must explicitly retain and reuse the registry. No AI inference, external incident corpus, data migration, cloud resource, secret, or deployment is involved.

## Review result

The final source review confirms signature validation and memory construction precede the single lock-protected claim, batch failures do not partially update state, the capacity is hard-bounded without eviction, and the feature docs state the restart/multi-worker boundary. All internal signed-import callers were migrated. No blocking finding remains. This review is local and is not an independent human review.
