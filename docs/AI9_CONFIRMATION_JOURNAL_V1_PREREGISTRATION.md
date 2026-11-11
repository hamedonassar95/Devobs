# AI-9 Confirmation Journal v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-confirmation-journal-v1` |
| Registered | 2026-10-30 13:33:13 UTC |
| Status | REGISTERED — IMPLEMENTATION NOT STARTED |
| Base commit | `71dbdbb958edec0238a0a601db4bc0243529aeca` (`origin/main`) |
| Scope | Local development persistence contract for confirmation checkpoint plus transactional outbox; no detector-quality evaluation |

## Frozen contract

This step adds a Node.js built-in-filesystem adapter around the existing isolated confirmation layer. It does not alter the detector, confirmation policy, incident rules, or AI-9 gates; it does not connect to the staging API, PostgreSQL, alert providers, or a live service.

1. A versioned journal document contains both the confirmation checkpoint and pending outbox events. A successful service-window operation updates both in one same-directory atomic file replacement; a partial state-only or outbox-only commit is forbidden.
2. Writes use an exclusive lock file. If a lock already exists, the operation fails closed with `journal_locked`; it never steals a lock, including one left after a crash. The operator must first establish that no writer is active before manual stale-lock recovery.
3. The write sequence is: validate current journal, restore the checkpoint, process the window, derive transition events, serialize under the byte limit, write a mode-0600 temporary file, sync it, rename it over the journal, then sync the containing directory. Temporary files are removed on failures where possible.
4. Only `incident_started`, `incident_closed`, and `incident_interrupted` transitions enter the outbox. Event IDs are deterministic SHA-256 digests; records omit detector channel lists and raw metric values. An exact retry of the latest accepted window returns the cached result and must not re-enqueue events already acknowledged. A same-time conflicting payload remains rejected by the confirmation layer.
5. Outbox acknowledgement atomically removes validated event IDs. Repeating acknowledgement is a no-op. Delivery is at-least-once across a crash between sending and acknowledging; a downstream consumer would need to deduplicate by event ID.
6. Fail closed if the document is malformed, has unsupported versions, is a symlink/non-regular file, has group/other file permissions, exceeds 8 MiB, or contains more than 10,000 pending events. The selected parent directory must already exist and be trusted/private; this adapter does not create or secure a directory tree.
7. The adapter is single-writer and local-development-only. The lock coordinates cooperating processes, but stale-lock recovery, hostile directory races, authenticated integrity, encryption, retention, multi-host operation, authorization, and production durability guarantees are out of scope.

## Verification plan

- Add temporary-directory contract tests for restart recovery, atomic checkpoint/outbox behavior, deterministic transition IDs, retry without event resurrection, acknowledgement, invalid input with unchanged journal bytes, lock refusal, and unsafe/corrupt storage rejection.
- Add the focused test to the existing pinned GitHub Actions Node test job so CI executes this contract.
- Run the focused test, `node --test tests/*.test.*`, syntax checks, and `git diff --check`. No performance benchmark or AI-9 evaluator is part of this step.
- Use only synthetic service IDs, detector channel names and timestamps in an isolated temporary directory. No network, credentials, real telemetry, cloud resource, or production endpoint.

## Explicit limits

This file journal demonstrates a local atomic state-plus-outbox contract only. It is not an approved production store or alert delivery path, and it does not make the confirmation layer production-ready. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**.
