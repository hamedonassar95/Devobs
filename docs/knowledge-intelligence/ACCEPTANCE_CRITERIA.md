# Proposed acceptance criteria

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
