"""Offline, synthetic-only tests for the KI-1 manifest contract."""

import copy
import hashlib
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_knowledge_source_manifest import (  # noqa: E402
    ManifestValidationError,
    canonical_json_bytes,
    canonical_manifest_bytes,
    deterministic_id,
    load_and_validate,
    main,
    validate_manifest,
)

FIXTURES = ROOT / "tests" / "fixtures" / "knowledge"
VALID = FIXTURES / "source-manifest-valid.json"
INVALID = FIXTURES / "source-manifest-invalid.json"


def manifest():
    return json.loads(VALID.read_text(encoding="utf-8"))


def add_version(data, content, created_at, previous=None):
    source = data["sources"][0]
    raw = content.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    doc_id = data["document_versions"][0]["document_id"]
    version_id = deterministic_id("ver", {
        "schema_version": 1, "document_id": doc_id,
        "content_sha256": digest, "content_type": "text/plain; charset=utf-8",
    })
    version = {
        "document_id": doc_id, "document_key": "synthetic-note-001",
        "source_id": source["source_id"], "version_id": version_id,
        "content_sha256": digest, "content_type": "text/plain; charset=utf-8",
        "byte_size": len(raw), "created_at": created_at,
        "previous_version_id": previous, "synthetic_content": content,
    }
    data["document_versions"].append(version)
    chunk_id = deterministic_id("chunk", {
        "schema_version": 1, "version_id": version_id, "chunk_index": 0,
        "start_offset": 0, "end_offset": len(raw), "offset_unit": "UTF8_BYTE",
        "content_sha256": digest,
    })
    data["chunks"].append({
        "chunk_id": chunk_id, "document_id": doc_id, "version_id": version_id,
        "chunk_index": 0, "content_sha256": digest, "start_offset": 0,
        "end_offset": len(raw), "offset_unit": "UTF8_BYTE",
        "tenant_id": source["tenant_id"], "repository_id": source["repository_id"],
    })
    return version


class KnowledgeSourceManifestTests(unittest.TestCase):
    def assert_code(self, data, code):
        with self.assertRaises(ManifestValidationError) as raised:
            validate_manifest(data)
        self.assertEqual(raised.exception.code, code)

    def test_01_valid_synthetic_manifest_and_verified_fixture_bytes(self):
        report = validate_manifest(manifest())
        self.assertEqual(report["decision"], "PASS")
        self.assertEqual(report["content_integrity"], "VERIFIED_SYNTHETIC_BYTES")
        self.assertEqual(report["counts"], {"policies": 1, "sources": 1,
                         "document_versions": 1, "chunks": 1})

    def test_02_empty_manifest_is_rejected(self):
        self.assert_code({"schema_version": 1, "manifest_mode": "SYNTHETIC_OFFLINE",
                          "policies": [], "sources": [], "document_versions": [], "chunks": []},
                         "empty_manifest")

    def test_03_unsupported_schema_version_is_rejected(self):
        data = manifest(); data["schema_version"] = 2
        self.assert_code(data, "unsupported_schema")

    def test_04_duplicate_json_keys_are_rejected(self):
        self.assert_file_error(b'{"schema_version":1,"schema_version":1}', "duplicate_json_key")

    def test_05_duplicate_source_ids_are_rejected(self):
        data = manifest(); data["sources"].append(copy.deepcopy(data["sources"][0]))
        self.assert_code(data, "duplicate_source_id")

    def test_06_conflicting_duplicate_document_ids_are_rejected(self):
        data = manifest(); second = add_version(data, "different synthetic bytes", "2026-11-27T01:00:00Z",
                                                 data["document_versions"][0]["version_id"])
        second["document_key"] = "other-logical-document"
        self.assert_code(data, "duplicate_document_id")

    def test_07_duplicate_version_ids_within_document_are_rejected(self):
        data = manifest(); data["document_versions"].append(copy.deepcopy(data["document_versions"][0]))
        self.assert_code(data, "duplicate_version_id")

    def test_08_duplicate_chunk_ids_are_rejected(self):
        data = manifest(); data["chunks"].append(copy.deepcopy(data["chunks"][0]))
        self.assert_code(data, "duplicate_chunk_id")

    def test_09_missing_source_reference_is_rejected(self):
        data = manifest(); data["document_versions"][0]["source_id"] = "src_" + "0" * 64
        self.assert_code(data, "missing_source_reference")

    def test_10_missing_policy_reference_is_rejected(self):
        data = manifest(); data["sources"][0]["policy_reference"] = "absent-policy"
        self.assert_code(data, "missing_policy_reference")

    def test_11_missing_document_reference_is_rejected(self):
        data = manifest(); data["chunks"][0]["document_id"] = "doc_" + "0" * 64
        self.assert_code(data, "missing_document_reference")

    def test_12_missing_version_reference_is_rejected(self):
        data = manifest(); data["chunks"][0]["version_id"] = "ver_" + "0" * 64
        self.assert_code(data, "missing_version_reference")

    def test_13_invalid_sha256_format_is_rejected(self):
        data = manifest(); data["document_versions"][0]["content_sha256"] = "not-a-hash"
        self.assert_code(data, "invalid_content_sha256")

    def test_14_incorrect_fixture_content_hash_is_rejected(self):
        data = manifest(); data["document_versions"][0]["content_sha256"] = "0" * 64
        self.assert_code(data, "content_hash_mismatch")

    def test_15_negative_chunk_index_is_rejected(self):
        data = manifest(); data["chunks"][0]["chunk_index"] = -1
        self.assert_code(data, "invalid_chunk_index")

    def test_16_invalid_chunk_boundaries_are_rejected(self):
        data = manifest(); data["chunks"][0]["end_offset"] += 1
        self.assert_code(data, "invalid_chunk_boundaries")

    def test_17_inconsistent_offset_units_are_rejected(self):
        data = manifest(); data["chunks"][0]["offset_unit"] = "UNICODE_CODE_POINT"
        self.assert_code(data, "invalid_offset_unit")

    def test_18_duplicate_chunk_positions_are_rejected(self):
        data = manifest(); chunk = copy.deepcopy(data["chunks"][0])
        raw = data["document_versions"][0]["synthetic_content"].encode("utf-8")
        start = len("عينة".encode("utf-8"))
        chunk["start_offset"] = start; chunk["end_offset"] = len(raw)
        chunk["content_sha256"] = hashlib.sha256(raw[start:]).hexdigest()
        chunk["chunk_id"] = deterministic_id("chunk", {"schema_version": 1,
            "version_id": chunk["version_id"], "chunk_index": 0, "start_offset": start,
            "end_offset": len(raw), "offset_unit": "UTF8_BYTE",
            "content_sha256": chunk["content_sha256"]})
        data["chunks"].append(chunk)
        self.assert_code(data, "duplicate_chunk_position")

    def test_19_cross_tenant_scope_mismatch_is_rejected(self):
        data = manifest(); data["chunks"][0]["tenant_id"] = "other-tenant"
        self.assert_code(data, "tenant_scope_mismatch")

    def test_20_cross_repository_scope_mismatch_is_rejected(self):
        data = manifest(); data["chunks"][0]["repository_id"] = "other/repository"
        self.assert_code(data, "repository_scope_mismatch")

    def test_21_unauthorized_policy_fails_closed(self):
        data = manifest(); data["policies"][0]["approval_status"] = "PENDING"
        data["policies"][0]["ingestion_authorized"] = False
        self.assert_code(data, "source_policy_invalid")

    def test_22_revoked_source_fails_closed(self):
        data = manifest(); data["sources"][0]["source_status"] = "REVOKED"
        self.assert_code(data, "source_not_active")

    def test_23_cyclic_version_relationship_is_rejected(self):
        data = manifest(); second = add_version(data, "new synthetic revision", "2026-11-27T01:00:00Z",
                                                 data["document_versions"][0]["version_id"])
        data["document_versions"][0]["previous_version_id"] = second["version_id"]
        self.assert_code(data, "cyclic_version_relationship")

    def test_24_missing_previous_version_is_rejected(self):
        data = manifest(); add_version(data, "new synthetic revision", "2026-11-27T01:00:00Z",
                                       "ver_" + "0" * 64)
        self.assert_code(data, "missing_previous_version")

    def test_25_oversized_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"; path.write_bytes(b" " * (1_048_577))
            with self.assertRaises(ManifestValidationError) as raised: load_and_validate(path)
        self.assertEqual(raised.exception.code, "input_too_large")

    def test_26_excessive_record_count_is_rejected(self):
        data = manifest(); data["sources"] *= 101
        self.assert_code(data, "record_limit_exceeded")

    def test_27_malformed_json_is_rejected(self):
        self.assert_file_error(b'{"schema_version":', "malformed_json")

    def test_28_deterministic_identifiers(self):
        value = {"tenant_id": "t", "source_id": "s"}
        self.assertEqual(deterministic_id("doc", value), deterministic_id("doc", value))
        self.assertTrue(deterministic_id("doc", value).startswith("doc_"))

    def test_29_canonical_serialization_ignores_mapping_insertion_order(self):
        data = manifest()
        add_version(data, "new synthetic revision", "2026-11-27T01:00:00Z",
                    data["document_versions"][0]["version_id"])
        reordered = copy.deepcopy(data)
        for key in ("policies", "sources", "document_versions", "chunks"):
            reordered[key].reverse()
        self.assertEqual(canonical_manifest_bytes(data), canonical_manifest_bytes(reordered))
        self.assertEqual(validate_manifest(data)["manifest_sha256"],
                         validate_manifest(reordered)["manifest_sha256"])

    def test_multi_version_manifest_is_valid_when_chain_is_ordered(self):
        data = manifest()
        add_version(data, "new synthetic revision", "2026-11-27T01:00:00Z",
                    data["document_versions"][0]["version_id"])
        self.assertEqual(validate_manifest(data)["counts"]["document_versions"], 2)

    def test_branched_version_history_is_rejected(self):
        data = manifest(); root_id = data["document_versions"][0]["version_id"]
        add_version(data, "revision two", "2026-11-27T01:00:00Z", root_id)
        add_version(data, "revision three", "2026-11-27T02:00:00Z", root_id)
        self.assert_code(data, "branched_version_history")

    def test_30_unicode_offsets_are_utf8_bytes(self):
        data = manifest(); version = data["document_versions"][0]
        raw = version["synthetic_content"].encode("utf-8")
        self.assertGreater(len(raw), len(version["synthetic_content"]))
        self.assertEqual(data["chunks"][0]["end_offset"], len(raw))
        self.assertEqual(validate_manifest(data)["decision"], "PASS")

    def test_31_validation_errors_do_not_echo_payload(self):
        data = manifest(); marker = "SYNTHETIC_CANARY_PRIVATE_71ab"
        data["document_versions"][0]["synthetic_content"] = marker
        data["document_versions"][0]["content_sha256"] = "bad"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"; path.write_text(json.dumps(data), encoding="utf-8")
            output = self.run_cli(path)
        self.assertNotIn(marker, output)

    def test_32_invalid_cli_input_returns_nonzero(self):
        self.assertNotEqual(self.run_main(INVALID), 0)

    def test_33_validation_has_no_external_network_dependency(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("network")):
            self.assertEqual(validate_manifest(manifest())["decision"], "PASS")

    def test_34_integrity_report_does_not_claim_authenticity(self):
        report = validate_manifest(manifest())
        self.assertEqual(report["content_integrity"], "VERIFIED_SYNTHETIC_BYTES")
        self.assertEqual(report["authorization_assurance"], "STRUCTURE_ONLY")

    def test_content_integrity_is_unverified_when_fixture_bytes_are_absent(self):
        data = manifest(); data["document_versions"][0].pop("synthetic_content")
        report = validate_manifest(data)
        self.assertEqual(report["content_integrity"], "UNVERIFIED_NO_CONTENT_BYTES")

    def test_policy_source_digest_must_match_initial_document_version(self):
        data = manifest(); data["policies"][0]["content_sha256"] = "0" * 64
        self.assert_code(data, "policy_content_hash_mismatch")

    def test_source_policy_scope_conflict_is_rejected(self):
        data = manifest(); data["sources"][0]["tenant_id"] = "other-tenant"
        self.assert_code(data, "tenant_scope_mismatch")

    def test_source_repository_scope_conflict_is_rejected(self):
        data = manifest(); data["sources"][0]["repository_id"] = "other/repository"
        self.assert_code(data, "repository_scope_mismatch")

    def test_non_synthetic_source_type_is_not_supported(self):
        data = manifest(); policy = data["policies"][0]
        policy.update({"source_type": "public_repository_file", "source_uri": "repo:/README.md",
                       "classification": "PUBLIC", "license_status": "PERMISSIVE",
                       "retention_policy": {"mode": "SOURCE_RIGHTS", "max_age_seconds": 86400},
                       "deletion_policy": "DELETE_ON_REVOCATION"})
        data["sources"][0]["source_type"] = "public_repository_file"
        self.assert_code(data, "non_synthetic_source_not_supported")

    def test_schema_drift_fails_closed_against_runtime_contract(self):
        schema_path = ROOT / "schemas" / "knowledge-source-manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["$defs"]["chunk"]["required"].remove("tenant_id")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schema.json"
            path.write_text(json.dumps(schema), encoding="utf-8")
            with patch("scripts.check_knowledge_source_manifest.SCHEMA_PATH", path):
                self.assert_code(manifest(), "schema_invalid")

    def test_35_utf8_offsets_cannot_split_a_code_point(self):
        data = manifest(); data["chunks"][0]["start_offset"] = 1
        self.assert_code(data, "invalid_utf8_boundary")

    def test_36_unknown_policy_schema_fails_closed(self):
        data = manifest(); data["policies"][0]["schema_version"] = 2
        self.assert_code(data, "source_policy_invalid")

    def test_37_deeply_nested_json_is_rejected_safely(self):
        self.assert_file_error(("[" * 40 + "0" + "]" * 40).encode(), "nesting_too_deep")

    def test_created_at_requires_timezone_aware_rfc3339_shape(self):
        data = manifest(); data["document_versions"][0]["created_at"] = "2026-11-27 00:00:00+00:00"
        self.assert_code(data, "invalid_created_at")

    def assert_file_error(self, raw, code):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"; path.write_bytes(raw)
            with self.assertRaises(ManifestValidationError) as raised: load_and_validate(path)
        self.assertEqual(raised.exception.code, code)

    def run_cli(self, path):
        from contextlib import redirect_stdout
        from io import StringIO
        stream = StringIO()
        with redirect_stdout(stream): main(["--input", str(path)])
        return stream.getvalue()

    def run_main(self, path):
        from contextlib import redirect_stdout
        from io import StringIO
        stream = StringIO()
        with redirect_stdout(stream): result = main(["--input", str(path)])
        return result


if __name__ == "__main__":
    unittest.main()
