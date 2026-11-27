"""Offline synthetic tests for the KI-0 source-policy validator."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_knowledge_source_policy import (
    PolicyValidationError,
    load_and_validate,
    main,
    validate_policy,
)


ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/fixtures/knowledge/source-policy-valid.json"
INVALID = ROOT / "tests/fixtures/knowledge/source-policy-invalid.json"


def fixture() -> dict:
    return json.loads(VALID.read_text(encoding="utf-8"))


class KnowledgeSourcePolicyTests(unittest.TestCase):
    def assert_policy_error(self, policy: dict, code: str) -> None:
        with self.assertRaises(PolicyValidationError) as raised:
            validate_policy(policy)
        self.assertEqual(raised.exception.code, code)

    def test_approved_synthetic_policy_is_structure_only_valid(self):
        report = load_and_validate(VALID)
        self.assertEqual(report["decision"], "PASS")
        self.assertEqual(report["assurance"], "STRUCTURE_ONLY")
        self.assertEqual(report["schema_version"], 1)

    def test_missing_source_identifier_is_rejected(self):
        policy = fixture()
        del policy["source_id"]
        self.assert_policy_error(policy, "invalid_fields")

    def test_missing_tenant_identifier_is_rejected(self):
        policy = fixture()
        del policy["tenant_id"]
        self.assert_policy_error(policy, "invalid_fields")

    def test_missing_repository_scope_is_rejected(self):
        policy = fixture()
        del policy["repository_id"]
        self.assert_policy_error(policy, "invalid_fields")

    def test_unsupported_schema_version_is_rejected(self):
        policy = fixture()
        policy["schema_version"] = 2
        self.assert_policy_error(policy, "unsupported_schema")

    def test_boolean_is_not_accepted_as_schema_version(self):
        policy = fixture()
        policy["schema_version"] = True
        self.assert_policy_error(policy, "unsupported_schema")

    def test_invalid_classification_is_rejected(self):
        policy = fixture()
        policy["classification"] = "TOP_SECRET"
        self.assert_policy_error(policy, "invalid_classification")

    def test_unhashable_values_fail_with_fixed_errors(self):
        cases = (
            ("source_type", [], "invalid_source_type"),
            ("classification", {}, "invalid_classification"),
            ("license_status", [], "invalid_license_status"),
            ("approval_status", [], "invalid_approval_status"),
            ("deletion_policy", {}, "invalid_deletion_policy"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                policy = fixture()
                policy[field] = value
                self.assert_policy_error(policy, code)

        policy = fixture()
        policy["retention_policy"]["mode"] = []
        self.assert_policy_error(policy, "invalid_retention_policy")

    def test_unknown_license_status_is_rejected(self):
        policy = fixture()
        policy["license_status"] = "UNKNOWN_LICENSE"
        self.assert_policy_error(policy, "invalid_license_status")

    def test_pending_authorization_fails_closed(self):
        policy = fixture()
        policy["approval_status"] = "PENDING"
        policy["ingestion_authorized"] = False
        self.assert_policy_error(policy, "authorization_pending")

    def test_denied_authorization_fails_closed(self):
        policy = fixture()
        policy["approval_status"] = "DENIED"
        policy["ingestion_authorized"] = False
        self.assert_policy_error(policy, "authorization_denied")

    def test_unknown_authorization_fails_closed(self):
        policy = fixture()
        policy["approval_status"] = "UNKNOWN"
        policy["ingestion_authorized"] = False
        self.assert_policy_error(policy, "authorization_unknown")

    def test_unrecognized_authorization_state_is_rejected(self):
        policy = fixture()
        policy["approval_status"] = "AUTO_APPROVED"
        self.assert_policy_error(policy, "invalid_approval_status")

    def test_malformed_content_hash_is_rejected(self):
        policy = fixture()
        policy["content_sha256"] = "abc123"
        self.assert_policy_error(policy, "invalid_content_sha256")

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(PolicyValidationError) as raised:
                load_and_validate(path)
        self.assertEqual(raised.exception.code, "duplicate_json_key")

    def test_malformed_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.json"
            path.write_text('{"schema_version":', encoding="utf-8")
            with self.assertRaises(PolicyValidationError) as raised:
                load_and_validate(path)
        self.assertEqual(raised.exception.code, "malformed_json")

    def test_oversized_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b" " * (16_385))
            with self.assertRaises(PolicyValidationError) as raised:
                load_and_validate(path)
        self.assertEqual(raised.exception.code, "input_too_large")

    def test_invalid_retention_configuration_is_rejected(self):
        policy = fixture()
        policy["retention_policy"]["max_age_seconds"] = 0
        self.assert_policy_error(policy, "invalid_retention_policy")

    def test_unauthorized_ingestion_is_rejected_as_conflict(self):
        policy = fixture()
        policy["ingestion_authorized"] = False
        self.assert_policy_error(policy, "authorization_conflict")

    def test_conflicting_approval_and_ingestion_states_are_rejected(self):
        policy = fixture()
        policy["approval_status"] = "PENDING"
        self.assert_policy_error(policy, "authorization_pending")

    def test_approved_but_disabled_ingestion_is_rejected_as_conflict(self):
        policy = fixture()
        policy["ingestion_authorized"] = "yes"
        self.assert_policy_error(policy, "invalid_ingestion_authorization")

    def test_source_type_classification_license_and_retention_must_match(self):
        policy = fixture()
        policy["classification"] = "PUBLIC"
        self.assert_policy_error(policy, "incompatible_policy_combination")

    def test_restricted_classification_is_not_ingestable_in_v1(self):
        policy = fixture()
        policy["classification"] = "RESTRICTED"
        self.assert_policy_error(policy, "restricted_source_not_supported")

    def test_deterministic_validation_output(self):
        outputs = []
        for _ in range(2):
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                result = main(["--input", str(VALID)])
            self.assertEqual(result, 0)
            outputs.append(stream.getvalue())
        self.assertEqual(outputs[0], outputs[1])

    def test_invalid_cli_input_returns_nonzero(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            result = main(["--input", str(INVALID)])
        self.assertNotEqual(result, 0)
        self.assertEqual(json.loads(stream.getvalue())["decision"], "FAIL")

    def test_errors_never_echo_sensitive_source_values(self):
        policy = fixture()
        marker = "SYNTHETIC_PRIVATE_CANARY_4d7a"
        policy["source_uri"] = f"https://example.invalid/path?token={marker}"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe-uri.json"
            path.write_text(json.dumps(policy), encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = main(["--input", str(path)])
        self.assertNotEqual(result, 0)
        self.assertNotIn(marker, stdout.getvalue() + stderr.getvalue())

    def test_validation_does_not_attempt_network_access(self):
        with (patch.object(socket, "create_connection", side_effect=AssertionError("network")) as connect,
              patch.object(socket, "socket", side_effect=AssertionError("network")) as socket_factory):
            report = load_and_validate(VALID)
        self.assertEqual(report["decision"], "PASS")
        connect.assert_not_called()
        socket_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
