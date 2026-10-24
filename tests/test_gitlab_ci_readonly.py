"""Behavioral tests for the bounded GitLab CI reader; no network is used."""

import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gitlab_ci_readonly as audit  # noqa: E402

SENTINEL = "PRIVATE_PROJECT_NAME_AND_SECRET"


class GitLabReadOnlyTests(unittest.TestCase):
    def test_success_queries_three_bounded_get_endpoints_per_project(self):
        paths = []

        def fake_fetch(path, token):
            self.assertEqual(token, "test-token")
            paths.append(path)
            if path == "projects/42":
                return {"id": 42, "default_branch": "main", "name": SENTINEL}
            if path == "projects/42/repository/branches/main":
                return {"name": "main", "commit": {"id": "a" * 40}}
            if path == "projects/42/pipelines?ref=main&per_page=1&order_by=id&sort=desc":
                return [{"id": 101, "project_id": 42, "ref": "main", "sha": "a" * 40, "status": "success"}]
            self.fail("Unexpected GitLab endpoint")

        result = audit.audit_projects(["42"], "test-token", fetcher=fake_fetch)
        self.assertEqual(result, {"schema_version": 1, "all_passed": True,
                                  "results": [{"slot": 1, "pipeline_state": "success"}]})
        self.assertEqual(len(paths), 3)
        self.assertNotIn(SENTINEL, json.dumps(result))
        self.assertNotIn("42", json.dumps(result))

    def test_missing_pipeline_is_not_success(self):
        def fake_fetch(path, token):
            if "pipelines" in path:
                return []
            if "repository/branches" in path:
                return {"name": "main", "commit": {"id": "a" * 40}}
            return {"id": 42, "default_branch": "main"}

        result = audit.audit_projects(["42"], "test-token", fetcher=fake_fetch)
        self.assertEqual(result["results"][0]["pipeline_state"], "missing")
        self.assertFalse(result["all_passed"])

    def test_stale_success_is_not_passed(self):
        def fake_fetch(path, token):
            if "pipelines" in path:
                return [{"project_id": 42, "ref": "main", "sha": "b" * 40, "status": "success"}]
            if "branches" in path:
                return {"name": "main", "commit": {"id": "a" * 40}}
            return {"id": 42, "default_branch": "main"}

        result = audit.audit_projects(["42"], "test-token", fetcher=fake_fetch)
        self.assertEqual(result["results"][0]["pipeline_state"], "stale")
        self.assertFalse(result["all_passed"])

    def test_invalid_ids_rejected_without_request(self):
        fetch = mock.Mock()
        for ids in (["-1"], ["42", "42"], ["../../a"], ["42"] * 11, []):
            with self.subTest(ids=ids), self.assertRaises(audit.AuditError):
                audit.audit_projects(ids, "test-token", fetcher=fetch)
        fetch.assert_not_called()

    def test_response_project_mismatch_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.audit_projects(["42"], "test-token", fetcher=lambda path, token:
                                 {"id": 99, "default_branch": "main"})

    def test_transport_errors_do_not_leak_error_details(self):
        with mock.patch.dict(os.environ, {"GITLAB_PROJECT_IDS": "42", "GITLAB_READONLY_TOKEN": SENTINEL}):
            with mock.patch.object(audit, "_get_json", side_effect=OSError(SENTINEL)):
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = audit.main()
        self.assertNotEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(SENTINEL, stderr.getvalue())

    def test_http_layer_is_fixed_https_get_and_does_not_echo_token(self):
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def geturl(self):
                return "https://gitlab.com/api/v4/projects/42"
            def read(self, limit):
                return b'{"id":42}'

        opener = mock.Mock()
        opener.open.return_value = Response()
        with mock.patch.object(audit, "build_opener", return_value=opener) as factory:
            result = audit._get_json("projects/42", SENTINEL)
        self.assertEqual(result, {"id": 42})
        self.assertIsInstance(factory.call_args.args[0], audit._NoRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://gitlab.com/api/v4/projects/42")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.data, None)
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 10)
        self.assertIsNone(audit._NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.org"))

    def test_http_response_over_limit_is_rejected(self):
        class LargeResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def geturl(self):
                return "https://gitlab.com/api/v4/projects/42"
            def read(self, limit):
                return b"a" * limit

        opener = mock.Mock()
        opener.open.return_value = LargeResponse()
        with mock.patch.object(audit, "build_opener", return_value=opener):
            with self.assertRaisesRegex(audit.AuditError, "oversized_response"):
                audit._get_json("projects/42", "test-token")

    def test_missing_token_fails_closed(self):
        with mock.patch.dict(os.environ, {"GITLAB_PROJECT_IDS": "42"}, clear=True):
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = audit.main()
        self.assertNotEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
