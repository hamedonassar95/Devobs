# Knowledge Intelligence acceptance criteria

## KI-0 local contract acceptance

The validator contract is considered locally covered when its focused tests
pass for the checked-in synthetic fixtures, duplicate keys, malformed and
oversized inputs, missing scopes, invalid classifications/licenses/retention,
denied/pending/unknown approval states, conflicting declarations, fixed error
output, and no network access. This demonstrates policy-envelope handling
only. It does **not** test source authentication, real authorization, source
rights, data deletion, runtime tenant isolation, database RLS, retrieval, or
production behavior. The branch's exact test results are recorded in its PR.

## KI-1 source manifest contract

The local v1 manifest is acceptable only when it resolves policy references
from explicit inline records through the existing KI-0 validator; rejects
non-synthetic, pending, denied, unknown, revoked, or inconsistent states; and
validates deterministic IDs, canonical serialization, version chains, record
uniqueness, references, limits, and tenant/repository scope consistency.
Present fixture bytes must match their declared SHA-256, byte size, UTF-8 chunk
boundaries, and chunk hashes. When bytes are absent, integrity must be reported
as `UNVERIFIED_NO_CONTENT_BYTES`.

The KI-1 tests use synthetic values only. A successful validator result is
structural evidence: it is not source authenticity, trusted approval,
authenticated authorization, runtime tenant isolation, deletion execution,
or production readiness. The v1 validator supports one synthetic document per
source and a single linear version history.

KI-0–KI-2 local contract evidence does not establish search quality. The
retrieval, isolation, storage and operational thresholds below remain proposed
targets for later implementation; no retrieval target has been measured.

## KI-2 deterministic local ingestion

KI-2 is accepted as a **local prototype** when its focused tests pass and it:

- uses the existing KI-0 policy and KI-1 manifest validators without duplicating
  their policy decisions;
- accepts only bounded, explicitly supplied synthetic UTF-8 bytes and supported
  text content types; rejects empty, malformed, oversized or unsupported input;
- emits stable source/document/version/chunk identifiers, SHA-256 digests and
  contiguous, non-overlapping UTF-8 byte spans that correspond to the exact
  original bytes;
- returns a full manifest only after KI-1 validation succeeds, and produces no
  partial success on failure;
- defaults to dry-run, makes no network connection, persists no document text,
  and reports sanitized errors without echoing content;
- keeps deduplication, revocation and deletion state in memory, clearly labeling
  lifecycle assurance `IN_MEMORY_ONLY` and authorization `STRUCTURE_ONLY`.

The v1 manifest limits remain authoritative: document <= 65,536 bytes,
non-overlapping chunks, and KI-1 version/manifest count and size limits. KI-2
requires zero overlap. Benchmarks at 100 KiB and 1 MiB are reported as not run
because those inputs exceed the current KI-1 contract. The 1 KiB and 10 KiB
smoke measurements are single-environment diagnostics, not performance targets
or a claim of improvement. Synthetic policy checks do not test trusted tenant
authentication, runtime isolation, durable deduplication, secure erasure,
backup deletion or distributed revocation.

All values below are **proposed targets** for later implementation. No target
has been measured by this architecture audit. The first evaluator must publish
the corpus/query manifest, source revisions, evaluator version, hardware and
repeatable command before reporting any result.

| Area | Proposed measurable target | Measurement contract |
| --- | --- | --- |
| Retrieval Recall@10 | At least 0.90 on a frozen set of at least 100 synthetic queries with labeled relevant source IDs | Report micro and per-category recall; no tuned/test leakage; compare lexical baseline and candidate |
| Retrieval latency | p95 <= 250 ms for a warm 10,000-chunk local index on a declared 4-vCPU, 8-GiB RAM Linux x86_64 reference runner | Exclude embedding-generation time from query latency and report it separately; at least 30 repeated query batches |
| Citation accuracy | At least 0.98 of returned evidence references resolve to the exact source version and valid source offsets | Validate programmatically; separately score answer claims only if a later answer-generation phase is reviewed |
| Tenant isolation | 100% deny for all unauthorized cross-tenant read, query, update and delete fixtures; zero data leakage in at least 100 negative cases per operation | Synthetic tenant IDs only; test storage RLS and application checks separately |
| Index reproducibility | 100% exact manifest/chunk IDs and source digests for identical source, parser, chunk policy and lock/model revisions on the same pinned environment | For vector values, record maximum absolute difference as well as a stable artifact digest; do not require cross-hardware bitwise equality without evidence |
| Duplicate handling | 100 repeated ingestions of the same source revision create exactly one logical active version and no duplicate chunks | Test idempotency before/after restart in the local adapter |
| Data deletion | All active searchable copies, caches and derived rows disappear within 60 seconds after a valid local deletion request; audit tombstone remains without content | Backup-retention deletion limits must be separately documented; this target does not promise physical-media erasure |
| Agent evaluation | At least 0.95 correct evidence-backed proposal rate and 1.00 abstention on unsupported/unauthorized cases, using frozen synthetic tests and human-reviewed rubric | No auto-execution; report false positives and per-category counts. Does not close AI-9 |
| Runtime resources | Total retrieval/index process RSS <= 4 GiB for the declared 10,000-chunk evaluation; no request exceeds configured 2 CPU-seconds or 10-second wall timeout | Measure actual CPU, peak RSS, disk, index bytes and embedding batch time on the reference runner |
| Operational cost | $0 new hosted-service/model spend in the offline prototype; all further paid usage remains disabled absent separately documented owner authorization | Include license, compute, storage, backup, egress, telemetry and human operations; no hosted price is estimated until location and workload are fixed |

## Reporting rules

- Label targets as proposed and results as measured.
- A run that fails, times out or omits source/model/hardware versions is not a
  pass.
- Report mean, median, p95, sample count, confidence interval where appropriate,
  and an exact source/evaluator SHA.
- Do not claim improvement from different hardware, models, corpus, or
  configuration without a controlled comparison.
- Synthetic data measures implementation contracts, not natural incident
  quality or customer relevance.
- A goal for citation accuracy is not a claim about generated answer truth.
- A 100% isolation test suite is not mathematical proof; use independent
  database and security review before any hosted release.
