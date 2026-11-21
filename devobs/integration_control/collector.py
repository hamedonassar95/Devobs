"""Validate and normalize one offline integration snapshot."""

from __future__ import annotations

from typing import Any

from .models import (
    BLOCKER,
    UNVERIFIED_SEVERITY,
    ControlError,
    Finding,
    INPUT_SCHEMA_VERSION,
)
from .security import (
    BRANCH_RE,
    ID_RE,
    MAX_ITEMS,
    MAX_RESPONSE_BYTES,
    MAX_STRING,
    REPO_RE,
    RUN_RE,
    SHA_RE,
    TIMESTAMP_RE,
    bounded_text,
    redact,
    require_keys,
    safe_source,
    secret_finding,
)

TOP_KEYS = {
    "schema_version",
    "run_id",
    "expected_head_sha",
    "github",
    "coordination",
    "approval",
    "artifacts",
    "branch_observations",
    "untrusted_text",
}
GITHUB_KEYS = {"repository", "pr_ref", "responses"}
RESPONSE_KEYS = {"argv", "returncode", "stdout", "stderr"}
ARTIFACT_KEYS = {"id", "kind", "source", "excerpt"}
BRANCH_KEYS = {"branch", "sha", "observed_at"}


def _validate_responses(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise ControlError("invalid_github_responses")
    responses: list[dict[str, Any]] = []
    for item in raw:
        record = require_keys(item, RESPONSE_KEYS, "invalid_github_response")
        argv = record["argv"]
        if (not isinstance(argv, list) or not 1 <= len(argv) <= 24
                or any(not isinstance(arg, str) or not arg or len(arg) > 256
                       or "\x00" in arg for arg in argv)
                or argv[0] != "gh"):
            raise ControlError("invalid_github_command")
        returncode = record["returncode"]
        if not isinstance(returncode, int) or isinstance(returncode, bool) or not 0 <= returncode <= 255:
            raise ControlError("invalid_github_returncode")
        stdout, stderr = record["stdout"], record["stderr"]
        if not isinstance(stdout, str) or len(stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise ControlError("invalid_github_stdout")
        if not isinstance(stderr, str) or len(stderr) > MAX_STRING:
            raise ControlError("invalid_github_stderr")
        responses.append({
            "argv": list(argv),
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        })
    return responses


def _validate_artifacts(raw: Any, findings: list[Finding]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        raise ControlError("invalid_artifacts")
    artifacts: list[dict[str, Any]] = []
    for item in raw:
        record = require_keys(item, ARTIFACT_KEYS, "invalid_artifact")
        artifact_id = record["id"]
        if not isinstance(artifact_id, str) or not ID_RE.fullmatch(artifact_id):
            raise ControlError("invalid_artifact_id")
        kind = bounded_text(record["kind"], "invalid_artifact_kind", limit=128)
        source = safe_source(record["source"])
        safe_excerpt, changed = redact(record["excerpt"], limit=512)
        if changed:
            findings.append(Finding(
                "SECRET_MATERIAL_DETECTED",
                BLOCKER,
                f"artifact:{artifact_id}",
                message=f"secret material detected: {safe_excerpt}",
            ))
        artifacts.append({
            "id": artifact_id,
            "kind": kind,
            "source": source,
            "excerpt": safe_excerpt,
        })
    return artifacts


def _validate_branches(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        raise ControlError("invalid_branch_observations")
    observations: list[dict[str, Any]] = []
    for item in raw:
        record = require_keys(item, BRANCH_KEYS, "invalid_branch_observation")
        branch = record["branch"]
        sha = record["sha"]
        observed_at = record["observed_at"]
        if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
            raise ControlError("invalid_branch_name")
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            raise ControlError("invalid_branch_sha")
        if not isinstance(observed_at, str) or not TIMESTAMP_RE.fullmatch(observed_at):
            raise ControlError("invalid_observation_time")
        observations.append({
            "branch": branch,
            "sha": sha,
            "observed_at": observed_at,
        })
    return observations


def collect(document: Any) -> tuple[dict[str, Any], tuple[Finding, ...]]:
    """Return a sanitized internal snapshot and collector findings."""
    payload = require_keys(document, TOP_KEYS, "invalid_snapshot_fields")
    if payload["schema_version"] != INPUT_SCHEMA_VERSION:
        raise ControlError("unsupported_input_schema")

    findings: list[Finding] = []
    run_id = payload["run_id"]
    if not isinstance(run_id, str) or not RUN_RE.fullmatch(run_id):
        raise ControlError("invalid_run_id")

    expected = payload["expected_head_sha"]
    if expected is not None and (not isinstance(expected, str) or not SHA_RE.fullmatch(expected)):
        raise ControlError("invalid_expected_head_sha")
    if expected is None:
        findings.append(Finding("EXPECTED_SHA_MISSING", UNVERIFIED_SEVERITY, "snapshot"))

    github = require_keys(payload["github"], GITHUB_KEYS, "invalid_github_snapshot")
    repository = github["repository"]
    if not isinstance(repository, str) or not REPO_RE.fullmatch(repository):
        raise ControlError("invalid_repository")
    pr_ref = bounded_text(github["pr_ref"], "invalid_pr_ref", limit=200)
    if not (pr_ref.isdigit() or BRANCH_RE.fullmatch(pr_ref)):
        raise ControlError("invalid_pr_ref")

    approval = payload["approval"]
    if approval is not None and not isinstance(approval, dict):
        raise ControlError("invalid_approval")

    untrusted = payload["untrusted_text"]
    if not isinstance(untrusted, str) or len(untrusted) > MAX_STRING:
        raise ControlError("invalid_untrusted_text")
    _safe_untrusted, changed = redact(untrusted)
    if changed:
        findings.append(secret_finding("untrusted_text"))

    if payload["coordination"] is not None and not isinstance(payload["coordination"], dict):
        raise ControlError("invalid_coordination")

    normalized = {
        "run_id": run_id,
        "expected_head_sha": expected,
        "github": {
            "repository": repository,
            "pr_ref": pr_ref,
            "responses": _validate_responses(github["responses"]),
        },
        "coordination": payload["coordination"],
        "approval": approval,
        "artifacts": _validate_artifacts(payload["artifacts"], findings),
        "branch_observations": _validate_branches(payload["branch_observations"]),
        "untrusted_text_present": bool(untrusted.strip()),
    }
    return normalized, tuple(findings)
