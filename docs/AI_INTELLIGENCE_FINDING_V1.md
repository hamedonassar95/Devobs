# AI Intelligence — incident finding wire contract v1 (historical)

Superseded by [incident finding wire contract v2](AI_INTELLIGENCE_FINDING_V2.md). The v2 parser intentionally rejects v1 records.

**Scope:** local, offline serialization for deterministic incident-correlation results. This is not an API endpoint, a trusted signature, or a readiness-gate change.

## Record contract

`IncidentFinding.to_record()` returns an exact JSON-compatible schema-version-1 object. `IncidentFinding.from_record(...)` rejects unknown or missing fields, unsupported versions, invalid scope, malformed or duplicate evidence, invalid status/category combinations, inconsistent topology or memory provenance, and a mismatched finding digest.

The record carries tenant and project scope, status, category, ranked and impacted services, evidence digests, runbook IDs, source SHA, model/calibration flags, optional topology snapshot digest and capture time, and bounded memory provenance. A finding with `INSUFFICIENT_EVIDENCE` has no ranked or impacted services. A finding with `PENDING_HUMAN_APPROVAL` remains a proposal for human review.

The `finding_digest` is SHA-256 over the canonical JSON payload without the digest field (sorted keys, compact separators, UTF-8, non-finite numbers rejected). It detects accidental or unsynchronized edits only; anyone can recompute it. It does not authenticate a producer, preserve a signature, authorize an action, or prove that supplied evidence is true.

The offline `AuditStore.append_finding(...)` consumer can bind this digest to a tenant-qualified source event and the existing local audit hash chain. See [incident finding audit binding](AI_INTELLIGENCE_FINDING_AUDIT.md) for the required `tenant/project` source scope and its limits.

When the record contains memory provenance, it includes the incident-record digest, source SHA and timestamp, plus the curator approval ID, approver ID and approval digest. Snapshot-based correlation includes only records with a verified, currently active approval. This wire contract does not re-verify the original Ed25519 signature or key trust map; downstream callers must preserve the verified result and must not treat this record digest as a signature.

## Limits

- No network endpoint, database, durable storage, model inference, or production action is added.
- No real incidents, customer data, or external data are included.
- Service ranking is a deterministic heuristic, not causal proof or calibrated confidence.
- Consumers must re-check tenant authorization and human-approval requirements; parsing a record is not authorization.
- This contract does not change AI quality evaluation or operational-readiness status.
