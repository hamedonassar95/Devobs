"""Offline behavior tests for the GitLab fast-forward-only merge policy gate."""
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
        self.assertTrue(result["approval_required_for_replica_transfer"])
        self.assertFalse(result["write_performed"])
        self.assertFalse(result["gitlab_pipeline_started"])

    def test_merge_commit_mode_blocks(self):
        result, code = policy.audit(self.data(merge_method="merge"))
        self.assertEqual((result["status"], code), ("BLOCKED", 2))
        self.assertEqual(result["reason"], "merge_method_creates_merge_commit")

    def test_semilinear_mode_also_blocks(self):
        result, code = policy.audit(self.data(merge_method="rebase_merge"))
        self.assertEqual((result["status"], code), ("BLOCKED", 2))

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


if __name__ == "__main__":
    unittest.main()
