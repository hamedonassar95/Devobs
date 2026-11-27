# Proposed Knowledge Intelligence architecture

**State:** Design only. The diagram and interfaces below describe a future
local-first system, not existing runtime behavior.

## Design goals

1. Use approved, versioned sources with traceable provenance.
2. Make ingestion and storage replaceable through narrow provider interfaces.
3. Keep retrieval read-only by default and require server-side tenant checks.
4. Keep model access and agent tools disabled unless an owner-reviewed phase
   explicitly adds them.
5. Treat retrieved content as untrusted evidence, never as executable policy.
6. Bound source size, parsing time, index size, tokens, compute, retention and
   reports.
7. Preserve existing Devobs interfaces rather than creating a second event,
   agent, monitoring, or CI framework.

## Logical flow

~~~mermaid
flowchart LR
  A[Approved repository or document source] --> B[Allowlisted read-only adapter]
  B --> C[Provenance and trust envelope]
  C --> D[Validate, classify, redact, version, deduplicate]
  D --> E[Local extraction and chunk manifest]
  E --> F[Optional local embedding adapter]
  E --> G[Lexical index]
  F --> H[Vector-store adapter]
  G --> I[Hybrid retrieval]
  H --> I
  I --> J[Server-side tenant and source authorization]
  J --> K[Cited evidence bundle]
  K --> L[Human-reviewed consumer]
  L -. future optional and separately gated .-> M[Model/agent adapter]
  M --> N[Proposal only; human approval remains outside model]
~~~

No call in this flow is implemented by this audit. Sources are not automatically
read and no model is called.

## Replaceable contracts

Keep contracts independent of a particular database or model:

- **SourceAdapter.read_snapshot(scope, revision)** returns bytes or normalized
  records plus a non-secret source identity, immutable revision, observed time,
  and adapter provenance. The adapter is allowlisted and read-only.
- **DocumentValidator.validate(item)** enforces type, size, encoding, allowed
  source, secret-exclusion result, trust label, retention class, and tenant.
  Invalid or incomplete provenance fails closed.
- **Normalizer.extract(item)** returns deterministic text and source offsets;
  it does not execute macros, scripts, HTML, notebooks, repository build steps,
  or embedded instructions.
- **Chunker.split(document, policy_version)** emits stable chunk IDs, source
  offsets, document version, and deterministic ordering.
- **EmbeddingProvider.embed(texts, model_revision)** is optional. Its result
  includes a verified model identifier/revision, dimensions, normalization
  contract and license reference. No remote provider is a default.
- **LexicalIndex.search(query, scope, limit)** and
  **VectorIndex.search(query_vector, scope, limit)** are read operations.
- **IndexWriter.upsert_version() / delete_version()** are ingestion-only
  operations behind a distinct, narrowly privileged adapter. They are never
  exposed to the retrieval/agent role.
- **EvidenceFormatter.format(hits)** returns references, source SHA/version,
  original byte/text offsets, score type, and retrieval time. It must not claim
  a citation if the source span cannot be recovered.
- **AuditSink.append(event)** records source and index versions, authorized
  scope, query ID digest, decision and outcome. It omits raw query/document
  contents by default.

These names are proposed design contracts, not existing public APIs.

## Data and trust boundaries

### Source admission

Admit only an explicitly approved source and scope. Check source identity,
version, maximum bytes, allowed content type, encoding, and ownership before
parsing. Scan for secret patterns before indexing, but do not treat a scanner
as proof that a document is safe. Minimize or redact sensitive values. Exclude
credentials, private connection strings, environment dumps, customer data
without a separate approved purpose, and prompt/system instructions from
indexable content.

### Untrusted content and prompt injection

Store content provenance and a trust class separately from content. A parser
must never execute retrieved content. Retrieved text is evidence only; it
cannot alter system instructions, tool permissions, tenant scope, budget, or
approval state. The response layer must show citations and allow abstention
when evidence is missing, stale, contradictory, or outside the caller's scope.

### Tenant authorization

Derive actor and tenant scope from trusted server middleware, then apply that
scope in both the application query and storage policy. A caller-supplied
tenant filter is not authentication. Add synthetic negative tests for every
read/write/delete path. If PostgreSQL is selected, new knowledge tables must
have forced RLS, immutable tenant ownership, and least-privilege roles. The
existing PostgresTenantStore is a read-only CI store and is not a suitable
ingestion writer.

### Versioning, deduplication, deletion

Use a stable document identity, source revision, normalized-content digest,
parser version, chunking policy version, and embedding model revision. Make
repeated ingestion idempotent. A changed source creates a new immutable
version; it must not silently rewrite its evidence history. Deletion requests
must remove searchable current versions, cached vectors, derived summaries and
scheduled work, then record a non-content audit tombstone. Backup retention
and legal retention behavior must be defined before any durable corpus.

## Existing components to reuse

- Reuse bounded evidence and SHA contracts in
  scripts/devobs_intelligence/contracts.py.
- Reuse exact-scope incident memory only for its existing incident use case;
  do not convert it into a document store.
- Reuse the local Graphify repository graph for source-to-code navigation.
- Reuse existing offline evaluation and synthetic fixtures as test patterns.
- Reuse existing OpenTelemetry, Prometheus and Grafana infrastructure for
  local observability if a later implementation has a measured need. Do not
  duplicate monitoring.
- Reuse existing RLS and CI security checks, but do not assume source SQL is
  applied to a live provider.

## Candidate request path

1. Authenticate via a separately verified middleware boundary.
2. Resolve tenant, role, allowed source set and request budget from trusted
   server context.
3. Reject unknown identity/scope with a fixed fail-closed response.
4. Retrieve lexical and optional vector candidates with the same tenant and
   source predicates.
5. Revalidate each citation against source version and retention state.
6. Return a bounded evidence bundle; no mutation or action is available here.
7. Log a privacy-minimized decision record without raw document/query content.

AI-9 is still BLOCKED. Any future model-written answer remains advisory until an
independently reviewed evaluation and identity-bound human approval boundary are
implemented.

## Resource and operating budgets

Before a local experiment, set hard maxima for documents, bytes per document,
chunks per document, vectors per batch, CPU time, memory, wall-clock timeout,
temporary disk, concurrent jobs, and output bytes. The local prototype must
abort at a limit, record a bounded reason, and clean temporary output. A future
system needs a separate owner-approved monthly spend boundary before any paid
service; no such service or budget was activated in this phase.

## Non-goals for this phase

- No vector database, embedding package, model, or cloud resource is installed.
- No existing database schema or deployment configuration changes.
- No document corpus is imported.
- No automatic agent scheduling, model inference, remediation, or deployment.
- No change to P01, AI-9, Codex runtime, Firebase, or release gates.
