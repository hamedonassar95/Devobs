# AI Intelligence — incident finding audit binding

**Scope:** local, offline linkage between a validated `IncidentFinding` v1 record and the existing SQLite audit hash chain.

## Behavior

`AuditStore.append_finding(event, finding)` validates the finding through its v1 serializer and reconstructs the source event contract. The source event must be an incident whose canonical project reference is exactly `tenant/project`, and whose source SHA and evidence digests exactly match the finding. This qualifies the project key with the tenant so two tenants using the same project name do not share the same binding.

The audit entry remains a scoped `read_evidence` decision. It carries only the finding's `finding_digest` as `subject_digest`; service names and the full finding payload are not copied into the audit table. Repeated delivery of the same event and digest is idempotent. A different digest for the same event/action is rejected as a conflict.

Generic `AuditStore.append(...)` now verifies that the supplied policy evaluation is the exact result for the action being recorded. For example, an `ALLOW_READ` evaluation cannot be recorded as a `deploy` action.

The SQLite schema adds a `subject_digest` column with an empty-string default for existing rows. Opening a legacy database adds the column without rewriting old entries; verification omits the digest field for those legacy hashes, preserving their original chain.

## Limits

- This is local logical audit evidence, not a tamper-proof hosted service. A privileged writer can still rewrite the whole database and recompute the chain.
- A content digest binds bytes but does not authenticate the producer or prove the underlying evidence is true.
- The source envelope and finding are supplied by the caller. This method verifies their declared scope and digests; it does not verify an external provider signature or tenant authorization.
- No endpoint, live provider, database service, customer data, model inference, or external action is added.
