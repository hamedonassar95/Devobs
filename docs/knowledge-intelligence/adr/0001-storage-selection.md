# ADR 0001: storage selection for Knowledge Intelligence

- **Status:** Accepted for offline evaluation only; production storage decision deferred.
- **Date:** 2026-11-26
- **Decision owner:** Devobs repository owner
- **Evidence baseline:** 1fc88930a9e66a318009b92f38510907b1793b1a

## Context

Devobs has PostgreSQL dependencies, a tenant-scoped read-only store contract,
forced-RLS SQL and PostgreSQL CI tests. It has no vector index or general
document store. The only incident-memory implementation is bounded,
metadata-only, in-process data. The Render Free PostgreSQL database is scheduled
for natural expiry on 2026-12-05 under the owner's direction and is not an
authorized or durable target for this roadmap.

Any option must preserve tenant isolation and human approval, support source
reconstruction and deletion, run locally with synthetic fixtures, and avoid new
cloud resources in the evaluation phase.

## Decision

Use PostgreSQL with pgvector as the **first local evaluation candidate**, paired
with existing PostgreSQL/RLS patterns. Do not add the extension, migration,
dependency, or service in this phase. A future proof-of-concept must use an
isolated local disposable database, synthetic data, pinned extension/image
versions, and the existing CI security gates.

This is not a final production storage commitment. Hosted extension availability,
live database attachment, backup policy, capacity and cost are unverified.
Production remains outside the scope and blocked by existing governance.

## Why this candidate

- Existing Python API dependencies include psycopg and the repository already
  tests PostgreSQL RLS behavior.
- A relational design can keep source metadata, document versions, tenant
  ownership, lexical fields and vectors in one transaction/policy domain.
- PostgreSQL full-text search can be measured alongside vector retrieval
  without introducing a second primary database.
- PostgreSQL backups and migration review are established operational concepts;
  an index can be rebuilt from a versioned source/model manifest.

These points indicate integration fit, not a measured speed, lower cost, or
supported hosted extension.

## Alternatives considered

| Option | Reason not selected first |
| --- | --- |
| Qdrant | Strong vector-focused option; adds a separate service, security boundary, backup and operational owner before a measured need exists. |
| ChromaDB | Convenient local client/server modes; persistence, server authorization, tenant boundary, and multi-user operational fit still require proof. |
| FAISS | Efficient search library but not a tenant-aware database; Devobs would need to own metadata, persistence, transactions, deletion and recovery. |
| Existing incident memory or JSONL event store | Wrong abstraction: neither is a durable general document index or semantically searchable store. |
| Existing Render Free database | Explicitly excluded: natural expiry is owner-directed, no extension support is verified, and no preservation or replacement action is authorized. |
| Firebase or unrelated Supabase projects | Separate source/application boundaries and current deny-by-default / isolation rules must remain unchanged. |

## Security and operational conditions for any future evaluation

- Do not write through the existing read-only PostgresTenantStore identity.
- Use a separate least-privilege local test identity for ingestion and a read-only
  query identity for retrieval.
- Enable and test forced RLS on every new tenant-bearing table.
- Include tenant and source-scope predicates in positive and negative tests for
  search, metadata retrieval, version replacement and deletion.
- Bind each chunk/vector to source ID, source version, normalized digest,
  extraction policy, chunk policy, embedding model revision and retention class.
- Treat filters from user input as selectors, never as trusted authorization.
- Preserve exact source offsets and verify citation provenance before return.
- Keep prompt injection and executable content out of tools, policies and system
  instructions; retrieved text is untrusted evidence.
- Add restore-from-backup and full re-index reproducibility checks before
  acceptance.
- No live database, cloud change, migration, paid service or production action
  is authorized by this ADR.

## Consequences

- Storage provider remains replaceable behind a small interface.
- The first benchmark can reuse existing PostgreSQL test expertise and synthetic
  tenant fixtures.
- pgvector is not added to the runtime lockfiles by this phase.
- If local tests fail tenancy, latency, deletion or resource targets, reopen this
  ADR and compare Qdrant/Chroma using the same data and metrics.
- A production storage decision requires separate reviewed evidence and must
  preserve all owner restrictions and release gates.
