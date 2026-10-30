# AI-9 Confirmation Journal v1 — Implementation Record

**Status:** isolated local-development persistence prototype. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**. No detector, evaluation gate, threshold, production route, or live resource changed.

## API and commit behavior

`createPostDetectorConfirmationJournal({ filePath })` in [`post_detector_confirmation_journal.mjs`](../scripts/ai_intelligence/post_detector_confirmation_journal.mjs) wraps the existing confirmation layer without changing its input or output semantics:

```js
const journal = createPostDetectorConfirmationJournal({
  filePath: '/path/to/private-local-directory/ai9-journal.json',
});
const { result, queued_events } = await journal.processServiceWindow(window);
const pending = await journal.listPendingEvents({ limit: 100 });
await sendWithIdempotencyKey(pending[0].event_id, pending[0]);
await journal.acknowledgeEvents([pending[0].event_id]);
```

The directory must already exist, be canonical and private (`0700` or stricter). The journal file and lock use mode `0600`; the adapter does not create directories. An event contains only service/metric identifiers, incident ID, timestamp, fixed transition type/reason, policy version, and a deterministic SHA-256 ID; it does not include raw metric values or detector channel lists.

Each accepted service window restores the current checkpoint, processes the window, and writes the new checkpoint plus pending transitions together through one same-directory temp-file write, file sync, atomic rename, and directory sync. The lock file admits one cooperating writer; an existing lock returns `journal_locked` and is never stolen. If a process dies while holding the lock, recovery is manual only after confirming no writer remains.

Supported outbox transitions are `incident_started`, `incident_closed`, and `incident_interrupted`. Exact retry of the latest accepted window returns the confirmation result and does not queue an event again, including after that event has been acknowledged. Acknowledgement atomically removes pending IDs and is a no-op when retried. Limits are 8 MiB per journal, 10,000 pending events, and 1,000 acknowledgement IDs per call; malformed, oversized, linked, insecure, or unsupported data fails closed.

## Delivery semantics and limits

Checkpoint and outbox state share an atomic local file replacement, so the journal cannot commit one without the other. External alert delivery is a separate operation: a crash after delivery but before acknowledgement can repeat delivery. Consumers must deduplicate by `event_id`; semantics are at-least-once, not exactly-once.

This is not a production store. It is single-writer and local-only, has no multi-host coordination, authenticated integrity, encryption-at-rest guarantee beyond local file permissions, retention/deletion policy, service identity mapping, alert-provider integration, or operational restore runbook. The parent directory must be trusted; this is not a defense against a hostile local administrator. Other operating systems and filesystems have not been verified. The journal was tested only on the Linux/Node environment and disposable temporary directories.

No PostgreSQL, API, cloud resource, external network, credentials, real telemetry, AI-9 evaluator, benchmark, or holdout was used. No measured quality metric or gate result changed.

## Verification

- Focused contract: `node --test tests/post_detector_confirmation_journal.test.mjs` — **10/10 passed**.
- Full Node suite: `node --test tests/*.test.*` — **121/121 passed**, 0 failures, 0 skipped.
- Syntax: `node --check scripts/ai_intelligence/post_detector_confirmation_journal.mjs` and `node --check tests/post_detector_confirmation_journal.test.mjs` — **PASS**.
- CI contract tests: `python3 tests/test_ci_trigger_contract.py` (**2 tests**) and `python3 tests/test_ci_release_gate.py` (**1 test**) — **PASS**.
- Action pin audit: `python3 scripts/check_action_pins.py` — **39 workflow/template files, PASS**.
- `git diff --check` — **PASS**.
- Hosted GitHub CI and CodeQL results are pending PR creation; no hosted result is claimed in this record.
