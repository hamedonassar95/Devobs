# AI-9 Detector-to-Confirmation Adapter v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-detector-confirmation-adapter-v1` |
| Status | REGISTERED — IMPLEMENTATION NOT STARTED |
| Base commit | `498e629dcd0c2d915226444e736c30aff8e97b69` (`origin/main`) |
| Scope | Local composition contract from the existing detector to the existing confirmation layer/journal; no quality evaluation |

## Frozen design

Add a small adapter that accepts `{ serviceId, occurredAt, events }`, calls the existing `analyzeMetricEvents(events)`, converts each detector result into the confirmation layer's `{ metric, channels }` shape, and passes one aligned service window to an injected `processServiceWindow` implementation. The adapter may be used with the in-memory confirmation layer or the local confirmation journal because both expose that method.

1. Accept only a non-empty, bounded array of stored `server_metric` events. Reject non-metric input and duplicate event IDs before confirmation state is touched. The existing detector remains responsible for validating event schemas and calculating signals.
2. Require `occurredAt` to be a canonical UTC timestamp and require the latest observation for every analyzed metric to match it exactly. Reject duplicate metric names, including names split across conflicting units, instead of merging ambiguous series.
3. Map only the detector's validated `signals` into the confirmation channel list. Reject unknown/duplicate channels and inconsistent detector status/results. Do not forward metric values, detector thresholds, or raw events into the confirmation layer or adapter output.
4. Pass the caller-supplied stable `serviceId` unchanged. This adapter does not authenticate the caller, prove that the ID maps to the events, establish tenant scope, or verify source provenance; those remain external prerequisites and are explicitly not inferred from event fields.
5. Return the adapter version and the confirmation implementation's result without changing confirmation policy, journal delivery semantics, detector thresholds, evaluation gates, or incident rules.
6. Fail closed before invoking the confirmation implementation on invalid or misaligned input. Existing confirmation errors propagate without including raw metric values.

## Verification plan

- Add synthetic end-to-end contract tests that run the real `analyzeMetricEvents` implementation and pass its output through the adapter to the existing confirmation layer and local journal.
- Cover an isolated unconfirmed signal, persistent detector signals starting an incident, aligned cross-metric signals, malformed/non-metric/duplicate/misaligned inputs leaving state unchanged, and journal replay/idempotency without raw values in the durable event.
- Add the adapter syntax check and focused test to the existing pinned GitHub Actions Node job.
- Run the focused test, `node --test tests/*.test.*`, relevant CI contract tests, `node --check`, and `git diff --check`.

## Explicit non-goals and limits

This step does not measure Precision, Recall, FPR, or any AI-9 gate; it consumes no evaluation seed, holdout, or real telemetry. It does not connect an event store, API, external alert provider, hosted database, or live service. The event schema has no authenticated service identity, so passing an arbitrary but syntactically valid `serviceId` does not prove that the histories belong to that service. The adapter is a local composition prototype only.

AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**. No production detector, threshold, gate definition, evaluation protocol, or live resource will change.
