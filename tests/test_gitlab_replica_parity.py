"""Behavioral, offline tests for the token-free public branch SHA parity probe."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_gitlab_replica_parity as probe  # noqa: E402


class _Headers:
    def __init__(self, content_type="application/json"):
        self.content_type = content_type

    def get_content_type(self):
        return self.content_type


class _Response:
    status = 200

    def __init__(self, *, url=probe.GITHUB_BRANCH_URL, content=b'{}', status=200,
                 content_type="application/json"):
        self.url = url
        self.content = content
        self.status = status
        self.headers = _Headers(content_type)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self):
        return self.url

    def read(self, length):
        return self.content[:length]


class GitLabReplicaParityTests(unittest.TestCase):
    def setUp(self):
        self.github_sha = "a" * 40
        self.gitlab_sha = "b" * 40

    def _fetch(self, gitlab_sha):
        def fetch(url):
            if url == probe.GITHUB_BRANCH_URL:
                return {"name": "main", "commit": {"sha": self.github_sha}}
            if url == probe.GITLAB_BRANCH_URL:
                return {"name": "main", "commit": {"id": gitlab_sha}}
            self.fail("Unexpected URL")
        return fetch

    def test_identical_shas_match(self):
        result = probe.check_parity(fetcher=self._fetch(self.github_sha))
        self.assertEqual(result, {"status": "MATCH", "github_sha": self.github_sha,
                                  "gitlab_sha": self.github_sha})

    def test_different_shas_report_drift_not_success(self):
        result = probe.check_parity(fetcher=self._fetch(self.gitlab_sha))
        self.assertEqual(result["status"], "DRIFT")
        self.assertEqual(result["gitlab_sha"], self.gitlab_sha)

    def test_missing_or_invalid_branch_metadata_fails_closed(self):
        for invalid in (None, [], {}, {"name": "other", "commit": {"sha": self.github_sha}},
                        {"name": "main"}, {"name": "main", "commit": {"sha": "a" * 39}},
                        {"name": "main", "commit": {"sha": "A" * 40}},
                        {"name": "main", "commit": {"sha": 5}}):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(probe.ParityError, "github_invalid_response"):
                    probe.check_parity(fetcher=lambda _url: invalid)

    def test_gitlab_invalid_sha_rejected(self):
        with self.assertRaisesRegex(probe.ParityError, "gitlab_invalid_response"):
            probe.check_parity(fetcher=self._fetch("unexpected_sha"))

    def test_no_fetch_of_second_provider_after_first_failure(self):
        seen = []
        def bad_fetch(url):
            seen.append(url)
            raise probe.ParityError("github_unavailable")
        with self.assertRaises(probe.ParityError):
            probe.check_parity(fetcher=bad_fetch)
        self.assertEqual(seen, [probe.GITHUB_BRANCH_URL])

    def test_fetch_is_fixed_https_get_without_credential_headers(self):
        response = _Response(content=json.dumps({"name": "main"}).encode())
        opener = Mock()
        opener.open.return_value = response
        with patch.object(probe, "build_opener", return_value=opener) as factory:
            result = probe._get_json(probe.GITHUB_BRANCH_URL)
        self.assertEqual(result, {"name": "main"})
        self.assertIsInstance(factory.call_args.args[0], probe._RejectRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, probe.GITHUB_BRANCH_URL)
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.data)
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 10)
        self.assertEqual(set(k.lower() for k in request.headers), {"accept", "user-agent"})
        self.assertIsNone(probe._RejectRedirect().redirect_request(None, None, 302, "", {}, "https://attacker.invalid"))

    def test_other_host_or_path_rejected_before_network(self):
        with patch.object(probe, "build_opener") as opener:
            for url in ("https://example.org", "http://gitlab.com/api/v4/projects/89037773/repository/branches/main",
                        "https://gitlab.com/api/v4/projects/89037773/repository/branches/other"):
                with self.assertRaisesRegex(probe.ParityError, "invalid_endpoint"):
                    probe._get_json(url)
            opener.assert_not_called()

    def test_redirect_or_non_200_response_fails_closed(self):
        for status, url in ((302, probe.GITHUB_BRANCH_URL), (200, "https://elsewhere.invalid")):
            response = _Response(status=status, url=url)
            opener = Mock()
            opener.open.return_value = response
            with self.subTest(status=status, url=url), patch.object(probe, "build_opener", return_value=opener):
                with self.assertRaisesRegex(probe.ParityError, "github_invalid_response"):
                    probe._get_json(probe.GITHUB_BRANCH_URL)

    def test_http_error_body_is_not_exposed(self):
        sentinel = "SYNTHETIC_PRIVATE_ERROR_BODY"
        opener = Mock()
        opener.open.side_effect = HTTPError(probe.GITHUB_BRANCH_URL, 403, sentinel, None, None)
        with patch.object(probe, "build_opener", return_value=opener):
            with self.assertRaises(probe.ParityError) as captured:
                probe._get_json(probe.GITHUB_BRANCH_URL)
        self.assertEqual(str(captured.exception), "github_unavailable")
        self.assertNotIn(sentinel, str(captured.exception))

    def test_bad_content_type_rejected(self):
        response = _Response(content_type="text/html")
        opener = Mock(open=Mock(return_value=response))
        with patch.object(probe, "build_opener", return_value=opener):
            with self.assertRaisesRegex(probe.ParityError, "github_invalid_response"):
                probe._get_json(probe.GITHUB_BRANCH_URL)

    def test_oversized_and_invalid_json_are_rejected(self):
        for content in (b"x" * (probe.MAX_RESPONSE_BYTES + 1), b"{", b"\xff"):
            opener = Mock(open=Mock(return_value=_Response(content=content)))
            with self.subTest(content_len=len(content)), patch.object(probe, "build_opener", return_value=opener):
                with self.assertRaisesRegex(probe.ParityError, "github_invalid_response"):
                    probe._get_json(probe.GITHUB_BRANCH_URL)

    def test_cli_returns_fail_closed_code_for_mismatch(self):
        output = StringIO()
        with patch.object(probe, "check_parity", return_value=probe.check_parity(self._fetch(self.gitlab_sha))):
            with redirect_stdout(output):
                code = probe.main(["--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "DRIFT")

    def test_cli_returns_success_only_for_match(self):
        output = StringIO()
        with patch.object(probe, "check_parity", return_value=probe.check_parity(self._fetch(self.github_sha))):
            with redirect_stdout(output):
                code = probe.main(["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "MATCH")

    def test_cli_unknown_has_no_raw_error(self):
        output = StringIO()
        with patch.object(probe, "check_parity", side_effect=RuntimeError("PRIVATE_PROVIDER_DETAILS")):
            with redirect_stdout(output):
                code = probe.main(["--json"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue()), {"status": "UNKNOWN", "error": "unexpected_failure"})
        self.assertNotIn("PRIVATE_PROVIDER_DETAILS", output.getvalue())


if __name__ == "__main__":
    unittest.main()
