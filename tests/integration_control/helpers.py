"""Deterministic offline fixtures for integration-control scenario tests."""

from __future__ import annotations

import copy
import json
from typing import Any

from scripts.pr_readiness_gate import CHECK_FIELDS, PR_FIELDS

REPO = "hamedonassar95/Devobs"
HEAD_SHA = "a" * 40
NEXT_SHA = "b" * 40
BASE = "main"
HEAD_TIME = "2026-11-21T00:00:00Z"
CHECK_TIME = "2026-11-21T00:05:00Z"
PR_NUMBER = "123"
BRANCH = "feature/integration-control-fixture"


def command_response(argv: list[str], stdout: str, returncode: int = 0,
                     stderr: str = "") -> dict[str, Any]:
    return {
        "argv": list(argv),
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def json_response(argv: list[str], payload: Any, returncode: int = 0,
                  stderr: str = "") -> dict[str, Any]:
    return command_response(
        argv,
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        returncode=returncode,
        stderr=stderr,
    )


def pr_view_argv(ref: str = PR_NUMBER) -> list[str]:
    return ["gh", "pr", "view", ref, "--repo", REPO, "--json", PR_FIELDS]


def commit_argv(sha: str = HEAD_SHA) -> list[str]:
    return [
        "gh", "api", f"repos/{REPO}/commits/{sha}", "--jq",
        ".commit.committer.date", "--hostname", "github.com",
    ]


def protection_argv() -> list[str]:
    return [
        "gh", "api", f"repos/{REPO}/branches/{BASE}/protection",
        "--hostname", "github.com",
    ]


def checks_argv() -> list[str]:
    return ["gh", "pr", "checks", PR_NUMBER, "--repo", REPO, "--json", CHECK_FIELDS]


def reviews_argv() -> list[str]:
    return [
        "gh", "api", f"repos/{REPO}/pulls/{PR_NUMBER}/reviews", "--paginate",
        "--slurp", "--hostname", "github.com",
    ]


def requested_argv() -> list[str]:
    return [
        "gh", "api", f"repos/{REPO}/pulls/{PR_NUMBER}/requested_reviewers",
        "--hostname", "github.com",
    ]


def valid_responses(*, check_bucket: str = "pass",
                    checks: list[dict[str, Any]] | None = None,
                    head_sha: str = HEAD_SHA) -> list[dict[str, Any]]:
    if checks is None:
        checks = [{
            "name": "CI",
            "bucket": check_bucket,
            "completedAt": CHECK_TIME,
            "state": "SUCCESS",
            "workflow": "CI",
        }]
    return [
        json_response(pr_view_argv(), {
            "number": int(PR_NUMBER),
            "state": "OPEN",
            "isDraft": False,
            "url": f"https://github.com/{REPO}/pull/{PR_NUMBER}",
            "headRefOid": head_sha,
            "baseRefName": BASE,
            "mergeable": True,
            "mergeStateStatus": "CLEAN",
            "reviewDecision": "APPROVED",
        }),
        command_response(commit_argv(head_sha), HEAD_TIME + "\n"),
        json_response(protection_argv(), {
            "required_status_checks": {
                "strict": True,
                "contexts": ["CI"],
            },
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
            },
        }),
        json_response(checks_argv(), checks),
        json_response(reviews_argv(), [{
            "state": "APPROVED",
            "submitted_at": CHECK_TIME,
            "commit_id": head_sha,
            "user": {"login": "human-reviewer", "type": "User"},
        }]),
        json_response(requested_argv(), {"users": [], "teams": []}),
    ]


def task(task_id: str, *, agent: str = "OPENCODE", branch: str = BRANCH,
         files: list[str] | None = None, status: str = "in_progress",
         previous_status: str = "planned", dependencies: list[str] | None = None,
         actions: list[str] | None = None, source_sha: str | None = HEAD_SHA,
         verification_result: str = "PENDING") -> dict[str, Any]:
    if files is None:
        files = [f"devobs/integration_control/{task_id.lower()}.py"]
    if actions is None:
        actions = ["code_change"]
    return {
        "id": task_id,
        "repository": REPO,
        "assigned_agent": agent,
        "branch": branch,
        "affected_files": list(files),
        "dependencies": list(dependencies or []),
        "status": status,
        "previous_status": previous_status,
        "source_sha": source_sha,
        "verification": {
            "commands": ["python -m unittest discover -s tests/integration_control -v"],
            "result": verification_result,
            "evidence": "offline fixture",
        },
        "pr_reference": f"#{PR_NUMBER}",
        "requested_actions": list(actions),
    }


def manifest(*tasks: dict[str, Any], approval: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "repositories": [REPO],
        "agents": {
            "CODEX": {"enabled": True},
            "OPENCODE": {"enabled": True},
        },
        "approval": copy.deepcopy(approval or {
            "merge": "pending_human",
            "deploy": "pending_human",
            "billing": "pending_human",
            "production": "pending_human",
        }),
        "tasks": copy.deepcopy(list(tasks)),
    }


def snapshot(*, responses: list[dict[str, Any]] | None = None,
             coordination: dict[str, Any] | None = None,
             approval: dict[str, Any] | None = None,
             expected_head_sha: str | None = HEAD_SHA,
             artifacts: list[dict[str, Any]] | None = None,
             branch_observations: list[dict[str, Any]] | None = None,
             untrusted_text: str = "") -> dict[str, Any]:
    if responses is None:
        responses = valid_responses()
    if coordination is None:
        coordination = manifest(task("ICP01"))
    if approval is None:
        approval = {
            "merge": "pending_human",
            "deploy": "pending_human",
            "billing": "pending_human",
            "production": "pending_human",
        }
    if branch_observations is None:
        branch_observations = [{
            "branch": BRANCH,
            "sha": HEAD_SHA,
            "observed_at": HEAD_TIME,
        }]
    return {
        "schema_version": 1,
        "run_id": "integration-control-fixture",
        "expected_head_sha": expected_head_sha,
        "github": {
            "repository": REPO,
            "pr_ref": PR_NUMBER,
            "responses": copy.deepcopy(responses),
        },
        "coordination": copy.deepcopy(coordination),
        "approval": copy.deepcopy(approval),
        "artifacts": copy.deepcopy(artifacts or []),
        "branch_observations": copy.deepcopy(branch_observations),
        "untrusted_text": untrusted_text,
    }


def artifact(artifact_id: str, *, excerpt: str = "sanitized evidence",
             kind: str = "local_artifact", source: str = "local:fixture") -> dict[str, Any]:
    return {
        "id": artifact_id,
        "kind": kind,
        "source": source,
        "excerpt": excerpt,
    }


def finding_codes(report: dict[str, Any]) -> set[str]:
    return {item["code"] for item in report["findings"]}
