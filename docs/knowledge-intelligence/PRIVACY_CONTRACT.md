# KI-0 privacy contract

**Status:** local design contract; no corpus or runtime ingestion exists.

## Data admitted in this phase

Only synthetic fixtures created for tests may be read. Do not place real
customer data, personal data, raw production logs, credentials, access tokens,
private keys, connection strings, purchased books, copyrighted source copies,
or unapproved confidential material in fixtures, reports, or commits. Public
availability alone is not permission to copy or retain a work; record and
verify its license and purpose before any later use.

No automatic ingestion, external embedding/API calls, database migrations,
cloud provisioning, production configuration changes, or provider access is
part of KI-0. The validator reads only local JSON policy metadata and does not
fetch a declared URI.

## Scope and access

Future knowledge records must carry both `tenant_id` and `repository_id` scope.
The validator checks syntax and presence only. A later runtime must derive the
tenant from independently verified identity and membership, enforce repository
authorization on every read and write, and fail closed when either scope is
missing or ambiguous. Never trust caller-supplied IDs or a policy file as proof
of access. Cross-tenant retrieval must be tested independently at application
and storage layers before runtime integration.

## Retention, deletion, and revocation

The schema requires an explicit retention mode, maximum age, and deletion
policy. The v1 ceilings in [the governance contract](KNOWLEDGE_GOVERNANCE.md)
are local design limits, not deployed timers or a legal hold decision. Any
future implementation must define an accountable owner, deletion trigger,
expiry handling, and an auditable outcome before ingesting non-synthetic data.

On permission withdrawal or a valid deletion request, a future system must
prevent new retrieval immediately, remove the source and derived chunks,
embeddings, indexes, caches, and exported reports, and record a content-free
tombstone. Backup copies and restore procedures need a documented expiry and
replay prevention policy; this repository has not verified physical erasure or
backup behavior. If deletion cannot be confirmed, access remains blocked and
the limitation is reported.

## Provenance and data minimization

Retain only fields necessary to identify a source revision, scope, rights,
policy version, approval evidence, and lifecycle. Do not log source text,
prompts containing source text, secret values, or sensitive host identifiers.
The current validator returns only a decision and fixed reason codes; it does
not print input content. `content_sha256` is accepted as a format-checked claim,
not independently computed evidence.

## Retrieved content is untrusted

Any future retrieved document, repository file, or embedded instruction is
untrusted data. It cannot change system/developer policy, grant permissions,
broaden tenant or repository scope, approve ingestion, authorize an agent tool,
trigger a deployment, or bypass human approval. Present citations and source
provenance as evidence; keep policy and executable tool authorization in
separate trusted code paths. Prompt-injection tests and safe rendering are
required before a retrieval UI or agent integration.

## Static-validation boundary

A KI-0 `PASS` confirms only local shape and consistency against the checked-in
v1 schema and allowlist. It proves no identity, authorization, data isolation,
source integrity, privacy compliance, deletion completion, or production
readiness. Synthetic policy tests do not test runtime tenant isolation. Any
unknown, conflicting, missing, revoked, or unavailable runtime authorization
must fail closed.
