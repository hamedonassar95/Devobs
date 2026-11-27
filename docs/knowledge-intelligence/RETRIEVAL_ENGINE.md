# KI-3 — deterministic lexical retrieval baseline

**Status:** local, synthetic-only implementation on
`feature/ki-3-lexical-retrieval`; review and hosted CI are pending. The branch
base is verified `origin/main` SHA `d1ccb4d681a775404a0ac1e74977d9c2507fd83e`.
This is not a production retriever, API, authenticated boundary, durable index,
or readiness approval.

## Design and reused contracts

`scripts/knowledge_retrieval.py` builds an in-memory BM25 index from explicitly
supplied records containing a KI-0 policy, KI-1 manifest, exact source bytes by
version, and a synthetic lifecycle state. It reuses:

- KI-0 `validate_policy` for declared policy structure and source eligibility.
- KI-1 `validate_manifest` and deterministic record IDs for schema, references,
  content hashes, version relationships, chunk boundaries, and UTF-8 byte spans.
- KI-2 `KnowledgeIngestionEngine.from_manifest`, `revoke_source`,
  `delete_document`, and `get_manifest` for the existing local lifecycle model.

No policy, manifest, or lifecycle subsystem is duplicated. The code requires
all exact version bytes for a supplied manifest, reconstructs a temporary
content-bearing copy in memory for KI-1 validation, and indexes only the latest
validated version. It then discards that temporary object when the build call
returns. Search results and index statistics contain no source text.

The existing Graphify integration remains focused on source-code structure and
relationships. This implementation searches explicit synthetic document
chunks and does not replace or duplicate Graphify.

## BM25 behavior

Defaults are `k1 = 1.2`, `b = 0.75`, and `top_k = 5`. `k1` must be finite and
positive; `b` must be finite and in `[0, 1]`; `top_k` must be an integer from 1
through 20. Queries are limited to 4,096 UTF-8 bytes. The index is bounded by
100 supplied records and KI-1's 5,000-chunk ceiling; each source document
retains KI-1's 65,536-byte maximum.

The implementation uses a positive Robertson/Sparck Jones IDF variant and
standard BM25 length normalization. For chunk `d`, term `t`, corpus size `N`,
document frequency `df(t)`, term frequency `f(t,d)`, chunk length `|d|`, and
average length `avgdl`:

```text
IDF(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))

score(q,d) = sum over each query-token occurrence t of
  IDF(t) * f(t,d) * (k1 + 1)
  / (f(t,d) + k1 * (1 - b + b * |d| / avgdl))
```

The corpus documents for BM25 are manifest chunks. Document frequency counts
each term once per chunk. Repeated query terms contribute repeatedly. Ranking is
descending score, then ascending `chunk_id` for a stable tie break. Chunks with
zero score are omitted. A valid query with no match returns `[]`; an empty or
punctuation-only query is rejected. A lexical score is a ranking value, not a
calibrated probability.

Index construction creates an inverted posting list from normalized term to
matching chunks, and computes scoped document frequencies at the same time.
Query execution unions only the postings for query terms before scoring; chunks
without a query term are not scored. Both the posting lists and their iteration
order are deterministic.

## Tokenization

Search normalization applies Unicode NFKC and `casefold()` to a temporary text
view, then retains Unicode letters, combining marks, and numbers. All other
characters delimit tokens. The original UTF-8 bytes and KI-1 SHA-256 values are
never normalized or rewritten.

Arabic and English token boundaries are supported by those Unicode rules. The
implementation does not stem, lemmatize, remove Arabic diacritics, identify
synonyms, or implement Arabic morphology. For example, morphological variants
can produce different tokens and no semantic match is promised. This tokenizer
is covered by synthetic tests only.

## Scope, lifecycle, and trust boundary

`build_index(records, tenant_id=..., repository_id=...)` checks that each
record's declared KI-0 and KI-1 tenant/repository values agree. Records whose
consistent declared scope differs from the requested scope are discarded
before document-frequency, average-length, ranking, result, or eligible-count
construction. Out-of-scope text therefore cannot affect scores or retrieval
output. It is not returned in an excluded-record list or a frequency count.

Missing or conflicting scope, malformed manifests, invalid content hashes,
pending/denied/unknown policies, and invalid lifecycle states fail the complete
index build. A declared `REVOKED` or `DELETED` lifecycle transition is applied
through the KI-2 in-memory engine and the record is then omitted. These values
and `APPROVED` remain synthetic declarations: they do not prove an
authenticated identity, source authorization, durable revocation, or runtime
tenant isolation. Caller-provided scope is not authentication.

The index uses only explicitly supplied synthetic UTF-8 bytes. It makes no
network request, performs no filesystem write, executes no document content,
and has no agent/tool interface. Retrieved text is inert: it cannot grant
permissions, override system rules, or authorize an action. No content is
returned by default; the result contract contains:

`rank`, `lexical_score`, `source_id`, `document_id`, `version_id`, `chunk_id`,
`content_sha256`, `start_offset`, `end_offset`, `offset_unit`, and
`provenance_reference`.

Every citation is checked against the supplied KI-1 manifest and source bytes.
Offsets use KI-1's half-open UTF-8 byte spans `[start_offset, end_offset)`.
`provenance_reference` is a declared synthetic reference, not proof of
approval or authenticity. A hash match proves byte consistency with the
supplied bytes, not who authored them or whether their use is authorized.

## Local use

Run the frozen evaluation from the repository root:

```sh
python3 scripts/evaluate_knowledge_retrieval.py
```

The command validates the fixed fixture set and prints one JSON report with
per-query results and aggregates. To include a manually invoked, bounded
performance measurement:

```sh
python3 scripts/evaluate_knowledge_retrieval.py \
  --include-benchmark --benchmark-iterations 100
```

Only 10–500 benchmark query iterations are accepted. Index construction is
measured separately in 10 iterations; query latency uses the requested number
of samples. Memory is measured separately with `tracemalloc`, so allocation
instrumentation does not distort reported latency. The tool has no output-file
option and writes no report artifact; redirect stdout only to a path selected by
the operator if a local report file is needed.

## Limits and rollback

- This is one-process, in-memory search over a small synthetic corpus; there is
  no concurrency control, persistence, authorization service, API, or model.
- The version history is validated, but only its latest leaf is indexed.
- KI-1's 65,536-byte source, 500-version, and 5,000-chunk limits remain in
  force. KI-2's zero-overlap requirement is unchanged.
- Synthetic evaluation does not establish customer relevance, source rights,
  production recall, secure deletion, or runtime isolation.
- No timing threshold is enforced in unit tests.

Rollback reverts the KI-3 retrieval module, evaluator, fixtures and their
documentation. It does not require deleting persistent content or changing
KI-0, KI-1, KI-2, application configuration, CI workflows, databases, cloud
resources, P01, AI-9, or Codex runtime gates.

The next independent milestone is KI-4: review one optional local embedding
adapter against this frozen baseline only after its model revision, license,
artifact hash, offline availability and resource budget are established.
