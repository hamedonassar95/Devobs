# AI Intelligence — local incident-memory provenance v1

**Scope:** offline metadata-only incident memory for P03 preparation. This is not a persistent store, a live corpus, or a readiness-gate change.

## Record contract

`IncidentRecord` keeps the existing tenant, project, service, category, reviewed runbook, outcome, and evidence digest fields. New records may also include a source commit SHA and timezone-aware `recorded_at`; the pair is all-or-nothing and the time is normalized to UTC. Older records without both fields remain supported by the legacy exact-scope `retrieve(...)` API.

`to_record()` and `from_record(...)` define an exact JSON-compatible schema version 1. The record includes all incident fields, nullable provenance fields for legacy rows, and a lowercase SHA-256 `record_digest` over the other canonical fields (sorted keys, compact separators, UTF-8). Unknown versions, extra/missing fields, malformed values, and a digest mismatch are rejected. Findings that use a memory row carry both its original evidence digest and the digest of the complete `IncidentRecord` payload.

`IncidentMemory.to_bundle()` and `IncidentMemory.from_bundle(...)` define a deterministic collection envelope, also schema version 1. The envelope sorts records by tenant, project, service, category, and evidence digest, caps imports at 1,000 records, and includes a `bundle_digest` over the version and complete record list. Import validates the envelope and every member before constructing a memory object, so an invalid or duplicate row rejects the whole bundle. The bundle and row digests detect accidental or unsynchronized edits; neither authenticates the writer.

`IncidentMemory.from_approved_envelopes(...)` is the external-record preflight path. Each envelope carries one provenance-bound resolved record, an approval ID, curator ID, issue/expiry times, and an Ed25519 signature over the complete canonical payload. The caller must supply an out-of-band trusted map from exact `(tenant, project, curator_id)` tuples to 32-byte Ed25519 public keys. Signatures, exact schema, record provenance, exact trust scope, and a maximum seven-day approval lifetime are verified before any memory is constructed. The entire batch is rejected on one invalid signature, untrusted curator/scope, duplicate approval ID, or duplicate record. When an approved record informs a finding, the result includes its approval ID, curator ID, and approval digest.

This curator signature approves use of incident metadata in the local memory layer only. It does not authorize incident response actions, deployments, merges, or changes to the human-approval state machine.

`IncidentMemory` copies records on construction and returns detached copies. `retrieve_provenanced(...)` requires an explicit `now` and `max_age_seconds`, returns only exact tenant/project/service/category matches with `resolved` outcome and source/time provenance, and rejects future or stale records. The result remains bounded to five records. The maximum supported age is a code bound, not an approved data-retention period.

When `correlate(...)` receives a `ServiceTopologySnapshot`, it does not use legacy memory by default. The caller must pass `memory_max_age_seconds`; returned findings then carry `memory_provenance` entries containing the record evidence digest, source SHA, and recorded time. A historical record's source SHA is attributed but is not required to equal the current telemetry SHA.

## Limits

Record and bundle digests detect accidental or unsynchronized content changes; they are not signatures because a caller can recompute them. The approval verifier checks signatures against the supplied key map but does not authenticate key enrollment, curator identity outside that trust map, or private-key custody. Duplicate approval IDs are rejected within one imported batch only; durable replay prevention across loads requires a protected persistent consumption registry and is not implemented. The ordinary constructor and unsigned bundle loader remain for trusted in-process fixtures; external imports must use the signed path. This contract does not establish incident-label quality, encrypt or persist memory, approve a retention period, or prove that the source SHA matches a deployed environment. Do not add customer incidents without a separate data-source and retention decision. No network, storage, model inference, or production action is involved.
