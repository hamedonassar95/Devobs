#!/usr/bin/env python3
"""Evaluate the frozen, synthetic KI-3 retrieval baseline offline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import statistics
import stat
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Sequence

try:
    from scripts.knowledge_retrieval import MAX_CORPUS_RECORDS, RetrievalError, build_index
except ModuleNotFoundError:  # Direct `python3 scripts/evaluate_knowledge_retrieval.py` invocation.
    from knowledge_retrieval import MAX_CORPUS_RECORDS, RetrievalError, build_index
try:
    from scripts.knowledge_ingestion import ChunkingConfig, IngestionError, KnowledgeIngestionEngine
except ModuleNotFoundError:  # Direct script invocation.
    from knowledge_ingestion import ChunkingConfig, IngestionError, KnowledgeIngestionEngine
try:
    from scripts.check_knowledge_source_manifest import MAX_CONTENT_BYTES
except ModuleNotFoundError:  # Direct script invocation.
    from check_knowledge_source_manifest import MAX_CONTENT_BYTES
try:
    from scripts.knowledge_retrieval_metrics import (
        EvaluationError,
        citation_reference_accuracy,
        empty_result_correctness,
        hit_rate_at_k,
        mean_reciprocal_rank,
        ndcg_at_k,
        precision_at_k,
        recall_at_k,
        scope_exclusion_correctness,
    )
except ModuleNotFoundError:  # Direct script invocation.
    from knowledge_retrieval_metrics import (
        EvaluationError,
        citation_reference_accuracy,
        empty_result_correctness,
        hit_rate_at_k,
        mean_reciprocal_rank,
        ndcg_at_k,
        precision_at_k,
        recall_at_k,
        scope_exclusion_correctness,
    )

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "knowledge"
CORPUS_PATH = FIXTURE_ROOT / "retrieval-corpus.json"
QUERIES_PATH = FIXTURE_ROOT / "retrieval-queries.json"
RELEVANCE_PATH = FIXTURE_ROOT / "retrieval-relevance.json"
DATASET_VERSION = "ki3-synthetic-v1"
EXPECTED_DATASET_SHA256 = "a7269c6b45f2e146c7bb38cb29a07d8e08f736921d64071957b0e9ee99a1fcc0"
MAX_FIXTURE_BYTES = 2_000_000
MAX_EVALUATION_QUERIES = 100
EVALUATION_K = (1, 3, 5, 10)
DEFAULT_BENCHMARK_ITERATIONS = 100
MIN_BENCHMARK_ITERATIONS = 10
MAX_BENCHMARK_ITERATIONS = 500
INDEX_BUILD_ITERATIONS = 10
BENCHMARK_ORDER_SEED = b"20261127"


def _fail(code: str) -> None:
    raise EvaluationError(code)


def _pairs_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def _check_json_depth(value: object, maximum: int = 32) -> None:
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > maximum:
            _fail("fixture_too_deep")
        if type(current) is dict:
            stack.extend((item, depth + 1) for item in current.values())
        elif type(current) is list:
            stack.extend((item, depth + 1) for item in current)


def _load_fixture(path: Path) -> object:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FIXTURE_BYTES:
            _fail("fixture_unavailable")
        with path.open("rb") as stream:
            raw = stream.read(MAX_FIXTURE_BYTES + 1)
    except OSError:
        _fail("fixture_unavailable")
    if len(raw) > MAX_FIXTURE_BYTES:
        _fail("fixture_too_large")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs_no_duplicates,
                           parse_constant=lambda _value: _fail("invalid_json_constant"))
        _check_json_depth(value)
        return value
    except EvaluationError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        _fail("fixture_malformed")


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        _fail("dataset_serialization_invalid")


def dataset_sha256() -> str:
    """SHA-256 of the three checked-in evaluation fixtures, in fixed path order."""
    digest = hashlib.sha256()
    for name, path in (("retrieval-corpus.json", CORPUS_PATH),
                       ("retrieval-queries.json", QUERIES_PATH),
                       ("retrieval-relevance.json", RELEVANCE_PATH)):
        try:
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FIXTURE_BYTES:
                _fail("fixture_unavailable")
            with path.open("rb") as stream:
                raw = stream.read(MAX_FIXTURE_BYTES + 1)
        except OSError:
            _fail("fixture_unavailable")
        if len(raw) > MAX_FIXTURE_BYTES:
            _fail("fixture_too_large")
        digest.update(name.encode("ascii") + b"\0" + raw + b"\0")
    return digest.hexdigest()


def _default_data() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    corpus = _load_fixture(CORPUS_PATH)
    query_set = _load_fixture(QUERIES_PATH)
    relevance = _load_fixture(RELEVANCE_PATH)
    if not all(type(item) is dict for item in (corpus, query_set, relevance)):
        _fail("dataset_shape_invalid")
    return corpus, query_set, relevance


def _query_payload(queries: object, dataset_version: str) -> list[dict[str, object]]:
    if type(queries) is dict:
        if set(queries) != {"dataset_version", "query_set", "queries"}:
            _fail("query_set_fields_invalid")
        if queries.get("query_set") != "evaluation":
            _fail("development_queries_not_evaluation")
        if queries.get("dataset_version") != dataset_version:
            _fail("dataset_version_mismatch")
        values = queries.get("queries")
    else:
        values = queries
    if type(values) is not list or not values or len(values) > MAX_EVALUATION_QUERIES:
        _fail("query_count_invalid")
    seen: set[str] = set()
    result = []
    for query in values:
        if type(query) is not dict or set(query) != {"query_id", "text", "tenant_id", "repository_id"}:
            _fail("query_fields_invalid")
        query_id = query.get("query_id")
        if type(query_id) is not str or not query_id or len(query_id) > 64 or query_id in seen:
            _fail("query_id_invalid")
        if type(query.get("text")) is not str:
            _fail("query_text_invalid")
        if type(query.get("tenant_id")) is not str or type(query.get("repository_id")) is not str:
            _fail("query_scope_invalid")
        seen.add(query_id)
        result.append(query)
    return result


def _normalize_relevance(
    value: object, query_ids: set[str], document_keys: set[str] | None,
) -> dict[str, dict[str, int]]:
    if type(value) is dict and set(value) == {"dataset_version", "labels"}:
        if value.get("dataset_version") != DATASET_VERSION:
            _fail("dataset_version_mismatch")
        value = value.get("labels")
    if type(value) is not dict or set(value) != query_ids:
        _fail("relevance_query_ids_invalid")
    output: dict[str, dict[str, int]] = {}
    for query_id, grades in value.items():
        if type(grades) is not dict:
            _fail("relevance_labels_invalid")
        if any(type(key) is not str or (document_keys is not None and key not in document_keys)
               or type(grade) is not int or not 1 <= grade <= 3
               for key, grade in grades.items()):
            _fail("relevance_labels_invalid")
        output[query_id] = grades
    return output


def _records_from_fixture(corpus: object, dataset_version: str) -> tuple[list[dict[str, object]], str, str]:
    expected_fields = {
        "dataset_version", "corpus_source_label", "scope", "policy_defaults",
        "source_version", "content_type", "created_at", "chunking", "records",
    }
    if (type(corpus) is not dict or set(corpus) != expected_fields
            or corpus.get("dataset_version") != dataset_version):
        _fail("corpus_fields_or_version_invalid")
    scope = corpus.get("scope")
    if type(scope) is not dict or set(scope) != {"tenant_id", "repository_id"}:
        _fail("corpus_scope_invalid")
    default_tenant = scope.get("tenant_id")
    default_repository = scope.get("repository_id")
    if type(default_tenant) is not str or type(default_repository) is not str:
        _fail("corpus_scope_invalid")
    source_version = corpus.get("source_version")
    content_type = corpus.get("content_type")
    created_at = corpus.get("created_at")
    defaults = corpus.get("policy_defaults")
    chunking_value = corpus.get("chunking")
    if (type(source_version) is not str or type(content_type) is not str
            or type(created_at) is not str or type(defaults) is not dict
            or type(chunking_value) is not dict
            or set(chunking_value) != {"target_chunk_bytes", "overlap_bytes", "max_chunks"}):
        _fail("corpus_template_invalid")
    try:
        chunking = ChunkingConfig(**chunking_value)
    except (IngestionError, TypeError):
        _fail("corpus_template_invalid")
    values = corpus.get("records")
    if type(values) is not list or not values or len(values) > MAX_CORPUS_RECORDS:
        _fail("corpus_records_invalid")
    records: list[dict[str, object]] = []
    for raw in values:
        if type(raw) is not dict or set(raw) != {
            "document_key", "text", "tenant_id", "repository_id", "lifecycle_state",
        }:
            _fail("corpus_record_fields_invalid")
        key = raw.get("document_key")
        text = raw.get("text")
        tenant = raw.get("tenant_id")
        repository = raw.get("repository_id")
        if (type(key) is not str or type(text) is not str or type(tenant) is not str
                or type(repository) is not str):
            _fail("corpus_content_invalid")
        try:
            content_bytes = text.encode("utf-8", errors="strict")
        except UnicodeError:
            _fail("corpus_content_invalid")
        if not content_bytes or len(content_bytes) > MAX_CONTENT_BYTES:
            _fail("corpus_content_size_invalid")
        source_id = f"synthetic-{key}"
        policy = copy.deepcopy(defaults)
        policy.update({
            "source_id": source_id,
            "source_version": source_version,
            "source_uri": f"fixture://{source_id}",
            "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
            "tenant_id": tenant,
            "repository_id": repository,
            "provenance": {
                "recorded_at": created_at,
                "recorded_by": "synthetic-reviewer-001",
                "approval_reference": f"synthetic-approval-{key}",
            },
        })
        try:
            ingested = KnowledgeIngestionEngine().ingest_document(
                source_policy=policy,
                document_bytes=content_bytes,
                source_version=source_version,
                document_key=key,
                tenant_id=tenant,
                repository_id=repository,
                content_type=content_type,
                created_at=created_at,
                chunking=chunking,
            )
        except (IngestionError, ValueError):
            _fail("corpus_record_invalid")
        manifest = ingested.manifest
        version_ids = [item["version_id"] for item in manifest["document_versions"]]
        if len(version_ids) != 1:
            _fail("corpus_record_invalid")
        records.append({
            "policy": policy,
            "manifest": manifest,
            "content_by_version": {version_ids[0]: content_bytes},
            "lifecycle_state": raw.get("lifecycle_state"),
        })
    if (type(corpus.get("corpus_source_label")) is not str
            or not corpus["corpus_source_label"] or len(corpus["corpus_source_label"]) > 120):
        _fail("corpus_source_label_invalid")
    return records, default_tenant, default_repository


def _canonical_input_digest(corpus: object, queries: object, relevance: object) -> str:
    digest = hashlib.sha256()
    for value in (corpus, queries, relevance):
        digest.update(_canonical_bytes(value) + b"\0")
    return digest.hexdigest()


def _validate_override_bounds(corpus: object, queries: object, relevance: object) -> None:
    total = 0
    for value in (corpus, queries, relevance):
        _check_json_depth(value)
        total += len(_canonical_bytes(value))
        if total > MAX_FIXTURE_BYTES:
            _fail("dataset_override_too_large")


def evaluate_dataset(
    *,
    corpus: object | None = None,
    queries: object | None = None,
    relevance: object | None = None,
    dataset_version: str = DATASET_VERSION,
) -> dict[str, object]:
    if type(dataset_version) is not str or dataset_version != DATASET_VERSION:
        _fail("dataset_version_unsupported")
    is_default = corpus is None and queries is None and relevance is None
    if is_default:
        corpus, queries, relevance = _default_data()
    elif corpus is None or queries is None or relevance is None:
        _fail("incomplete_dataset_override")
    else:
        _validate_override_bounds(corpus, queries, relevance)
    records, default_tenant, default_repository = _records_from_fixture(corpus, dataset_version)
    query_list = _query_payload(queries, dataset_version)
    query_ids = {query["query_id"] for query in query_list}
    grade_map = _normalize_relevance(relevance, query_ids, None)
    indexes: dict[tuple[str, str], object] = {}
    document_key_by_scope_chunk: dict[tuple[str, str], dict[str, str]] = {}
    document_keys_by_scope: dict[tuple[str, str], set[str]] = {}
    for query in query_list:
        scope = (query["tenant_id"], query["repository_id"])
        if scope not in indexes:
            indexes[scope] = build_index(records, tenant_id=scope[0], repository_id=scope[1])
            scoped_chunks = indexes[scope]._chunks
            document_key_by_scope_chunk[scope] = {
                chunk.chunk_id: chunk.document_key for chunk in scoped_chunks
            }
            document_keys_by_scope[scope] = {chunk.document_key for chunk in scoped_chunks}
    per_query: list[dict[str, object]] = []
    for query in query_list:
        index = indexes[(query["tenant_id"], query["repository_id"])]
        scope = (query["tenant_id"], query["repository_id"])
        grades = grade_map[query["query_id"]]
        if not set(grades) <= document_keys_by_scope[scope]:
            _fail("relevance_scope_invalid")
        raw_results = index.search(query["text"], top_k=20)
        retrieved_chunk_ids = [item["chunk_id"] for item in raw_results]
        retrieved_document_keys = [document_key_by_scope_chunk[scope][item] for item in retrieved_chunk_ids]
        relevant_keys = set(grades)
        per_k: dict[str, object] = {}
        for k in EVALUATION_K:
            current_results = raw_results[:k]
            ranked_docs = retrieved_document_keys[:k]
            per_k[str(k)] = {
                "precision_at_k": precision_at_k(ranked_docs, relevant_keys, k),
                "recall_at_k": recall_at_k(ranked_docs, relevant_keys, k),
                "hit_rate_at_k": hit_rate_at_k(ranked_docs, relevant_keys, k),
                "mrr": mean_reciprocal_rank(ranked_docs, relevant_keys),
                "ndcg_at_k": ndcg_at_k(ranked_docs, grades, k),
                "citation_reference_accuracy": citation_reference_accuracy(current_results, index),
                "scope_exclusion_correctness": scope_exclusion_correctness(current_results, index),
            }
        per_query.append({
            "query_id": query["query_id"],
            "relevant_document_count": len(relevant_keys),
            "returned_result_count": len(raw_results),
            "empty_result_correctness": empty_result_correctness(raw_results, relevant_keys),
            "retrieved_document_keys": retrieved_document_keys,
            "metrics": per_k,
        })

    aggregates: dict[str, object] = {}
    for k in EVALUATION_K:
        metric_names = ("precision_at_k", "recall_at_k", "hit_rate_at_k", "mrr", "ndcg_at_k",
                        "citation_reference_accuracy", "scope_exclusion_correctness")
        metrics: dict[str, float | None] = {}
        for metric in metric_names:
            values = [item["metrics"][str(k)][metric] for item in per_query]
            if metric in {"citation_reference_accuracy", "scope_exclusion_correctness"}:
                weights = [min(k, item["returned_result_count"]) for item in per_query]
                numerator = sum(value * weight for value, weight in zip(values, weights)
                                if value is not None and weight > 0)
                denominator = sum(weight for value, weight in zip(values, weights)
                                  if value is not None and weight > 0)
                metrics[metric] = numerator / denominator if denominator else (1.0 if metric == "scope_exclusion_correctness" else None)
            else:
                values = [value for value in values if value is not None]
                metrics[metric] = statistics.fmean(values) if values else None
        metrics["empty_result_correctness"] = statistics.fmean(
            item["empty_result_correctness"] for item in per_query
        )
        aggregates[str(k)] = metrics
    if is_default:
        input_digest = dataset_sha256()
        if input_digest != EXPECTED_DATASET_SHA256:
            _fail("frozen_dataset_integrity_mismatch")
    else:
        input_digest = _canonical_input_digest(corpus, queries, relevance)
    primary_scope = (default_tenant, default_repository)
    primary_chunks = indexes.get(primary_scope)
    return {
        "schema_version": 1,
        "dataset_version": dataset_version,
        "dataset_sha256": input_digest,
        "corpus_source_label": corpus["corpus_source_label"],
        "query_count": len(query_list),
        "eligible_chunk_count": primary_chunks.statistics["chunk_count"] if primary_chunks else 0,
        "aggregate_metrics": aggregates,
        "per_query": per_query,
        "limitations": [
            "Synthetic labels measure this fixed fixture only, not natural user relevance.",
            "Declared scope is not authenticated identity or production tenant isolation.",
            "Lexical score is not a probability or generated-answer truth measure.",
        ],
    }


def _percentile_95(samples: Sequence[float]) -> float:
    if not samples:
        _fail("benchmark_samples_missing")
    ordered = sorted(samples)
    rank = math.ceil(0.95 * len(ordered))
    return ordered[max(0, rank - 1)]


def _deterministic_query_order(queries: Sequence[str]) -> list[str]:
    """Interleave a fixed query set without a pseudo-random generator."""
    return sorted(
        queries,
        key=lambda query: (
            hashlib.sha256(BENCHMARK_ORDER_SEED + b"\0" + query.encode("utf-8")).digest(),
            query,
        ),
    )


def run_performance_benchmark(iterations: int = DEFAULT_BENCHMARK_ITERATIONS) -> dict[str, object]:
    if type(iterations) is not int or not MIN_BENCHMARK_ITERATIONS <= iterations <= MAX_BENCHMARK_ITERATIONS:
        _fail("benchmark_iteration_count_invalid")
    corpus, query_set, _relevance = _default_data()
    records, tenant, repository = _records_from_fixture(corpus, DATASET_VERSION)
    queries = _query_payload(query_set, DATASET_VERSION)
    scopes = {(query["tenant_id"], query["repository_id"]) for query in queries}
    if len(scopes) != 1:
        _fail("benchmark_requires_one_scope")
    selected_queries = [query["text"] for query in queries]
    selected_queries = _deterministic_query_order(selected_queries)

    build_samples = []
    for _ in range(INDEX_BUILD_ITERATIONS):
        started = time.perf_counter()
        index = build_index(records, tenant_id=tenant, repository_id=repository)
        build_samples.append(time.perf_counter() - started)

    latencies = []
    for sample in range(iterations):
        query = selected_queries[sample % len(selected_queries)]
        started = time.perf_counter()
        index.search(query, top_k=10)
        latencies.append(time.perf_counter() - started)
    tracemalloc.start()
    index.search(selected_queries[0], top_k=10)
    _query_current, query_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    build_index(records, tenant_id=tenant, repository_id=repository)
    _index_current, index_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "measurement_mode": "SYNTHETIC_LOCAL_BENCHMARK",
        "corpus_chunks": index.statistics["chunk_count"],
        "index_build_iterations": INDEX_BUILD_ITERATIONS,
        "index_build_mean_seconds": statistics.fmean(build_samples),
        "index_build_median_seconds": statistics.median(build_samples),
        "query_iterations": iterations,
        "query_latency_median_seconds": statistics.median(latencies),
        "query_latency_p95_seconds": _percentile_95(latencies),
        "index_peak_python_allocation_bytes": index_peak,
        "single_query_peak_python_allocation_bytes": query_peak,
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "query_order_seed": 20261127,
        "dataset_sha256": dataset_sha256(),
        "timing_note": "perf_counter wall time; tracemalloc measured separately from query latency",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-benchmark", action="store_true",
                        help="run the bounded synthetic performance baseline")
    parser.add_argument("--benchmark-iterations", type=int, default=DEFAULT_BENCHMARK_ITERATIONS)
    args = parser.parse_args(argv)
    try:
        report = evaluate_dataset()
        if args.include_benchmark:
            report["performance"] = run_performance_benchmark(args.benchmark_iterations)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2))
    except (EvaluationError, RetrievalError):
        print("knowledge retrieval evaluation failed: validation_error", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
