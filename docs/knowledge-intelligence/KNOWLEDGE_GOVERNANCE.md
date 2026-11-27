# KI-0 knowledge-source governance contract

**Contract:** `schemas/knowledge-source-policy.schema.json`, version 1

**Validator:** `scripts/check_knowledge_source_policy.py`

**Operating boundary:** local, offline, synthetic fixtures only

KI-0 defines what a future knowledge source must declare before it can be
considered for ingestion. It does not ingest, fetch, authenticate, store, index,
or retrieve documents. A validator result means only that the local policy
envelope is structurally consistent with this contract.

## Evidence reused from Devobs

- The CI event parser already uses exact fields, size bounds, digest checks, and
  fixed error codes: [`contracts.py`](../../scripts/devobs_intelligence/contracts.py).
- The tenant gate explicitly depends on an injected trusted identity resolver;
  it is not a live identity verifier: [`tenant_scope.py`](../../scripts/devobs_intelligence/tenant_scope.py).
- The action policy is read/propose/deny and does not treat model advice as
  authority: [`policy.py`](../../scripts/devobs_intelligence/policy.py).
- `APPROVED` is not a reachable state in the current state machine:
  [`state_machine.py`](../../scripts/devobs_intelligence/state_machine.py).
- PostgreSQL row-level security exists as source SQL, but no live application
  is asserted here: [`001_tenant_rls.sql`](../../deploy/postgres/001_tenant_rls.sql).

These source controls are useful patterns. They do not make this policy validator
a runtime authorization system.

## Version 1 fields

| Field | Requirement |
| --- | --- |
| `schema_version` | Integer `1`; booleans are not integers for this contract. |
| `source_id` | Stable bounded identifier. |
| `source_type` | One of the enumerated source classes below. |
| `source_version` | Stable revision/version token; must not contain content. |
| `source_uri` | Validated as a string only. Never resolved or fetched. |
| `content_sha256` | Lowercase 64-character SHA-256 syntax. The validator cannot compare it with source bytes. |
| `tenant_id` | Required, bounded tenant scope. Its authenticity is not checked. |
| `repository_id` | Required owner/repository scope. A syntax check is not proof of repository ownership or access. |
| `owner_id` | Required declared source owner. Its identity is not authenticated. |
| `classification` | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, or `RESTRICTED`. |
| `license_status` | One of the explicit statuses in the JSON Schema; unknown rights fail closed. |
| `ingestion_authorized` | Boolean declaration; only `true` is structurally admissible with `APPROVED`. |
| `retention_policy` | Bounded mode and maximum age in seconds. |
| `deletion_policy` | Explicit lifecycle action from the enumerated set. |
| `provenance` | Timestamp, declared actor, and approval reference; all are untrusted metadata until verified elsewhere. |
| `approval_status` | `APPROVED`, `PENDING`, `DENIED`, or `UNKNOWN`; only `APPROVED` passes this structural check. |

Unknown fields are rejected. Missing fields, unknown enum values, malformed
hashes, duplicate JSON keys, oversized inputs, and invalid combinations fail
closed with fixed error codes that do not echo input values.

## Allowed v1 combinations

Passing this table is necessary for a structural `PASS`; it is never sufficient
authorization to collect or use content. All rows also require explicit tenant,
repository, owner, provenance, and approval declarations.

| `source_type` | Classification | License evidence | Retention | Deletion |
| --- | --- | --- | --- | --- |
| `synthetic_fixture` | `INTERNAL` | `NOT_APPLICABLE` | `EPHEMERAL_TEST`, at most 86,400 seconds | `DELETE_ON_COMPLETION` |
| `public_document` | `PUBLIC` | `PUBLIC_DOMAIN`, `PERMISSIVE`, or `EXPLICIT_PERMISSION` | `SOURCE_RIGHTS`, at most 31,536,000 seconds | `DELETE_ON_REVOCATION` |
| `public_repository_file` | `PUBLIC` | `PUBLIC_DOMAIN`, `PERMISSIVE`, or `EXPLICIT_PERMISSION` | `SOURCE_RIGHTS`, at most 31,536,000 seconds | `DELETE_ON_REVOCATION` |
| `internal_document` | `INTERNAL` | `INTERNAL_USE_AUTHORIZED` or `EXPLICIT_PERMISSION` | `OWNER_APPROVED`, at most 2,592,000 seconds | `DELETE_ON_REQUEST_AND_EXPIRY` |
| `confidential_document` | `CONFIDENTIAL` | `CONFIDENTIAL_SCOPE_APPROVED` or `EXPLICIT_PERMISSION` | `OWNER_APPROVED`, at most 604,800 seconds | `DELETE_ON_REQUEST_AND_EXPIRY` |
| `restricted_document` | `RESTRICTED` | `EXPLICIT_PERMISSION` | No supported v1 duration | `DELETE_ON_REQUEST_AND_EXPIRY` |

`restricted_document` is representable so policy can identify it, but is
deliberately not ingestible in v1. The local fixture is the only source class
used by this implementation. Non-synthetic rows describe future contract
possibilities, not approval to process such material. Retention ceilings are
proposed conservative contract limits, not current repository runtime behavior
or a legal retention determination.

## Trusted authorization boundary

`approval_status: "APPROVED"`, `ingestion_authorized: true`, a named owner, a
tenant ID, or an approval reference can all be forged in a JSON file. The local
validator cannot prove who approved a source, who owns a tenant/repository, or
whether permission remains valid. Before any non-synthetic ingestion, a future
reviewed service must verify an authenticated actor, tenant membership,
repository/source ownership, purpose and license scope, an integrity-protected
approval bound to the exact source version and action, expiry and revocation,
and a separate human approval where required. Missing or unavailable checks
must deny.

## Local use

From the repository root:

```sh
python3 scripts/check_knowledge_source_policy.py \
  --input tests/fixtures/knowledge/source-policy-valid.json
python3 scripts/check_knowledge_source_policy.py \
  --input tests/fixtures/knowledge/source-policy-invalid.json
python3 -m unittest tests.test_knowledge_source_policy -v
```

The valid synthetic fixture emits a deterministic JSON report with
`decision: PASS` and `assurance: STRUCTURE_ONLY`. The invalid fixture exits
nonzero and emits fixed error codes only. The command is local-only, reads a
bounded regular JSON file and the checked-in schema, does not resolve source
URIs, execute source content, or make network calls. No package dependency is
required. No pinned JSON Schema validator was found in the inspected dependency
locks, so the standard-library validator enforces this version's declared
constraints and cross-checks the checked-in schema shape; it is not a
general-purpose JSON Schema implementation.

## Limitations and rollback

This checker does not authenticate identities or approvals, prove license
rights, compare the digest to source bytes, scan source content for secrets or
malware, enforce runtime tenant isolation, apply PostgreSQL RLS, implement
retention/deletion, or establish legal compliance. It must not be used as an
ingestion command or a runtime authorization oracle.

Rollback is a revert of the KI-0 documentation/schema/validator/test change.
There is no database, cloud, application-runtime, or persistent data state to
migrate or undo. Preserve existing P01, AI-9, human-approval, and Codex runtime
gates during review and rollback.
