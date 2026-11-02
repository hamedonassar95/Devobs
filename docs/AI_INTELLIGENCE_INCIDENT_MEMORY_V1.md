# AI Intelligence — local incident-memory provenance v1

**Scope:** offline metadata-only incident memory for P03 preparation. This is not a persistent store, a live corpus, or a readiness-gate change.

## Record contract

`IncidentRecord` keeps the existing tenant, project, service, category, reviewed runbook, outcome, and evidence digest fields. New records may also include a source commit SHA and timezone-aware `recorded_at`; the pair is all-or-nothing and the time is normalized to UTC. Older records without both fields remain supported by the legacy exact-scope `retrieve(...)` API.

`to_record()` and `from_record(...)` define an exact JSON-compatible schema version 1. The record includes all incident fields, nullable provenance fields for legacy rows, and a lowercase SHA-256 `record_digest` over the other canonical fields (sorted keys, compact separators, UTF-8). Unknown versions, extra/missing fields, malformed values, and a digest mismatch are rejected. Findings that use a memory row carry both its original evidence digest and the digest of the complete `IncidentRecord` payload.

`IncidentMemory` copies records on construction and returns detached copies. `retrieve_provenanced(...)` requires an explicit `now` and `max_age_seconds`, returns only exact tenant/project/service/category matches with `resolved` outcome and source/time provenance, and rejects future or stale records. The result remains bounded to five records. The maximum supported age is a code bound, not an approved data-retention period.

When `correlate(...)` receives a `ServiceTopologySnapshot`, it does not use legacy memory by default. The caller must pass `memory_max_age_seconds`; returned findings then carry `memory_provenance` entries containing the record evidence digest, source SHA, and recorded time. A historical record's source SHA is attributed but is not required to equal the current telemetry SHA.

## Limits

The record digest detects accidental or unsynchronized content changes; it is not a signature, writer identity, replay defense, or trusted provenance proof because a caller can recompute it. This contract does not establish incident-label quality, encrypt or persist memory, approve a retention period, or prove that the source SHA matches a deployed environment. Do not add customer incidents without a separate data-source and retention decision. No network, storage, model inference, or production action is involved.
