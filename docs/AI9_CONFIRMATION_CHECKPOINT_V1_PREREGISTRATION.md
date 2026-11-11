# AI-9 Confirmation Checkpoint v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-confirmation-checkpoint-v1` |
| Registered | 2026-10-30 12:52:00 UTC |
| Status | REGISTERED — IMPLEMENTATION NOT STARTED |
| Base commit | `e76e2bd83ec3738998cb560fa890a0a47e40059c` (`origin/main`) |
| Scope | Development-only state serialization and retry contract; no performance evaluation |

## Frozen contract

This step adds an optional checkpoint/restore API to the existing isolated post-detector confirmation component. It does not change the detector, confirmation thresholds, incident grouping rules, or AI-9 evaluation gates. It does not add a database, file writer, queue, service identity mapping, or cloud integration.

1. The checkpoint envelope is versioned as `ai9-confirmation-checkpoint-v1` and records the exact existing confirmation policy version. A missing, unsupported, malformed, or policy-mismatched checkpoint is rejected before state is accepted.
2. Checkpoints capture each service's stream timestamps, confirmation history, active incident and counters, coincidence history, plus the most recent accepted window fingerprint and returned result. Snapshot ordering is deterministic by service and metric identity.
3. Repeating the exact most recently accepted window for the same service returns its cached result and leaves all state unchanged. Reusing that timestamp with a different payload fails closed with `idempotency_conflict`.
4. A duplicate older than the most recent accepted window remains rejected by the existing strict-order contract. This version does not provide arbitrary replay, a durable persistence backend, or an atomic transaction with downstream alert delivery.
5. Restoring a JSON serialization of a checkpoint and processing the same next window must produce the same result and public state snapshot as uninterrupted processing.
6. Existing time-gap, sub-cadence, missing-metric, incident closure, channel, and cross-metric behavior remains unchanged.

## Verification plan

- Add contract tests for exact retry idempotency, same-time conflicting payload rejection, malformed/version/policy mismatch rejection, checkpoint round-trip equivalence, and preservation of existing sequence and incident semantics.
- Run the focused contract test and the repository's full Node test suite after implementation. Run syntax checks and `git diff --check`.
- No generated seed, benchmark, Precision, Recall, FPR, incident-prevalence estimate, or gate result will be produced in this step.
- The test fixtures use only synthetic channel names and timestamps. No real data, external service, production detector, or locked evaluation/holdout is involved.

## Limits

The checkpoint is a serializable state transfer object, not durable storage. Safe use across process restarts still requires a caller-selected persistent store and an atomic commit protocol that couples state checkpointing with alert/outbox delivery. Storage encryption, retention, concurrency, multi-worker ownership, crash recovery, and production service identity remain unimplemented and unverified. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**.
