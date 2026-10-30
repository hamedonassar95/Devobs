# AI-9 Confirmation Checkpoint v1 — Implementation Record

**Status:** isolated development component. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**. This step does not evaluate detector quality or change detector behavior, gates, or thresholds.

## Contract and API

The existing `createPostDetectorConfirmationLayer()` now exposes `getCheckpoint()` and accepts an optional checkpoint on construction:

```js
const layer = createPostDetectorConfirmationLayer();
const result = layer.processServiceWindow({ serviceId, occurredAt, metrics });
const checkpoint = JSON.parse(JSON.stringify(layer.getCheckpoint()));
const restored = createPostDetectorConfirmationLayer({ checkpoint });
```

The checkpoint envelope records the schema version `ai9-confirmation-checkpoint-v1`, the exact policy version, each service's last accepted timestamp and input digest, the cached result for that timestamp, confirmation/coincidence histories, active incident state, and counters. Services and metric streams are serialized in deterministic sorted order.

- An exact retry of the most recently accepted window for a service returns a copy of its cached result without changing the state.
- The same service timestamp with a different normalized payload fails with `idempotency_conflict`.
- An older duplicate remains rejected by the existing `timestamp_not_increasing` rule. This does not provide arbitrary replay or out-of-order delivery.
- A malformed checkpoint, unsupported checkpoint version, or confirmation policy mismatch fails closed before state is restored.
- Caller mutation of the returned checkpoint or result does not mutate the component's internal cached state.

## Verification

- Contract tests: `node --test tests/post_detector_confirmation_checkpoint.test.mjs` — **7/7 passed**.
- Existing confirmation contract updated so exact last-window retries are idempotent while out-of-order/sub-cadence windows remain rejected.
- Full local Node suite: `node --test tests/*.test.*` — **111/111 passed**, 0 failed, 0 skipped.
- `node --check` on the changed module and tests, and `git diff --check`: **PASS**.
- Tests cover exact retry, conflicting duplicate, JSON round-trip and next-window equivalence, retry after restore, version/policy rejection, malformed-state rejection, and deterministic ordering.
- No seeds, benchmark, Precision/Recall/FPR, incident estimate, real telemetry, service, cloud resource, or production evaluator were used in this step.

## Limits before operational integration

This is a serializable checkpoint, **not durable storage**. The component still holds state in memory until a caller writes the checkpoint. A future adapter must define a durable backend and atomically commit checkpoint state with alert/outbox delivery; otherwise a crash can still cause lost or repeated downstream alerts. Multi-worker ownership, concurrent writes, retention and size bounds, crash recovery, store access control, encryption, and end-to-end routing remain unimplemented and unverified. The checkpoint is structurally validated but is not cryptographically authenticated; only a trusted, integrity-protected store should supply it.

The synthetic service identity used by the component is still supplied out of band. There is no approved production mapping in the event schema. This prototype is not an authorization to use real or customer telemetry and is not ready to attach to a live alert path.
