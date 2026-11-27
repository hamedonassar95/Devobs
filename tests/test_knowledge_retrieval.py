"""Offline contract tests for the KI-3 BM25 retrieval baseline."""

from __future__ import annotations

import copy
import builtins
import hashlib
import json
import os
import socket
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

from scripts.knowledge_ingestion import ChunkingConfig, KnowledgeIngestionEngine
from scripts.knowledge_retrieval import (
    MAX_CORPUS_RECORDS,
    MAX_QUERY_BYTES,
    MAX_TOP_K,
    RetrievalError,
    build_index,
    tokenize,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_FIXTURE = ROOT / "tests/fixtures/knowledge/source-policy-valid.json"


def record_for(
    text: str,
    *,
    key: str = "retrieval-note",
    tenant: str = "synthetic-tenant-001",
    repository: str = "synthetic-org/synthetic-repo",
    lifecycle: str = "ACTIVE",
    target_bytes: int = 256,
) -> dict[str, object]:
    content = text.encode("utf-8")
    policy = json.loads(POLICY_FIXTURE.read_text(encoding="utf-8"))
    policy.update({
        "source_id": f"synthetic-{key}",
        "source_uri": f"fixture://synthetic-{key}",
        "source_version": "retrieval-v1",
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "tenant_id": tenant,
        "repository_id": repository,
        "provenance": {
            "recorded_at": "2026-11-27T00:00:00Z",
            "recorded_by": "synthetic-reviewer-001",
            "approval_reference": f"synthetic-approval-{key}",
        },
    })
    ingested = KnowledgeIngestionEngine().ingest_document(
        source_policy=policy,
        document_bytes=content,
        source_version="retrieval-v1",
        document_key=key,
        tenant_id=tenant,
        repository_id=repository,
        content_type="text/plain; charset=utf-8",
        created_at="2026-11-27T00:00:00Z",
        chunking=ChunkingConfig(target_chunk_bytes=target_bytes),
    )
    version = ingested.manifest["document_versions"][0]
    return {
        "policy": policy,
        "manifest": ingested.manifest,
        "content_by_version": {version["version_id"]: content},
        "lifecycle_state": lifecycle,
    }


class KnowledgeRetrievalTests(unittest.TestCase):
    def build(self, records, **kwargs):
        return build_index(
            records,
            tenant_id=kwargs.pop("tenant_id", "synthetic-tenant-001"),
            repository_id=kwargs.pop("repository_id", "synthetic-org/synthetic-repo"),
            **kwargs,
        )

    def test_01_valid_corpus_builds_and_retrieves_expected_chunk(self):
        index = self.build([record_for("GitHub Actions validates CI workflows.", key="ci")])
        results = index.search("github actions", top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["document_id"], index._chunks[0].document_id)

    def test_02_empty_corpus_is_valid_and_returns_explicit_empty_results(self):
        self.assertEqual(self.build([]).search("workflow"), [])

    def test_03_empty_query_is_rejected(self):
        index = self.build([record_for("A local CI pipeline.")])
        with self.assertRaisesRegex(RetrievalError, "empty_query"):
            index.search("")

    def test_04_oversized_query_is_rejected_before_tokenization(self):
        index = self.build([record_for("pipeline")])
        with self.assertRaisesRegex(RetrievalError, "query_too_large"):
            index.search("x" * (MAX_QUERY_BYTES + 1))

    def test_05_invalid_top_k_values_are_rejected(self):
        index = self.build([record_for("pipeline")])
        for value in (0, -1, True, MAX_TOP_K + 1, 1.5):
            with self.subTest(value=value), self.assertRaises(RetrievalError):
                index.search("pipeline", top_k=value)

    def test_06_exact_term_retrieval(self):
        index = self.build([
            record_for("kubernetes readiness probe", key="kube"),
            record_for("incident response evidence", key="incident"),
        ])
        self.assertEqual(len(index.search("kubernetes")), 1)

    def test_07_multiple_query_terms_rank_combined_match_first(self):
        combined = record_for("CI workflow validation tests", key="combined")
        index = self.build([combined, record_for("CI process only", key="partial")])
        results = index.search("workflow validation", top_k=2)
        self.assertEqual(results[0]["document_id"], combined["manifest"]["document_versions"][0]["document_id"])

    def test_08_unknown_terms_return_empty(self):
        index = self.build([record_for("ordinary workflow checks")])
        self.assertEqual(index.search("quartzvane"), [])

    def test_09_ranking_is_deterministic_across_repeated_queries(self):
        index = self.build([record_for("same words here", key=f"same-{i}") for i in range(3)])
        self.assertEqual(index.search("same words"), index.search("same words"))

    def test_10_equal_scores_use_stable_chunk_id_tie_breaking(self):
        index = self.build([
            record_for("identical vocabulary", key="tie-a"),
            record_for("identical vocabulary", key="tie-b"),
        ])
        results = index.search("identical vocabulary", top_k=2)
        self.assertEqual([item["chunk_id"] for item in results],
                         sorted(item["chunk_id"] for item in results))

    def test_11_arabic_tokenization(self):
        self.assertEqual(tokenize("مراقبة الأنظمة"), ["مراقبة", "الأنظمة"])

    def test_12_english_tokenization_casefolds(self):
        self.assertEqual(tokenize("CI Pipeline"), ["ci", "pipeline"])

    def test_13_mixed_language_tokenization(self):
        self.assertEqual(tokenize("تشغيل Kubernetes بأمان"), ["تشغيل", "kubernetes", "بأمان"])

    def test_14_nfkc_casefold_is_search_only(self):
        self.assertEqual(tokenize("ＡＢＣ Straße"), ["abc", "strasse"])

    def test_15_original_utf8_bytes_and_hash_are_preserved(self):
        content = "إجراء DevOps – إدارة الحاويات".encode("utf-8")
        record = record_for(content.decode("utf-8"), key="unicode")
        result = self.build([record]).search("إجراء")
        self.assertEqual(result[0]["content_sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(record["content_by_version"][record["manifest"]["document_versions"][0]["version_id"]], content)

    def test_16_term_frequency_contributes_to_bm25_score(self):
        index = self.build([
            record_for("signal", key="tf-one"),
            record_for("signal signal signal signal signal", key="tf-many"),
            record_for("background", key="tf-bg"),
        ])
        by_key = {chunk.document_key: chunk for chunk in index._chunks}
        self.assertGreater(index._score("signal", by_key["tf-many"]),
                           index._score("signal", by_key["tf-one"]))

    def test_17_document_frequency_counts_only_scoped_chunks(self):
        inside = record_for("common scoped term", key="df-inside")
        outside = record_for("common external term", key="df-outside", tenant="synthetic-tenant-002")
        index = self.build([inside, outside])
        self.assertEqual(index._document_frequency["common"], 1)
        self.assertEqual(index.statistics["document_count"], 1)

    def test_18_document_length_normalization_penalizes_longer_chunk(self):
        index = self.build([
            record_for("needle", key="len-short"),
            record_for("needle filler filler filler filler filler filler", key="len-long"),
            record_for("background filler", key="len-bg"),
        ])
        by_key = {chunk.document_key: chunk for chunk in index._chunks}
        self.assertGreater(index._score("needle", by_key["len-short"]),
                           index._score("needle", by_key["len-long"]))

    def test_19_duplicate_chunk_ids_are_rejected(self):
        record = record_for("chunk identity", key="dup-chunk")
        with self.assertRaisesRegex(RetrievalError, "duplicate_corpus_identifier"):
            self.build([record, copy.deepcopy(record)])

    def test_20_invalid_manifest_is_rejected(self):
        record = record_for("manifest verification", key="invalid-manifest")
        record["manifest"]["chunks"][0]["end_offset"] += 1
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_20a_unsupported_manifest_schema_is_rejected(self):
        record = record_for("unsupported schema", key="schema-invalid")
        record["manifest"]["schema_version"] = 2
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_21_invalid_content_hash_is_rejected(self):
        record = record_for("hash verification", key="invalid-hash")
        record["content_by_version"][record["manifest"]["document_versions"][0]["version_id"]] = b"wrong bytes"
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_22_missing_provenance_is_rejected(self):
        record = record_for("provenance required", key="no-provenance")
        del record["policy"]["provenance"]
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_23_unauthorized_pending_source_fails_closed(self):
        record = record_for("pending source", key="pending")
        record["policy"]["approval_status"] = "PENDING"
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_23a_unknown_policy_state_fails_closed(self):
        record = record_for("unknown policy state", key="unknown-policy")
        record["policy"]["approval_status"] = "UNDECIDED"
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_24_revoked_source_is_excluded(self):
        record = record_for("revoked source evidence", key="revoked", lifecycle="REVOKED")
        self.assertEqual(self.build([record]).search("revoked evidence"), [])

    def test_25_deleted_document_is_excluded(self):
        record = record_for("deleted source evidence", key="deleted", lifecycle="DELETED")
        self.assertEqual(self.build([record]).search("deleted evidence"), [])

    def test_26_tenant_scope_excludes_other_tenant(self):
        other = record_for("isolated tenant sentinel", key="tenant-two", tenant="synthetic-tenant-002")
        self.assertEqual(self.build([other]).search("sentinel"), [])

    def test_27_repository_scope_excludes_other_repository(self):
        other = record_for("isolated repository sentinel", key="repo-two", repository="synthetic-org/other")
        self.assertEqual(self.build([other]).search("sentinel"), [])

    def test_28_out_of_scope_records_do_not_change_statistics_or_score(self):
        inside = record_for("common target term", key="scope-base")
        outside = record_for("common common common distractor", key="scope-out", tenant="synthetic-tenant-002")
        base = self.build([inside]).search("common target")
        expanded = self.build([inside, outside]).search("common target")
        self.assertEqual(base, expanded)

    def test_29_missing_policy_is_rejected(self):
        record = record_for("missing policy", key="missing-policy")
        del record["policy"]
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_30_conflicting_scope_is_rejected(self):
        record = record_for("scope conflict", key="scope-conflict")
        record["policy"]["tenant_id"] = "synthetic-tenant-002"
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_31_results_have_valid_citation_fields_and_utf8_offsets(self):
        text = "مدخل Kubernetes آمن"
        record = record_for(text, key="citation", target_bytes=256)
        result = self.build([record]).search("Kubernetes")[0]
        self.assertEqual(result["offset_unit"], "UTF8_BYTE")
        matching_chunk = next(chunk for chunk in record["manifest"]["chunks"]
                              if chunk["chunk_id"] == result["chunk_id"])
        self.assertEqual(result["content_sha256"], matching_chunk["content_sha256"])
        self.assertEqual(result["start_offset"], 0)
        self.assertEqual(result["end_offset"], len(text.encode("utf-8")))
        self.assertTrue(result["provenance_reference"].startswith("synthetic-approval-"))

    def test_32_scores_are_finite_and_results_do_not_include_content(self):
        index = self.build([record_for("retrieved content remains hidden", key="no-content")])
        result = index.search("retrieved")[0]
        self.assertTrue(result["lexical_score"] > 0)
        self.assertNotIn("content", result)
        self.assertNotIn("text", result)

    def test_33_invalid_bm25_parameters_are_rejected(self):
        valid = record_for("parameter checks", key="params")
        for config in ({"k1": 0}, {"k1": float("nan")}, {"b": -0.1}, {"b": 1.1}, {"b": True}):
            with self.subTest(config=config), self.assertRaises(RetrievalError):
                self.build([valid], **config)

    def test_34_missing_lifecycle_state_fails_closed(self):
        record = record_for("lifecycle check", key="lifecycle-missing")
        del record["lifecycle_state"]
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_35_unknown_lifecycle_state_fails_closed(self):
        record = record_for("lifecycle unknown", key="lifecycle-unknown", lifecycle="UNKNOWN")
        with self.assertRaises(RetrievalError):
            self.build([record])

    def test_36_duplicate_document_ids_are_rejected(self):
        first = record_for("first revision", key="same-doc")
        second = record_for("second revision", key="same-doc")
        # Same policy/document identity with conflicting source bytes is not merged implicitly.
        second["policy"]["source_id"] = first["policy"]["source_id"]
        second["policy"]["source_uri"] = first["policy"]["source_uri"]
        with self.assertRaises(RetrievalError):
            self.build([first, second])

    def test_36a_only_latest_ki2_version_is_indexed(self):
        first = record_for("stale cobalt instruction", key="versioned")
        old_version = first["manifest"]["document_versions"][0]
        engine = KnowledgeIngestionEngine.from_manifest(first["manifest"])
        new_content = b"current amber instruction"
        latest = engine.ingest_document(
            source_policy=first["policy"],
            document_bytes=new_content,
            source_version="retrieval-v1",
            document_key="versioned",
            tenant_id="synthetic-tenant-001",
            repository_id="synthetic-org/synthetic-repo",
            content_type="text/plain; charset=utf-8",
            created_at="2026-11-28T00:00:00Z",
            chunking=ChunkingConfig(target_chunk_bytes=256),
        )
        new_version = latest.manifest["document_versions"][-1]
        first["manifest"] = latest.manifest
        first["content_by_version"][new_version["version_id"]] = new_content
        index = self.build([first])
        self.assertEqual(index.search("cobalt"), [])
        self.assertEqual(index.search("amber")[0]["version_id"], new_version["version_id"])
        self.assertNotEqual(old_version["version_id"], new_version["version_id"])

    def test_37_scope_is_required(self):
        with self.assertRaises(RetrievalError):
            build_index([], tenant_id="", repository_id="synthetic-org/repo")

    def test_38_tokenizer_keeps_combining_marks_and_does_not_stem_arabic(self):
        marked = tokenize("مُراقَبَة")
        self.assertEqual(len(marked), 1)
        self.assertTrue(any(unicodedata.category(char).startswith("M") for char in marked[0]))
        self.assertNotEqual(tokenize("المراقبة"), tokenize("يراقب"))

    def test_39_top_k_uses_configured_default_and_cap(self):
        index = self.build([record_for("alert signal", key=f"cap-{i}") for i in range(25)])
        self.assertEqual(len(index.search("alert", top_k=MAX_TOP_K)), MAX_TOP_K)

    def test_40_retrieval_has_no_network_dependency(self):
        with mock.patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            self.assertEqual(len(self.build([record_for("offline retrieval", key="offline")]).search("offline")), 1)

    def test_41_retrieval_does_not_open_files_for_writing(self):
        original_open = builtins.open

        def deny_writes(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                raise AssertionError("write attempted")
            return original_open(file, mode, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=deny_writes):
            self.assertTrue(self.build([record_for("read only retrieval", key="read-only")]).search("read"))

    def test_42_validation_errors_do_not_echo_sensitive_source_text(self):
        secret_marker = "SYNTHETIC_PRIVATE_SENTINEL_7654321"
        record = record_for(secret_marker, key="sanitized-error")
        record["content_by_version"][record["manifest"]["document_versions"][0]["version_id"]] = b"mismatch"
        with self.assertRaises(RetrievalError) as raised:
            self.build([record])
        self.assertNotIn(secret_marker, str(raised.exception))

    def test_43_corpus_record_limit_is_enforced_before_processing(self):
        with self.assertRaisesRegex(RetrievalError, "corpus_record_limit_exceeded"):
            self.build([{}] * (MAX_CORPUS_RECORDS + 1))

    def test_44_untrusted_document_content_remains_inert(self):
        record = record_for("__import__('os').system('touch /tmp/ki3-marker') inert text", key="inert")
        with mock.patch.object(os, "system") as system:
            result = self.build([record]).search("inert")
        system.assert_not_called()
        self.assertEqual(len(result), 1)

    def test_45_invalid_record_rejects_the_entire_index_without_partial_success(self):
        valid = record_for("valid scoped entry", key="batch-valid")
        invalid = record_for("invalid scoped entry", key="batch-invalid")
        invalid["manifest"]["chunks"][0]["content_sha256"] = "0" * 64
        with self.assertRaises(RetrievalError):
            self.build([valid, invalid])

    def test_46_arbitrary_nan_in_bm25_configuration_fails_closed(self):
        with self.assertRaises(RetrievalError):
            self.build([record_for("finite score", key="nan-score")], k1=float("inf"))

    def test_47_retrieval_scores_follow_the_documented_bm25_idf_formula(self):
        records = [
            record_for("signal signal", key="formula-a"),
            record_for("signal filler", key="formula-b"),
        ]
        index = self.build(records)
        result = index.search("signal", top_k=2)[0]
        chunk = next(item for item in index._chunks if item.chunk_id == result["chunk_id"])
        n = 2
        df = 2
        import math
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        tf = chunk.term_frequency["signal"]
        length_norm = 1 - index.b + index.b * len(chunk.terms) / index.statistics["average_document_length"]
        expected = idf * (tf * (index.k1 + 1)) / (tf + index.k1 * length_norm)
        self.assertAlmostEqual(result["lexical_score"], expected, places=12)

    def test_48_search_scores_only_chunks_from_the_inverted_index(self):
        index = self.build([
            record_for("Kubernetes readiness probe", key="posting-hit"),
            record_for("incident response evidence", key="posting-miss"),
        ])
        with mock.patch.object(index, "_score", wraps=index._score) as score:
            results = index.search("kubernetes")
        self.assertEqual(len(results), 1)
        self.assertEqual(score.call_count, 1)


if __name__ == "__main__":
    unittest.main()
