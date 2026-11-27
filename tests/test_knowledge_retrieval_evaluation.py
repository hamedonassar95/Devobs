"""Offline tests for frozen synthetic retrieval evaluation and reporting."""

from __future__ import annotations

import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.evaluate_knowledge_retrieval import (
    EXPECTED_DATASET_SHA256,
    EvaluationError,
    MAX_FIXTURE_BYTES,
    _load_fixture,
    citation_reference_accuracy,
    dataset_sha256,
    empty_result_correctness,
    evaluate_dataset,
    hit_rate_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    run_performance_benchmark,
    scope_exclusion_correctness,
)
from scripts.knowledge_retrieval import build_index
from tests.test_knowledge_retrieval import record_for

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/knowledge"


def corpus_fixture():
    return json.loads((FIXTURES / "retrieval-corpus.json").read_text(encoding="utf-8"))


class KnowledgeRetrievalEvaluationTests(unittest.TestCase):
    def test_01_precision_at_k_uses_fixed_k_denominator(self):
        self.assertEqual(precision_at_k(["a"], {"a"}, 3), 1 / 3)

    def test_02_recall_at_k_counts_relevant_items(self):
        self.assertEqual(recall_at_k(["a", "b"], {"a", "c"}, 2), 0.5)

    def test_03_hit_rate_at_k_is_binary(self):
        self.assertEqual(hit_rate_at_k(["x", "a"], {"a"}, 2), 1.0)
        self.assertEqual(hit_rate_at_k(["x"], {"a"}, 1), 0.0)

    def test_04_mrr_uses_first_relevant_rank(self):
        self.assertEqual(mean_reciprocal_rank(["x", "a", "b"], {"a", "b"}), 0.5)

    def test_05_ndcg_supports_graded_relevance(self):
        actual = ndcg_at_k(["a", "b"], {"a": 1, "b": 3}, 2)
        ideal = ndcg_at_k(["b", "a"], {"a": 1, "b": 3}, 2)
        self.assertLess(actual, ideal)
        self.assertEqual(ideal, 1.0)

    def test_06_queries_with_no_relevant_results_have_undefined_recall(self):
        self.assertIsNone(recall_at_k(["a"], set(), 5))

    def test_07_duplicate_retrieval_ids_are_deduplicated(self):
        self.assertEqual(precision_at_k(["a", "a", "b"], {"a"}, 2), 0.5)
        self.assertEqual(mean_reciprocal_rank(["a", "a"], {"a"}), 1.0)

    def test_08_invalid_metric_k_is_rejected(self):
        for function, args in (
            (precision_at_k, (["a"], {"a"}, 0)),
            (recall_at_k, (["a"], {"a"}, True)),
            (ndcg_at_k, (["a"], {"a": -1}, 1)),
        ):
            with self.subTest(function=function.__name__), self.assertRaises(EvaluationError):
                function(*args)

    def test_09_empty_result_correctness(self):
        self.assertEqual(empty_result_correctness([], set()), 1.0)
        self.assertEqual(empty_result_correctness(["a"], set()), 0.0)
        self.assertEqual(empty_result_correctness([], {"a"}), 0.0)

    def test_10_citation_reference_accuracy_checks_exact_known_records(self):
        index = build_index([record_for("citation target", key="eval-citation")],
                            tenant_id="synthetic-tenant-001",
                            repository_id="synthetic-org/synthetic-repo")
        results = index.search("citation")
        self.assertEqual(citation_reference_accuracy(results, index), 1.0)
        broken = [dict(results[0], content_sha256="0" * 64)]
        self.assertEqual(citation_reference_accuracy(broken, index), 0.0)
        extra_scope = [dict(results[0], tenant_id="synthetic-tenant-002")]
        self.assertEqual(citation_reference_accuracy(extra_scope, index), 0.0)

    def test_11_scope_exclusion_correctness_checks_output_scope(self):
        index = build_index([record_for("scope target", key="eval-scope")],
                            tenant_id="synthetic-tenant-001",
                            repository_id="synthetic-org/synthetic-repo")
        self.assertEqual(scope_exclusion_correctness(index.search("scope"), index), 1.0)
        leaked = [dict(index.search("scope")[0], source_id="src_" + "0" * 64)]
        self.assertEqual(scope_exclusion_correctness(leaked, index), 0.0)

    def test_12_dataset_evaluation_is_reproducible(self):
        first = evaluate_dataset()
        second = evaluate_dataset()
        self.assertEqual(first, second)

    def test_13_results_include_all_requested_k_values_and_per_query_data(self):
        result = evaluate_dataset()
        self.assertEqual(sorted(map(int, result["aggregate_metrics"])), [1, 3, 5, 10])
        self.assertGreaterEqual(len(result["per_query"]), 30)
        self.assertIn("citation_reference_accuracy", result["aggregate_metrics"]["10"])

    def test_14_evaluation_reports_empty_query_correctness_and_scope(self):
        result = evaluate_dataset()
        self.assertIn("empty_result_correctness", result["aggregate_metrics"]["10"])
        self.assertIn("scope_exclusion_correctness", result["aggregate_metrics"]["10"])

    def test_15_dataset_hash_is_stable_and_present(self):
        digest = dataset_sha256()
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, dataset_sha256())
        self.assertEqual(digest, EXPECTED_DATASET_SHA256)
        self.assertEqual(evaluate_dataset()["dataset_sha256"], digest)

    def test_15a_checked_in_corpus_has_at_least_40_eligible_chunks(self):
        result = evaluate_dataset()
        self.assertGreaterEqual(result["eligible_chunk_count"], 40)

    def test_16_bad_relevance_label_is_rejected(self):
        query = {"query_id": "q", "text": "term", "tenant_id": "t", "repository_id": "o/r"}
        with self.assertRaises(EvaluationError):
            evaluate_dataset(corpus=corpus_fixture(), queries=[query], relevance={"q": {"not-a-record": 1}})

    def test_17_empty_evaluation_set_is_rejected(self):
        with self.assertRaises(EvaluationError):
            evaluate_dataset(corpus=corpus_fixture(), queries=[], relevance={})

    def test_18_corpus_dataset_duplicate_keys_and_schema_errors_fail_closed(self):
        query_set = json.loads((FIXTURES / "retrieval-queries.json").read_text(encoding="utf-8"))
        query_set["queries"].append(query_set["queries"][0])
        with self.assertRaises(EvaluationError):
            evaluate_dataset(corpus=corpus_fixture(), queries=query_set,
                             relevance={"unexpected": {}})

    def test_19_no_network_dependency(self):
        with mock.patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            evaluate_dataset()

    def test_20_invalid_dataset_version_is_rejected(self):
        with self.assertRaises(EvaluationError):
            evaluate_dataset(dataset_version="unsupported")

    def test_21_metric_results_are_json_safe_and_content_free(self):
        result = evaluate_dataset()
        rendered = json.dumps(result, ensure_ascii=False, allow_nan=False)
        self.assertNotIn("synthetic document content", rendered.lower())
        self.assertNotIn("raw_content", rendered)

    def test_22_out_of_scope_document_cannot_be_a_relevance_label(self):
        corpus = corpus_fixture()
        query = {"query_id": "q-scope", "text": "sentinel", "tenant_id": "synthetic-tenant-001",
                 "repository_id": "synthetic-org/operations"}
        with self.assertRaisesRegex(EvaluationError, "relevance_scope_invalid"):
            evaluate_dataset(corpus=corpus, queries=[query],
                             relevance={"q-scope": {"out-of-scope-tenant-sentinel": 1}})

    def test_23_performance_measurement_reports_separate_bounded_samples(self):
        with self.assertRaises(EvaluationError):
            run_performance_benchmark(9)
        result = run_performance_benchmark(10)
        self.assertEqual(result["corpus_chunks"], 45)
        self.assertEqual(result["query_iterations"], 10)
        self.assertEqual(result["index_build_iterations"], 10)
        for field in ("index_build_median_seconds", "query_latency_median_seconds",
                      "query_latency_p95_seconds"):
            self.assertGreater(result[field], 0)
        self.assertIn("index_peak_python_allocation_bytes", result)
        self.assertIn("single_query_peak_python_allocation_bytes", result)

    def test_24_evaluation_does_not_write_persistent_reports(self):
        with mock.patch.object(Path, "write_text", side_effect=AssertionError("write attempted")), \
                mock.patch.object(Path, "write_bytes", side_effect=AssertionError("write attempted")):
            result = evaluate_dataset()
        self.assertIn("aggregate_metrics", result)

    def test_25_cli_fixture_reader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"safe":1,"safe":2}', encoding="utf-8")
            with self.assertRaisesRegex(EvaluationError, "duplicate_json_key"):
                _load_fixture(path)

    def test_26_dataset_overrides_reject_excess_size_and_nesting(self):
        query = [{"query_id": "q", "text": "term", "tenant_id": "t", "repository_id": "o/r"}]
        with self.assertRaisesRegex(EvaluationError, "dataset_override_too_large"):
            evaluate_dataset(corpus={"large": "x" * MAX_FIXTURE_BYTES}, queries=query, relevance={"q": {}})
        nested = value = {}
        for _ in range(34):
            child = {}
            value["child"] = child
            value = child
        with self.assertRaisesRegex(EvaluationError, "fixture_too_deep"):
            evaluate_dataset(corpus=nested, queries=query, relevance={"q": {}})


if __name__ == "__main__":
    unittest.main()
