# KI-3 — frozen synthetic retrieval evaluation

**Evaluation version:** `ki3-synthetic-v1`

**Dataset SHA-256:**
`39e350014831ff06d1e279453df7b1d5f0316b512ff8ed0f9421f8d59b90a48c`

**Evaluation code source:** KI-3 implementation commit
`8682b059b71f0312364b0525877dd47ea44e8824`
**Status:** measured local synthetic baseline; not natural-query quality or
production readiness.

## Dataset and separation

The checked-in dataset is authored for this Devobs change and contains no
customer data, production logs, purchased book content, network-fetched text,
or external documents. The compact corpus fixture stores synthetic UTF-8 text
and KI-0 policy defaults; the evaluator constructs each record through KI-2,
then retrieval revalidates its KI-0 policy, KI-1 manifest, content hash, and
chunk spans before indexing.

| Fixture | Contents |
| --- | --- |
| `tests/fixtures/knowledge/retrieval-corpus.json` | 47 synthetic KI-0/KI-1/KI-2 records; one current version per record; two explicit out-of-scope sentinels |
| `tests/fixtures/knowledge/retrieval-queries.json` | 30 held-out synthetic evaluation queries, each with declared tenant/repository scope |
| `tests/fixtures/knowledge/retrieval-relevance.json` | Independently authored graded labels 1–3 keyed by query and synthetic document key; one empty-result query |
| `tests/fixtures/knowledge/retrieval-development-queries.json` | Four separate development prompts; never loaded by the evaluation command |

After scope filtering, 45 chunks are eligible for the evaluation
tenant/repository. The out-of-scope records are not used for BM25 document
frequency, average length, result counts, metrics, or ranking. The dataset hash
covers the exact complete corpus, evaluation-query, and relevance fixture
bytes, including those sentinel records, to identify the frozen artifacts.
They have no scoring or reporting influence other than changing the artifact
integrity digest if someone edits the fixture.

The evaluation labels and the default BM25 parameters were frozen as checked
in. No parameter tuning or label edits were made after observing these scores.
The four development queries are intentionally excluded from scoring.

The path `scripts/knowledge_retrieval_metrics.py` is a small support module
added beyond the requested file list so pure metric calculations stay
independently testable; `scripts/evaluate_knowledge_retrieval.py` owns fixture
validation, aggregation, and the manual benchmark CLI.

## Metric definitions and aggregation

For each query and `K ∈ {1, 3, 5, 10}`:

- **Precision@K:** unique relevant returned chunks among the first K divided by
  K, even when fewer than K results are returned.
- **Recall@K:** unique relevant returned chunks divided by the query's labeled
  relevant chunks. Queries with no relevant labels are undefined and excluded
  from the Recall@K macro average.
- **HitRate@K:** 1 if any relevant result occurs in the first K, otherwise 0.
  No-relevance queries are undefined and excluded from this macro average.
- **MRR:** reciprocal rank of the first relevant item over the returned list.
  No-relevance queries are undefined and excluded; queries with labels but no
  hit score 0.
- **nDCG@K:** graded labels use gain `2^grade - 1`, discounted by
  `log2(rank + 1)`, divided by ideal DCG. No-relevance queries are undefined.
- **Citation-reference accuracy:** exact match of result identifiers, hash,
  byte offsets, offset unit and provenance reference against the validated
  in-memory corpus. Aggregated as a micro-average over returned references.
- **Scope-exclusion correctness:** fraction of returned references that
  resolve inside the single requested index scope. Aggregated over returned
  references; an empty result set is vacuously correct and empty-result
  behavior is also measured separately.
- **Empty-result correctness:** whether the retriever returns no items exactly
  when the query has no relevant labels. It is macro-averaged over all queries.

Duplicate result IDs are removed while preserving first rank before ranking
metrics. The corpus currently emits one chunk per synthetic document; the
metrics still operate on chunk IDs. Citations are integrity checks against
synthetic fixtures, not source authenticity or factuality checks.

## Measured aggregate results

Command:

```sh
python3 scripts/evaluate_knowledge_retrieval.py
```

| K | Precision@K | Recall@K | HitRate@K | MRR | nDCG@K | Citation accuracy | Scope correctness | Empty-result correctness |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.9667 | 0.6092 | 1.0000 | 1.0000 | 0.9606 | 1.0000 | 1.0000 | 1.0000 |
| 3 | 0.4889 | 0.8276 | 1.0000 | 1.0000 | 0.9367 | 1.0000 | 1.0000 | 1.0000 |
| 5 | 0.3133 | 0.8736 | 1.0000 | 1.0000 | 0.9472 | 1.0000 | 1.0000 | 1.0000 |
| 10 | 0.1600 | 0.8908 | 1.0000 | 1.0000 | 0.9488 | 1.0000 | 1.0000 | 1.0000 |

The proposed exploratory Recall@10 target is `>= 0.90`; measured Recall@10 is
`0.8908`, so the target is **not met**. This result is left unchanged. The
small frozen fixture is deliberately useful as a regression contract, not a
claim that retrieval is ready for real users.

## Per-query results at K=10

This table reports the actual evaluator output without query text or source
content. `P` is Precision@10, `R` is Recall@10, `MRR` and `nDCG` follow the
definitions above, and `Empty` is empty-result correctness.

| Query | Labeled docs | Returned | P@10 | R@10 | MRR | nDCG@10 | Empty |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| q01 | 3 | 6 | 0.300 | 1.000 | 1.000 | 0.750 | 1.0 |
| q02 | 3 | 5 | 0.300 | 1.000 | 1.000 | 1.000 | 1.0 |
| q03 | 3 | 7 | 0.200 | 0.667 | 1.000 | 0.905 | 1.0 |
| q04 | 2 | 7 | 0.200 | 1.000 | 1.000 | 0.983 | 1.0 |
| q05 | 2 | 2 | 0.100 | 0.500 | 1.000 | 0.917 | 1.0 |
| q06 | 2 | 5 | 0.200 | 1.000 | 1.000 | 1.000 | 1.0 |
| q07 | 2 | 7 | 0.200 | 1.000 | 1.000 | 0.834 | 1.0 |
| q08 | 1 | 7 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q09 | 3 | 7 | 0.200 | 0.667 | 1.000 | 0.947 | 1.0 |
| q10 | 2 | 5 | 0.200 | 1.000 | 1.000 | 0.983 | 1.0 |
| q11 | 3 | 5 | 0.300 | 1.000 | 1.000 | 1.000 | 1.0 |
| q12 | 1 | 2 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q13 | 2 | 2 | 0.100 | 0.500 | 1.000 | 0.917 | 1.0 |
| q14 | 1 | 5 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q15 | 2 | 6 | 0.200 | 1.000 | 1.000 | 0.964 | 1.0 |
| q16 | 2 | 6 | 0.100 | 0.500 | 1.000 | 0.787 | 1.0 |
| q17 | 1 | 7 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q18 | 2 | 6 | 0.200 | 1.000 | 1.000 | 0.918 | 1.0 |
| q19 | 1 | 2 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q20 | 2 | 3 | 0.100 | 0.500 | 1.000 | 0.917 | 1.0 |
| q21 | 2 | 4 | 0.200 | 1.000 | 1.000 | 1.000 | 1.0 |
| q22 | 2 | 6 | 0.200 | 1.000 | 1.000 | 1.000 | 1.0 |
| q23 | 1 | 2 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q24 | 1 | 3 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q25 | 2 | 5 | 0.200 | 1.000 | 1.000 | 0.968 | 1.0 |
| q26 | 1 | 1 | 0.100 | 1.000 | 1.000 | 1.000 | 1.0 |
| q27 | 2 | 6 | 0.200 | 1.000 | 1.000 | 0.956 | 1.0 |
| q28 | 2 | 1 | 0.100 | 0.500 | 1.000 | 0.787 | 1.0 |
| q29 | 2 | 7 | 0.200 | 1.000 | 1.000 | 0.983 | 1.0 |
| q30 | 0 | 0 | 0.000 | — | — | — | 1.0 |

## Performance measurement

Command:

```sh
python3 scripts/evaluate_knowledge_retrieval.py \
  --include-benchmark --benchmark-iterations 100
```

Measured locally on Python `3.12.14`, Linux `x86_64`, 45 eligible chunks. The
query order used fixed seed `20261127`. Index construction used 10 independent
wall-time samples; query latency used 100 samples, with median and nearest-rank
P95. `tracemalloc` was run separately from latency timing.

| Measurement | Result |
| --- | ---: |
| Index-build mean, 10 samples | 0.055328 s |
| Index-build median, 10 samples | 0.055226 s |
| Query-latency median, 100 samples | 0.000013691 s |
| Query-latency P95, 100 samples | 0.000022744 s |
| Peak Python allocation while building index | 251,947 bytes |
| Peak Python allocation for one query | 2,751 bytes |

These are small local synthetic measurements, not CI thresholds, cross-runner
comparisons, or production latency promises. The benchmark ran against code
source commit `8682b059b71f0312364b0525877dd47ea44e8824`; later commits update
tests and documentation without changing the measured implementation.

## Reproduction and limitations

Run the focused tests with:

```sh
python3 -m unittest tests.test_knowledge_retrieval tests.test_knowledge_retrieval_evaluation -v
```

The dataset integrity check pins all three evaluation fixture files. The
development query file is intentionally outside the evaluation digest. The
evaluator emits stable per-query and aggregate JSON to stdout and makes no
network calls or report-file writes.

Limitations: the 30 queries and 45 eligible chunks are small, synthetic, and
independently authored for this implementation; graded relevance is not a
human study. The `1.0` citation result is a local reference-consistency check,
not authenticity or semantic correctness. The `1.0` scope score verifies only
that returned IDs resolve inside a caller-selected in-memory index. No
authenticated identity, database, persistent deletion, external model, or
agent behavior is covered.

## Separate dependency-risk follow-up

Two previously reported Dependabot items remain separate follow-up risks; this
KI-3 change adds no dependencies and changes no lockfile:

1. A historical **HIGH** alert was reported as `dependabot/1`, but its package,
   advisory identity, and current disposition remain **UNVERIFIED**. A
   withdrawn `picomatch` advisory exists in the repository, but available
   evidence does not prove that it is the same alert.
2. The owner-reported `minimatch`/`uuid` dependency-update blocker associated
   with Dependabot Updates run `45249445403` remains **UNVERIFIED** at current
   package/advisory/path level.

A read-only GitHub Dependabot alerts API query during this work returned HTTP
403 (`Resource not accessible by integration`). These are two distinct
reported records, but available evidence does not establish whether they
represent separate underlying advisories. Do not suppress either alert or
modify unrelated dependencies in KI-3.
