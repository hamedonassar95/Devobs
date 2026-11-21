"""Behavioral tests for the read-only pull request readiness gate."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pr_readiness_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pr_readiness_gate", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Cannot load pr_readiness_gate module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str
    stderr: str = ""


HEAD_SHA = "1111111111111111111111111111111111111111"
OLD_SHA = "0000000000000000000000000000000000000000"
HEAD_TIME = "2026-11-20T10:00:00Z"


def fixture() -> dict[str, object]:
    return {
        "pr": {
            "number": 42,
            "state": "OPEN",
            "isDraft": False,
            "url": "https://github.com/acme/widgets/pull/42",
            "headRefOid": HEAD_SHA,
            "baseRefName": "main",
            "mergeable": True,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "APPROVED",
        },
        "commit_date": HEAD_TIME,
        "protection": {
            "required_status_checks": {
                "strict": False,
                "contexts": ["validate", "security"],
                "checks": [
                    {"context": "validate", "app_id": None},
                    {"context": "security", "app_id": None},
                ],
            },
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
            },
        },
        "checks": [
            {
                "name": "validate",
                "state": "SUCCESS",
                "bucket": "pass",
                "completedAt": "2026-11-20T10:20:00Z",
                "link": "https://github.com/acme/widgets/actions/runs/1",
                "workflow": "CI",
            },
            {
                "name": "security",
                "state": "SUCCESS",
                "bucket": "pass",
                "completedAt": "2026-11-20T10:21:00Z",
                "link": "https://github.com/acme/widgets/actions/runs/2",
                "workflow": "CI",
            },
        ],
        "reviews": [
            {
                "id": 1,
                "state": "APPROVED",
                "submitted_at": "2026-11-20T10:30:00Z",
                "commit_id": HEAD_SHA,
                "user": {"login": "alice", "type": "User"},
            }
        ],
        "requested": {"users": [], "teams": []},
    }


def command_key(args: list[str]) -> str:
    if args[:3] == ["gh", "pr", "view"]:
        return "pr"
    if args[:2] == ["gh", "pr"] and len(args) > 2 and args[2] == "checks":
        return "checks"
    if args[:2] != ["gh", "api"]:
        raise AssertionError(f"Unexpected command: {args!r}")
    endpoint = args[2]
    if endpoint.endswith("/requested_reviewers"):
        return "requested"
    if "/reviews" in endpoint:
        return "reviews"
    if "/protection" in endpoint:
        return "protection"
    if "/commits/" in endpoint:
        return "commit_date"
    raise AssertionError(f"Unexpected gh api endpoint: {endpoint}")


class FakeRunner:
    def __init__(self, data: dict[str, object], failures: dict[str, Result] | None = None):
        self.data = copy.deepcopy(data)
        self.failures = failures or {}
        self.commands: list[list[str]] = []

    def __call__(self, args: list[str]) -> Result:
        self.commands.append(list(args))
        key = command_key(args)
        if key in self.failures:
            return self.failures[key]
        value = self.data[key]
        if key == "commit_date":
            return Result(0, str(value))
        return Result(0, json.dumps(value))


class PrReadinessGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def evaluate(self, data: dict[str, object], failures: dict[str, Result] | None = None):
        runner = FakeRunner(data, failures)
        return self.module.evaluate("acme/widgets", "42", runner), runner

    def test_failed_ci_blocks_ready_status(self) -> None:
        data = fixture()
        data["checks"][1]["bucket"] = "fail"
        data["checks"][1]["state"] = "FAILURE"
        result, _ = self.evaluate(data)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("CI_FAILED", [item["code"] for item in result["blockers"]])

    def test_pending_ci_blocks_ready_status(self) -> None:
        data = fixture()
        data["checks"][1]["bucket"] = "pending"
        data["checks"][1]["state"] = "PENDING"
        data["checks"][1]["completedAt"] = None
        result, _ = self.evaluate(data)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("CI_PENDING", [item["code"] for item in result["blockers"]])

    def test_missing_human_approval_blocks_ready_status(self) -> None:
        data = fixture()
        data["reviews"] = []
        data["pr"]["reviewDecision"] = "REVIEW_REQUIRED"
        result, _ = self.evaluate(data)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("APPROVAL_MISSING", [item["code"] for item in result["blockers"]])

    def test_approval_on_old_head_is_stale_and_blocks(self) -> None:
        data = fixture()
        data["reviews"][0]["commit_id"] = OLD_SHA
        data["reviews"][0]["submitted_at"] = "2026-11-20T09:00:00Z"
        result, _ = self.evaluate(data)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("APPROVAL_STALE", [item["code"] for item in result["blockers"]])

    def test_merge_conflict_blocks_ready_status(self) -> None:
        data = fixture()
        data["pr"]["mergeable"] = False
        data["pr"]["mergeStateStatus"] = "DIRTY"
        result, _ = self.evaluate(data)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("MERGE_CONFLICT", [item["code"] for item in result["blockers"]])

    def test_branch_protection_api_failure_is_unverified(self) -> None:
        failure = Result(1, "", "gh: API error (403): Resource not accessible")
        result, _ = self.evaluate(fixture(), {"protection": failure})
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertIn(
            "BRANCH_PROTECTION_UNVERIFIED",
            [item["code"] for item in result["unverified"]],
        )

    def test_valid_github_evidence_is_verified_ready(self) -> None:
        result, runner = self.evaluate(fixture())
        self.assertEqual("VERIFIED_READY", result["status"])
        self.assertEqual([], result["blockers"])
        self.assertEqual([], result["unverified"])
        keys = {command_key(command) for command in runner.commands}
        self.assertEqual({"pr", "commit_date", "protection", "checks", "reviews", "requested"}, keys)

    def test_local_test_output_is_never_treated_as_github_ci(self) -> None:
        local_output = "Ran 7 tests in 0.01s\n\nOK\n"
        failure = Result(0, local_output)
        result, _ = self.evaluate(fixture(), {"checks": failure})
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertNotIn("VERIFIED_READY", result["status"])
        self.assertTrue(
            any(item["code"] == "CHECKS_UNVERIFIED" for item in result["unverified"])
        )

    def test_unresolved_review_request_blocks_ready_status(self) -> None:
        data = fixture()
        data["requested"]["users"] = [{"login": "bob"}]
        result, _ = self.evaluate(data)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("REVIEW_REQUESTED", [item["code"] for item in result["blockers"]])

    def test_missing_required_check_is_unverified(self) -> None:
        data = fixture()
        data["checks"] = data["checks"][:1]
        result, _ = self.evaluate(data)
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertIn("REQUIRED_CHECK_MISSING", [item["code"] for item in result["unverified"]])

    def test_empty_check_evidence_is_unverified(self) -> None:
        data = fixture()
        data["checks"] = []
        result, _ = self.evaluate(data)
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertIn("CI_EVIDENCE_MISSING", [item["code"] for item in result["unverified"]])

    def test_draft_pull_request_blocks_ready_status(self) -> None:
        data = fixture()
        data["pr"]["isDraft"] = True
        result, _ = self.evaluate(data)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("PR_NOT_READY", [item["code"] for item in result["blockers"]])

    def test_unprotected_base_can_still_be_verified_ready(self) -> None:
        failure = Result(1, "{\"message\":\"Branch not protected\"}\n", "gh: HTTP 404: Not Found")
        result, _ = self.evaluate(fixture(), {"protection": failure})
        self.assertEqual("VERIFIED_READY", result["status"])
        self.assertEqual([], result["unverified"])
        self.assertFalse(result["evidence"]["branch_protection"]["protected"])

    def test_invalid_repository_input_is_unverified(self) -> None:
        result = self.module.evaluate("not-a-repo", "42", FakeRunner(fixture()))
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertIn("INPUT_INVALID", [item["code"] for item in result["unverified"]])


if __name__ == "__main__":
    unittest.main()
