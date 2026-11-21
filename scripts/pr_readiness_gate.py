#!/usr/bin/env python3
"""Read-only pull request merge-readiness gate backed by GitHub CLI evidence.

This tool never approves, merges, closes, labels, comments on, or modifies a pull
request. It only runs read-only ``gh pr view``, ``gh pr checks`` and ``gh api``
GET commands. Missing or malformed evidence is never counted as success.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404 - fixed gh executable; read-only commands, no shell.
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

SCHEMA_VERSION = 1
PR_FIELDS = (
    "number,state,isDraft,url,headRefOid,baseRefName,mergeable,"
    "mergeStateStatus,reviewDecision"
)
CHECK_FIELDS = "bucket,completedAt,description,event,link,name,startedAt,state,workflow"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
PR_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/pull/"
    r"(?P<number>[1-9][0-9]*)(?:[/?#].*)?$"
)
BRANCH_REF_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")
SECRET_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|"
    r"Bearer\s+\S+|(?:token|secret|password)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)
SKEW = timedelta(seconds=60)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


def finding(code: str, message: str, source: str) -> dict[str, str]:
    return {"code": code, "message": message, "source": source}


def clean_error(value: object) -> str:
    text = " ".join(str(value or "").split())
    return SECRET_RE.sub("[REDACTED]", text)[:300]


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_repo(repo: str) -> str:
    candidate = repo.strip()
    if not REPO_RE.fullmatch(candidate) or any(part in {".", ".."} for part in candidate.split("/")):
        raise ValueError("repository must use OWNER/REPO format")
    return candidate


def normalize_pr_ref(value: str) -> str:
    candidate = value.strip()
    if candidate.isdigit():
        return str(int(candidate))
    match = PR_URL_RE.fullmatch(candidate)
    if match:
        return match.group("number")
    if BRANCH_REF_RE.fullmatch(candidate) and ".." not in candidate:
        return candidate
    raise ValueError("pull request must be a number, GitHub PR URL, or branch name")


def repo_from_pr_url(value: str) -> str:
    match = PR_URL_RE.fullmatch(value.strip())
    return f"{match.group('owner')}/{match.group('repo')}" if match else ""


def result_shell(
    status: str,
    *,
    repo: str,
    pr_ref: str,
    blockers: list[dict[str, str]] | None = None,
    unverified: list[dict[str, str]] | None = None,
    evidence: dict[str, Any] | None = None,
    pr: dict[str, Any] | None = None,
    summary: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "repository": repo,
        "pull_request_ref": pr_ref,
        "pr": pr or {},
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": summary,
        "blockers": blockers or [],
        "unverified": unverified or [],
        "evidence": evidence or {},
    }


def finalize(
    *,
    repo: str,
    pr_ref: str,
    blockers: list[dict[str, str]],
    unverified: list[dict[str, str]],
    evidence: dict[str, Any],
    pr: dict[str, Any],
) -> dict[str, Any]:
    if unverified:
        status, summary = "UNVERIFIED", "Evidence is incomplete; merge readiness cannot be verified."
    elif blockers:
        status, summary = "BLOCKED", "Verified evidence shows unmet merge requirements."
    else:
        status, summary = "VERIFIED_READY", "Verified GitHub evidence satisfies all readiness requirements."
    return result_shell(
        status, repo=repo, pr_ref=pr_ref, blockers=blockers, unverified=unverified,
        evidence=evidence, pr=pr, summary=summary,
    )


def run(
    runner: Callable[[list[str]], CommandResult],
    args: list[str],
    *,
    label: str,
    code: str,
    unverified: list[dict[str, str]],
    pending_exit_code: int | None = None,
    suppress_404: bool = False,
) -> CommandResult | None:
    try:
        response = runner(args)
    except Exception as exc:  # noqa: BLE001 - fail closed on any runner failure.
        unverified.append(finding(code, f"{label} command failed: {type(exc).__name__}", label))
        return None
    rc = getattr(response, "returncode", None)
    stdout, stderr = getattr(response, "stdout", ""), getattr(response, "stderr", "")
    if not isinstance(rc, int) or not isinstance(stdout, str):
        unverified.append(finding(code, f"{label} returned an invalid response", label))
        return None
    stderr = str(stderr)
    wrapped = CommandResult(rc, stdout, stderr)
    if rc == 0 or rc == pending_exit_code:
        return wrapped
    if suppress_404 and is_404(wrapped):
        return wrapped
    detail = clean_error(stderr) or clean_error(stdout) or f"exit {rc}"
    unverified.append(finding(code, f"{label} failed: {detail}", label))
    return None


def is_404(response: CommandResult) -> bool:
    text = f"{response.stdout} {response.stderr}".lower()
    return "404" in text or "not found" in text or "not protected" in text


def json_payload(
    response: CommandResult,
    *,
    label: str,
    code: str,
    expected: type,
    unverified: list[dict[str, str]],
) -> Any | None:
    try:
        payload = json.loads(response.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError):
        unverified.append(finding(code, f"{label} did not return valid JSON", label))
        return None
    if not isinstance(payload, expected):
        unverified.append(finding(code, f"{label} returned unexpected JSON", label))
        return None
    return payload


def protection_summary(
    payload: dict[str, Any],
    unverified: list[dict[str, str]],
) -> dict[str, Any]:
    contexts: list[str] = []
    strict, approvals, dismiss = False, 1, False
    policy = payload.get("required_status_checks")
    if policy is not None:
        if not isinstance(policy, dict):
            unverified.append(finding("BRANCH_PROTECTION_UNVERIFIED", "required_status_checks is malformed", "branch protection"))
        else:
            strict = policy.get("strict") is True
            raw_contexts = policy.get("contexts")
            if raw_contexts is not None and not isinstance(raw_contexts, list):
                unverified.append(finding("BRANCH_PROTECTION_UNVERIFIED", "required status contexts are malformed", "branch protection"))
            elif isinstance(raw_contexts, list):
                contexts.extend(item for item in raw_contexts if isinstance(item, str))
            raw_checks = policy.get("checks")
            if isinstance(raw_checks, list):
                contexts.extend(
                    item["context"] for item in raw_checks
                    if isinstance(item, dict) and isinstance(item.get("context"), str)
                )
    reviews = payload.get("required_pull_request_reviews")
    if reviews is not None:
        if not isinstance(reviews, dict):
            unverified.append(finding("BRANCH_PROTECTION_UNVERIFIED", "required_pull_request_reviews is malformed", "branch protection"))
        else:
            count = reviews.get("required_approving_review_count", 1)
            if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                approvals = max(1, count)
            else:
                unverified.append(finding("BRANCH_PROTECTION_UNVERIFIED", "required approving review count is malformed", "branch protection"))
            dismiss = reviews.get("dismiss_stale_reviews") is True
    return {
        "protected": True,
        "required_contexts": sorted(set(contexts)),
        "required_approvals": approvals,
        "strict": strict,
        "dismiss_stale_reviews": dismiss,
    }


def read_protection(
    repo: str,
    base: str,
    runner: Callable[[list[str]], CommandResult],
    unverified: list[dict[str, str]],
) -> dict[str, Any]:
    unknown = {"protected": None, "required_contexts": [], "required_approvals": 1}
    response = run(
        runner,
        ["gh", "api", f"repos/{repo}/branches/{base}/protection", "--hostname", "github.com"],
        label="branch protection", code="BRANCH_PROTECTION_UNVERIFIED",
        unverified=unverified, suppress_404=True,
    )
    if response is None:
        return unknown
    if response.returncode != 0:
        if is_404(response):
            return {"protected": False, "required_contexts": [], "required_approvals": 1,
                    "strict": False, "dismiss_stale_reviews": False}
        return unknown
    payload = json_payload(
        response, label="branch protection", code="BRANCH_PROTECTION_UNVERIFIED",
        expected=dict, unverified=unverified,
    )
    return protection_summary(payload, unverified) if payload is not None else unknown


def read_list(
    runner: Callable[[list[str]], CommandResult],
    args: list[str],
    *,
    label: str,
    code: str,
    unverified: list[dict[str, str]],
) -> list[dict[str, Any]]:
    response = run(runner, args, label=label, code=code, unverified=unverified,
                   pending_exit_code=8 if label == "GitHub checks" else None)
    if response is None:
        return []
    payload = json_payload(response, label=label, code=code, expected=list, unverified=unverified)
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def read_requested(
    number: int,
    repo: str,
    runner: Callable[[list[str]], CommandResult],
    unverified: list[dict[str, str]],
) -> dict[str, Any]:
    response = run(
        runner,
        ["gh", "api", f"repos/{repo}/pulls/{number}/requested_reviewers", "--hostname", "github.com"],
        label="requested reviewers", code="REVIEW_REQUESTS_UNVERIFIED", unverified=unverified,
    )
    if response is None:
        return {}
    payload = json_payload(
        response, label="requested reviewers", code="REVIEW_REQUESTS_UNVERIFIED",
        expected=dict, unverified=unverified,
    )
    return payload or {}


def assess_checks(
    raw_checks: list[dict[str, Any]],
    *,
    head_time: datetime | None,
    blockers: list[dict[str, str]],
    unverified: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    evidence: list[dict[str, Any]] = []
    observed: set[str] = set()
    passing: set[str] = set()
    if not raw_checks:
        unverified.append(finding("CI_EVIDENCE_MISSING", "no GitHub check evidence returned", "GitHub checks"))
    for item in raw_checks:
        name, bucket = item.get("name"), item.get("bucket")
        if not isinstance(name, str) or not name or not isinstance(bucket, str):
            unverified.append(finding("CHECKS_UNVERIFIED", "check evidence is malformed", "GitHub checks"))
            continue
        lowered, name = bucket.strip().lower(), name.strip()
        observed.add(name.lower())
        completed_raw = item.get("completedAt")
        completed = parse_time(completed_raw)
        fresh = False
        if lowered in {"fail", "cancel"}:
            blockers.append(finding("CI_FAILED", f"check {name} is {lowered}", "GitHub checks"))
        elif lowered == "pending":
            blockers.append(finding("CI_PENDING", f"check {name} is pending", "GitHub checks"))
        elif lowered == "pass":
            if completed is None or (head_time and completed < head_time - SKEW):
                unverified.append(finding("CHECK_STALE", f"check {name} lacks fresh completion evidence", "GitHub checks"))
            else:
                fresh = True
                passing.add(name.lower())
        elif lowered != "skipping":
            unverified.append(finding("CHECKS_UNVERIFIED", f"check {name} has unknown bucket {lowered}", "GitHub checks"))
        evidence.append({
            "name": name, "bucket": lowered,
            "state": item.get("state") if isinstance(item.get("state"), str) else None,
            "completed_at": completed_raw if isinstance(completed_raw, str) else None,
            "fresh": fresh,
        })
    return evidence, observed, passing


def assess_reviews(
    raw_reviews: list[dict[str, Any]],
    *,
    head_sha: str,
    head_time: datetime | None,
    required_approvals: int,
    review_decision: object,
    blockers: list[dict[str, str]],
    unverified: list[dict[str, str]],
) -> tuple[list[str], list[str]]:
    latest: dict[str, dict[str, Any]] = {}
    meaningful = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
    for review in raw_reviews:
        state = review.get("state")
        if not isinstance(state, str) or state.upper() not in meaningful:
            continue
        user = review.get("user")
        login = user.get("login") if isinstance(user, dict) else None
        user_type = user.get("type") if isinstance(user, dict) else None
        if not isinstance(login, str) or not login or not isinstance(user_type, str):
            unverified.append(finding("REVIEWS_UNVERIFIED", "review identity is malformed", "reviews"))
            continue
        if user_type.lower() == "bot" or login.endswith("[bot]"):
            continue
        submitted, commit_id = parse_time(review.get("submitted_at")), review.get("commit_id")
        if submitted is None or not isinstance(commit_id, str) or not commit_id:
            unverified.append(finding("REVIEWS_UNVERIFIED", f"review by {login} lacks freshness evidence", "reviews"))
            continue
        state = state.upper()
        if login not in latest or submitted >= latest[login]["submitted"]:
            latest[login] = {"state": state, "submitted": submitted, "commit_id": commit_id}

    valid: list[str] = []
    stale: list[str] = []
    for login, review in latest.items():
        if review["state"] == "CHANGES_REQUESTED":
            blockers.append(finding("CHANGES_REQUESTED", f"{login} requested changes", "reviews"))
        elif review["state"] == "APPROVED":
            old = review["commit_id"] != head_sha or (head_time and review["submitted"] < head_time - SKEW)
            (stale if old else valid).append(login)

    if review_decision == "CHANGES_REQUESTED" and not any(
        item["code"] == "CHANGES_REQUESTED" for item in blockers
    ):
        blockers.append(finding("CHANGES_REQUESTED", "GitHub reports requested changes", "PR metadata"))
    if len(valid) < required_approvals:
        code = "APPROVAL_STALE" if stale else "APPROVAL_MISSING"
        message = ("approval does not apply to the current head" if stale
                   else "no fresh human approval satisfies the requirement")
        blockers.append(finding(code, message, "reviews"))
    return valid, stale


def evaluate(
    repo: str,
    pr_ref: str,
    runner: Callable[[list[str]], CommandResult],
) -> dict[str, Any]:
    """Evaluate one PR using only the supplied read-only GitHub CLI runner."""
    original_ref = str(pr_ref)
    try:
        target_repo = normalize_repo(repo or repo_from_pr_url(original_ref))
        target_ref = normalize_pr_ref(original_ref)
    except ValueError as exc:
        return result_shell(
            "UNVERIFIED", repo=str(repo), pr_ref=original_ref,
            unverified=[finding("INPUT_INVALID", str(exc), "input")],
            summary="Invalid repository or pull request reference.",
        )

    blockers: list[dict[str, str]] = []
    unverified: list[dict[str, str]] = []
    pr_response = run(
        runner,
        ["gh", "pr", "view", target_ref, "--repo", target_repo, "--json", PR_FIELDS],
        label="PR metadata", code="PR_METADATA_UNVERIFIED", unverified=unverified,
    )
    pr = (json_payload(pr_response, label="PR metadata", code="PR_METADATA_UNVERIFIED",
                       expected=dict, unverified=unverified) if pr_response else None)
    if not isinstance(pr, dict):
        return finalize(repo=target_repo, pr_ref=target_ref, blockers=blockers,
                        unverified=unverified, evidence={}, pr={})

    number, head_sha, base = pr.get("number"), pr.get("headRefOid"), pr.get("baseRefName")
    if (not isinstance(number, int) or isinstance(number, bool) or number < 1
            or not isinstance(head_sha, str) or not SHA_RE.fullmatch(head_sha)
            or not isinstance(base, str) or not base):
        unverified.append(finding("PR_METADATA_UNVERIFIED", "PR number, head SHA, or base branch is invalid", "PR metadata"))
        return finalize(repo=target_repo, pr_ref=target_ref, blockers=blockers,
                        unverified=unverified, evidence={}, pr=pr)

    if pr.get("state") != "OPEN" or pr.get("isDraft") is not False:
        blockers.append(finding("PR_NOT_READY", "pull request must be open and not a draft", "PR metadata"))
    mergeable, merge_state = pr.get("mergeable"), pr.get("mergeStateStatus")
    norm_state = merge_state.upper() if isinstance(merge_state, str) else ""
    if not isinstance(mergeable, bool) or not norm_state:
        unverified.append(finding("MERGEABILITY_UNVERIFIED", "GitHub has not published mergeability", "PR metadata"))
    elif mergeable is False or norm_state == "DIRTY":
        blockers.append(finding("MERGE_CONFLICT", "pull request has merge conflicts", "PR metadata"))
    elif norm_state in {"BLOCKED", "UNSTABLE"}:
        blockers.append(finding("PR_MERGE_STATE", f"GitHub merge state is {norm_state}", "PR metadata"))
    elif norm_state in {"UNKNOWN"} or norm_state not in {"CLEAN", "BEHIND"}:
        unverified.append(finding("MERGEABILITY_UNVERIFIED", "GitHub merge state is not verifiable", "PR metadata"))

    head_time: datetime | None = None
    commit_response = run(
        runner,
        ["gh", "api", f"repos/{target_repo}/commits/{head_sha}", "--jq", ".commit.committer.date",
         "--hostname", "github.com"],
        label="head commit", code="COMMIT_EVIDENCE_UNVERIFIED", unverified=unverified,
    )
    if commit_response:
        head_time = parse_time(commit_response.stdout.strip())
        if head_time is None:
            unverified.append(finding("COMMIT_EVIDENCE_UNVERIFIED", "head commit time is missing or invalid", "head commit"))

    protection = read_protection(target_repo, base, runner, unverified)
    raw_checks = read_list(
        runner,
        ["gh", "pr", "checks", str(number), "--repo", target_repo, "--json", CHECK_FIELDS],
        label="GitHub checks", code="CHECKS_UNVERIFIED", unverified=unverified,
    )
    raw_reviews = read_list(
        runner,
        ["gh", "api", f"repos/{target_repo}/pulls/{number}/reviews", "--paginate", "--slurp",
         "--hostname", "github.com"],
        label="reviews", code="REVIEWS_UNVERIFIED", unverified=unverified,
    )
    requested = read_requested(number, target_repo, runner, unverified)

    check_evidence, observed, passing = assess_checks(
        raw_checks, head_time=head_time, blockers=blockers, unverified=unverified,
    )
    contexts = protection.get("required_contexts", [])
    if isinstance(contexts, list):
        for context in contexts:
            if isinstance(context, str) and context.lower() not in observed:
                unverified.append(finding("REQUIRED_CHECK_MISSING", f"required check {context} was not returned", "branch protection"))

    required_approvals = protection.get("required_approvals", 1)
    if not isinstance(required_approvals, int) or isinstance(required_approvals, bool):
        required_approvals = 1
    valid, stale = assess_reviews(
        raw_reviews, head_sha=head_sha, head_time=head_time,
        required_approvals=required_approvals, review_decision=pr.get("reviewDecision"),
        blockers=blockers, unverified=unverified,
    )

    users, teams = requested.get("users"), requested.get("teams")
    if not isinstance(users, list) or not isinstance(teams, list):
        unverified.append(finding("REVIEW_REQUESTS_UNVERIFIED", "requested reviewer evidence is malformed", "requested reviewers"))
    elif users or teams:
        blockers.append(finding("REVIEW_REQUESTED", "review requests remain unresolved", "requested reviewers"))
    if protection.get("strict") is True and norm_state == "BEHIND":
        blockers.append(finding("OUTDATED_BRANCH", "branch is behind the protected base", "PR metadata"))

    evidence = {
        "head_commit": {"sha": head_sha, "committed_at": head_time.isoformat() if head_time else None},
        "branch_protection": protection,
        "ci": {
            "source": "gh pr checks --json", "checks": check_evidence,
            "required_contexts": contexts if isinstance(contexts, list) else [],
            "passing_checks": sorted(passing),
        },
        "reviews": {
            "source": "GitHub REST reviews", "required_approving_review_count": required_approvals,
            "fresh_approvals": sorted(valid), "stale_approvals": sorted(stale),
            "requested_users": len(users) if isinstance(users, list) else None,
            "requested_teams": len(teams) if isinstance(teams, list) else None,
        },
        "mergeability": {"source": "gh pr view --json", "mergeable": mergeable, "merge_state_status": merge_state},
    }
    return finalize(repo=target_repo, pr_ref=target_ref, blockers=blockers,
                    unverified=unverified, evidence=evidence, pr=pr)


def subprocess_runner(timeout: int = 30) -> Callable[[list[str]], CommandResult]:
    env = os.environ.copy()
    env.update({"GH_PAGER": "cat", "GH_PROMPT_DISABLED": "1", "NO_COLOR": "1"})

    def invoke(args: list[str]) -> CommandResult:
        if not args or args[0] != "gh":
            raise ValueError("only read-only gh commands are allowed")
        try:
            done = subprocess.run(  # noqa: S603  # nosec B603 - fixed gh argv, shell=False, read-only.
                args, capture_output=True, text=True, timeout=timeout, env=env, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CommandResult(1, "", type(exc).__name__)
        return CommandResult(done.returncode, done.stdout or "", done.stderr or "")

    return invoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pr", required=True, help="PR number, GitHub PR URL, or branch name")
    parser.add_argument("--repo", default="", help="OWNER/REPO; inferred from a PR URL when omitted")
    parser.add_argument("--timeout", type=int, default=30, help="per-command timeout in seconds")
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.repo, args.pr, subprocess_runner(args.timeout))
    except Exception as exc:  # noqa: BLE001 - never leak an unhandled error as success.
        report = result_shell(
            "UNVERIFIED", repo=args.repo, pr_ref=args.pr,
            unverified=[finding("INTERNAL_ERROR", type(exc).__name__, "gate")],
            summary="The readiness gate failed closed after an unexpected error.",
        )
    print(json.dumps(report, indent=2 if args.pretty else None, sort_keys=True))
    return {"VERIFIED_READY": 0, "BLOCKED": 1, "UNVERIFIED": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
