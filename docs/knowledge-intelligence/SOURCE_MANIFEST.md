# KI-1 knowledge source manifest

**Status:** implemented on `feature/ki-1-knowledge-source-manifest`; review and
merge are pending. This is a local contract, not an ingestion service.

## Contract

The v1 JSON document contains `policies`, `sources`, `document_versions`, and
`chunks`, with top-level `schema_version: 1` and `manifest_mode:
SYNTHETIC_OFFLINE`. Its JSON Schema is
[`schemas/knowledge-source-manifest.schema.json`](../../schemas/knowledge-source-manifest.schema.json).
The validator is [`scripts/check_knowledge_source_manifest.py`](../../scripts/check_knowledge_source_manifest.py).
The checked-in examples contain synthetic content only.

- A source repeats its tenant/repository scope, provenance, a `source_status`,
  and a `policy_reference`. The reference is the KI-0 policy record's
  `source_id`; it resolves only within the manifest's `policies` array. It is
  never interpreted as a path or URI. v1 accepts only `synthetic_fixture` and
  `ACTIVE`; pending, revoked, unknown, or other source types fail closed.
- A source policy is passed to the existing KI-0 `validate_policy` function.
  Its declared `APPROVED` and `ingestion_authorized` values are not trusted
  authorization evidence. The result is `STRUCTURE_ONLY`; a future trusted
  authorization service and runtime tenant checks remain necessary.
- The KI-0 policy's `content_sha256` must match the root (initial) document
  version for that source. When version bytes are present, the validator first
  verifies that digest against those exact UTF-8 bytes; without bytes, the link
  remains a declared digest relationship and the report is unverified.
- v1 maps one source to one logical document. A `document_key` is the stable
  caller-supplied logical name. `document_id` is `doc_` plus the lowercase
  SHA-256 of canonical JSON containing schema version, source ID, tenant ID,
  repository ID, and document key.
- `source_id` is `src_` plus SHA-256 of canonical JSON containing schema
  version, policy reference, tenant ID, and repository ID. `version_id` is
  `ver_` plus SHA-256 over schema version, document ID, content SHA-256, and
  content type. Identical bytes and type in the same document therefore map to
  one version ID; a repeated version is rejected. One linear, chronological
  history is required, with exactly one root and no cycles or branches.
- `chunk_id` is `chunk_` plus SHA-256 over schema version, version ID, chunk
  index, start/end offsets, offset unit, and chunk SHA-256. Chunk indexes start
  at zero and are contiguous within each version; spans cannot overlap.
- All IDs use full lowercase SHA-256 hex. Canonical JSON is UTF-8, preserves
  Unicode, sorts object keys, uses compact separators, and rejects NaN/Infinity.
  Manifest arrays serialize in the order `policy.source_id`, `source_id`,
  `(document_id, created_at, version_id)`, and `(version_id, chunk_index)`.

## Content integrity and limits

Offsets are **UTF-8 byte offsets**, with half-open `[start_offset, end_offset)`
spans. If optional `synthetic_content` bytes are present, the validator checks
their byte count and SHA-256, verifies every chunk span is a UTF-8 boundary, and
checks each chunk digest against the exact byte slice. If bytes are absent, the
report says `UNVERIFIED_NO_CONTENT_BYTES`; declared hashes and boundaries then
remain metadata only. A matching SHA-256 proves only that the supplied bytes
match the supplied digest; it does not prove source authenticity, authorship,
rights, or integrity before the bytes entered the fixture.

Limits: manifest 1 MiB; schema 64 KiB; 100 policies and sources; 500 document
versions; 5,000 chunks; each represented content 64 KiB; nesting depth 32.
Duplicate JSON keys, unknown fields, invalid UTF-8, excessive counts, malformed
timestamps, unsupported versions, missing links, and scope mismatches fail
closed. Diagnostics are fixed codes and never include document content.

```sh
python3 scripts/check_knowledge_source_manifest.py \
  --input tests/fixtures/knowledge/source-manifest-valid.json
python3 -m unittest tests.test_knowledge_source_manifest -v
python3 -m unittest tests.test_knowledge_source_policy -v
```

## Security boundary and limitations

Validation is offline: no source URI is fetched, no external reference is
resolved, and no source content is executed. `STRUCTURE_ONLY` does not
authenticate a tenant or approver, establish runtime tenant isolation, perform
retention/deletion, or make retrieved text trustworthy. Retrieved text remains
untrusted input and cannot grant permissions, change policy, or authorize agent
actions. There are no embeddings, vector stores, migrations, background jobs,
or production configuration changes in KI-1.

Rollback by reverting the KI-1 feature commit(s); there is no persisted state to
clean up. KI-2 may start only after review freezes this schema and the synthetic
evaluation fixture, and after documenting that source authentication, runtime
authorization, data deletion, and tenant isolation are not supplied by this
validator. No non-synthetic data is admitted by this implementation.
