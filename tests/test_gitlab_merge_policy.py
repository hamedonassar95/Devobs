"""Offline behavior tests for MR-only merge policy classification."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gitlab_merge_policy as policy  # noqa: E402


class GitLabMergePolicyTests(unittest.TestCase):
    def data(self, **changes):
        valid = {"id": 89037773, "path_with_namespace": "hamedonassar95/Devobs",
                 "visibility": "public", "default_branch": "main", "merge_method": "ff"}
        valid.update(changes)
        return json.dumps(valid).encode("utf-8")

    def test_ff_is_only_review_required_not_sync_success(self):
        result, code = policy.audit(self.data())
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["mr_path"], "FF_MR_POLICY_ONLY")
        self.assertEqual(result["direct_git_push"], "NOT_EVALUATED")
        self.assertTrue(result["approval_required_for_replica_transfer"])
        self.assertFalse(result["write_performed"])
        self.assertFalse(result["gitlab_pipeline_started"])

    def test_merge_commit_blocks_only_mr_sha_identity_not_direct_push(self):
        result, code = policy.audit(self.data(merge_method="merge"))
        self.assertEqual((result["status"], code), ("REVIEW_REQUIRED", 0))
        self.assertEqual(result["mr_path"], "MR_ADDS_COMMIT")
        self.assertEqual(result["direct_git_push"], "NOT_EVALUATED")
        self.assertTrue(result["approval_required_for_replica_transfer"])
        self.assertFalse(result["write_performed"])

    def test_semilinear_mode_blocks_only_mr_sha_identity(self):
        result, code = policy.audit(self.data(merge_method="rebase_merge"))
        self.assertEqual((result["status"], code), ("REVIEW_REQUIRED", 0))
        self.assertEqual(result["mr_path"], "MR_ADDS_COMMIT")
        self.assertEqual(result["direct_git_push"], "NOT_EVALUATED")

    def test_mismatched_project_is_not_accepted(self):
        for bad in (self.data(id=13), self.data(path_with_namespace="other/project"),
                    self.data(default_branch="dev"), self.data(visibility="private")):
            with self.subTest(bad=bad):
                result, code = policy.audit(bad)
                self.assertEqual((result["status"], code), ("BLOCKED", 2))

    def test_unknown_merge_method_fails_closed(self):
        result, code = policy.audit(self.data(merge_method="unknown"))
        self.assertEqual((result["status"], code), ("BLOCKED", 2))

    def test_html_and_invalid_utf8_fail_closed(self):
        for raw in (b"<html>not JSON</html>", b"\xff", b"", b"[]", b"null"):
            with self.subTest(raw=raw):
                self.assertEqual(policy.audit(raw)[1], 2)

    def test_oversized_response_fails_closed(self):
        self.assertEqual(policy.audit(b"x" * (policy.MAX_RESPONSE + 1))[1], 2)

    def test_unknown_fields_do_not_leak_in_output(self):
        result, code = policy.audit(self.data(private_key="FAKE_SECRET"))
        self.assertEqual(code, 0)
        self.assertNotIn("FAKE_SECRET", json.dumps(result))

    def test_http_error_is_sanitized(self):
        with patch.object(policy, "load_public_project", side_effect=OSError("FAKE_SECRET")):
            from io import StringIO
            import contextlib
            output = StringIO()
            with contextlib.redirect_stdout(output):
                code = policy.main()
        self.assertEqual(code, 2)
        self.assertNotIn("FAKE_SECRET", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["reason"], "public_metadata_unavailable")

    def test_actual_provider_is_never_called_from_unit_test(self):
        with patch.object(policy, "load_public_project", return_value=self.data()):
            self.assertEqual(policy.main(), 0)


    def test_missing_identity_fields_name_the_exact_field(self):
        for field in ("id", "path_with_namespace", "default_branch", "visibility"):
            payload = json.loads(self.data())
            del payload[field]
            with self.subTest(field=field):
                result, code = policy.audit(json.dumps(payload).encode())
                self.assertEqual((result["status"], code), ("BLOCKED", 2))
                self.assertEqual(result["reason"], f"missing_field:{field}")

    def test_missing_merge_method_is_never_defaulted(self):
        payload = json.loads(self.data())
        del payload["merge_method"]
        result, code = policy.audit(json.dumps(payload).encode())
        self.assertEqual((result["status"], code), ("BLOCKED", 2))
        self.assertEqual(result["reason"], "missing_field:merge_method")
        self.assertNotIn("mr_path", result)
        self.assertNotIn("approval_required_for_replica_transfer", result)

    def test_wrong_field_types_are_named(self):
        cases = (("id", "89037773"), ("path_with_namespace", 123),
                 ("default_branch", None), ("visibility", ["public"]),
                 ("merge_method", 5))
        for field, bad_value in cases:
            with self.subTest(field=field):
                result, code = policy.audit(self.data(**{field: bad_value}))
                self.assertEqual((result["status"], code), ("BLOCKED", 2))
                self.assertEqual(result["reason"], f"wrong_type:{field}")

    def test_mismatched_identity_names_the_exact_field(self):
        cases = (("id", 13), ("path_with_namespace", "other/project"),
                 ("default_branch", "dev"), ("visibility", "private"))
        for field, bad_value in cases:
            with self.subTest(field=field):
                result, code = policy.audit(self.data(**{field: bad_value}))
                self.assertEqual((result["status"], code), ("BLOCKED", 2))
                self.assertEqual(result["reason"], f"mismatched_field:{field}")

    def test_unsupported_merge_method_has_its_own_reason(self):
        for method in ("unknown", "", "ff ", "FF", "squash"):
            with self.subTest(method=method):
                result, code = policy.audit(self.data(merge_method=method))
                self.assertEqual((result["status"], code), ("BLOCKED", 2))
                self.assertEqual(result["reason"], "unsupported_merge_method")

    def test_malformed_responses_are_classified_without_echoing_content(self):
        cases = ((b"<html>FAKE_SECRET</html>", "invalid_json"),
                 (b"\xff", "invalid_json"),
                 (b'{"id": 1', "invalid_json"),
                 (b"[]", "invalid_payload"),
                 (b"null", "invalid_payload"),
                 (b'"text"', "invalid_payload"),
                 (b"", "invalid_payload"),
                 (b"x" * (policy.MAX_RESPONSE + 1), "response_too_large"))
        for raw, expected in cases:
            with self.subTest(expected=expected):
                result, code = policy.audit(raw)
                self.assertEqual((result["status"], code), ("BLOCKED", 2))
                self.assertEqual(result["reason"], expected)
                self.assertNotIn("FAKE_SECRET", json.dumps(result))

    def test_reason_tokens_never_reflect_provider_values(self):
        sentinel = "FAKE_SECRET_VALUE"
        result, code = policy.audit(self.data(path_with_namespace=sentinel))
        self.assertEqual((result["status"], code), ("BLOCKED", 2))
        self.assertEqual(result["reason"], "mismatched_field:path_with_namespace")
        self.assertNotIn(sentinel, json.dumps(result))

    def test_main_prints_the_specific_reason_and_exits_two(self):
        payload = json.loads(self.data())
        del payload["merge_method"]
        with patch.object(policy, "load_public_project",
                          return_value=json.dumps(payload).encode("utf-8")):
            from io import StringIO
            import contextlib
            output = StringIO()
            with contextlib.redirect_stdout(output):
                code = policy.main()
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["reason"],
                         "missing_field:merge_method")


if __name__ == "__main__":
    unittest.main()
