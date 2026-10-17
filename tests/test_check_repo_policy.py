"""Tests for the read-only GitHub repository policy audit."""

from __future__ import annotations

import os
import tempfile
import unittest
import urllib.error
import urllib.request
from unittest import mock

from scripts.check_repo_policy import (
    PolicyCheckError,
    audit_repository,
    get_json,
    write_step_summary,
)


def api_fixtures() -> dict[str, object]:
    repository = "hamedonassar95/Devobs"
    root = f"repos/{repository}"
    return {
        root: {"default_branch": "main"},
        f"{root}/branches/main": {"protected": True},
        f"{root}/rulesets?includes_parents=true": [
            {"id": 24507159, "name": "Protect main"}
        ],
        f"{root}/rulesets/24507159": {
            "name": "Protect main",
            "target": "branch",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "bypass_actors": [],
            "rules": [
                {"type": "deletion"},
                {"type": "non_fast_forward"},
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": True,
                        "required_status_checks": [{"context": "validate"}],
                    },
                },
                {"type": "pull_request", "parameters": {"required_approving_review_count": 0}},
                {
                    "type": "code_scanning",
                    "parameters": {
                        "code_scanning_tools": [
                            {
                                "tool": "CodeQL",
                                "security_alerts_threshold": "high_or_higher",
                                "alerts_threshold": "errors",
                            }
                        ]
                    },
                },
            ],
        },
    }


class RepositoryPolicyAuditTests(unittest.TestCase):
    def test_accepts_current_policy_shape(self) -> None:
        fixtures = api_fixtures()
        scope, findings = audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

        self.assertEqual(scope, "hamedonassar95/Devobs (default branch `main`)")
        self.assertEqual(findings, [])

    def test_reports_unprotected_default_branch_and_missing_check(self) -> None:
        fixtures = api_fixtures()
        fixtures["repos/hamedonassar95/Devobs/branches/main"] = {"protected": False}
        ruleset = fixtures["repos/hamedonassar95/Devobs/rulesets/24507159"]
        assert isinstance(ruleset, dict)
        rules = ruleset["rules"]
        assert isinstance(rules, list)
        status_rule = next(rule for rule in rules if rule["type"] == "required_status_checks")
        status_rule["parameters"]["required_status_checks"] = []
        _, findings = audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

        self.assertTrue(any("not reported as protected" in finding for finding in findings))
        self.assertTrue(any("does not require the `validate`" in finding for finding in findings))

    def test_reports_inactive_ruleset_and_policy_drift(self) -> None:
        fixtures = api_fixtures()
        ruleset = fixtures["repos/hamedonassar95/Devobs/rulesets/24507159"]
        assert isinstance(ruleset, dict)
        ruleset["enforcement"] = "disabled"
        ruleset["bypass_actors"] = [{"actor_id": 12}]
        _, findings = audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

        self.assertTrue(any("is not active" in finding for finding in findings))
        self.assertTrue(any("bypass actors" in finding for finding in findings))

    def test_accepts_null_bypass_actors_as_no_configured_bypass(self) -> None:
        fixtures = api_fixtures()
        ruleset = fixtures["repos/hamedonassar95/Devobs/rulesets/24507159"]
        assert isinstance(ruleset, dict)
        ruleset["bypass_actors"] = None

        _, findings = audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

        self.assertEqual(findings, [])

    def test_rejects_missing_bypass_actors_field(self) -> None:
        fixtures = api_fixtures()
        ruleset = fixtures["repos/hamedonassar95/Devobs/rulesets/24507159"]
        assert isinstance(ruleset, dict)
        del ruleset["bypass_actors"]

        with self.assertRaisesRegex(PolicyCheckError, "did not include bypass actors"):
            audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

    def test_rejects_malformed_bypass_actors_field(self) -> None:
        fixtures = api_fixtures()
        ruleset = fixtures["repos/hamedonassar95/Devobs/rulesets/24507159"]
        assert isinstance(ruleset, dict)
        ruleset["bypass_actors"] = "none"

        with self.assertRaisesRegex(PolicyCheckError, "invalid bypass-actor list"):
            audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

    def test_reports_wrong_default_branch_scope_and_weakened_codeql_threshold(self) -> None:
        fixtures = api_fixtures()
        ruleset = fixtures["repos/hamedonassar95/Devobs/rulesets/24507159"]
        assert isinstance(ruleset, dict)
        ruleset["conditions"]["ref_name"]["include"] = ["refs/heads/release"]
        rules = ruleset["rules"]
        assert isinstance(rules, list)
        code_scanning = next(rule for rule in rules if rule["type"] == "code_scanning")
        code_scanning["parameters"]["code_scanning_tools"][0]["security_alerts_threshold"] = "critical"
        _, findings = audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

        self.assertTrue(any("does not include the default branch" in finding for finding in findings))
        self.assertTrue(any("high-or-higher" in finding for finding in findings))

    def test_rejects_wildcard_exclusion_that_removes_default_branch(self) -> None:
        fixtures = api_fixtures()
        ruleset = fixtures["repos/hamedonassar95/Devobs/rulesets/24507159"]
        assert isinstance(ruleset, dict)
        ruleset["conditions"]["ref_name"]["exclude"] = ["refs/heads/*"]
        _, findings = audit_repository("hamedonassar95/Devobs", api_get=fixtures.__getitem__)

        self.assertTrue(any("does not include the default branch" in finding for finding in findings))

    def test_api_client_can_use_public_api_without_authorization_header(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"default_branch":"main"}'
        with (
            mock.patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}),
            mock.patch(
                "scripts.check_repo_policy.urllib.request.urlopen", return_value=response
            ) as urlopen,
        ):
            payload = get_json("repos/hamedonassar95/Devobs")

        self.assertEqual(payload, {"default_branch": "main"})
        request = urlopen.call_args.args[0]
        self.assertIsInstance(request, urllib.request.Request)
        self.assertTrue(request.full_url.startswith("https://api.github.com/"))
        self.assertFalse(request.has_header("Authorization"))

    def test_api_client_uses_supplied_github_token_for_read_requests(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"default_branch":"main"}'
        with (
            mock.patch.dict(os.environ, {"GH_TOKEN": "test-read-token", "GITHUB_TOKEN": ""}),
            mock.patch(
                "scripts.check_repo_policy.urllib.request.urlopen", return_value=response
            ) as urlopen,
        ):
            payload = get_json("repos/hamedonassar95/Devobs")

        self.assertEqual(payload, {"default_branch": "main"})
        request = urlopen.call_args.args[0]
        self.assertIsInstance(request, urllib.request.Request)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-read-token")

    def test_api_http_errors_are_reported_as_inconclusive(self) -> None:
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/hamedonassar95/Devobs",
            403,
            "rate limit",
            {},
            None,
        )
        with mock.patch("scripts.check_repo_policy.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(PolicyCheckError, "HTTP 403"):
                get_json("repos/hamedonassar95/Devobs")

    def test_actions_summary_includes_named_drift_findings(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r+", encoding="utf-8") as summary_file:
            with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary_file.name}):
                write_step_summary(
                    "drift detected",
                    "hamedonassar95/Devobs (default branch main)",
                    ["The validate check is missing."],
                )
            summary_file.seek(0)
            summary = summary_file.read()

        self.assertIn("Status: **drift detected**", summary)
        self.assertIn("The validate check is missing.", summary)

    def test_reports_missing_ruleset_without_requesting_details(self) -> None:
        fixtures = api_fixtures()
        fixtures["repos/hamedonassar95/Devobs/rulesets?includes_parents=true"] = []
        requested: list[str] = []

        def api_get(path: str) -> object:
            requested.append(path)
            return fixtures[path]

        _, findings = audit_repository("hamedonassar95/Devobs", api_get=api_get)

        self.assertEqual(len(findings), 1)
        self.assertIn("was not found", findings[0])
        self.assertFalse(any(path.endswith("/rulesets/24507159") for path in requested))

    def test_rejects_invalid_repository_name(self) -> None:
        with self.assertRaises(PolicyCheckError):
            audit_repository("Devobs")


if __name__ == "__main__":
    unittest.main()
