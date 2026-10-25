#!/usr/bin/env python3
"""Report drift from the repository's required default-branch ruleset.

This check is intentionally read-only and uses the public GitHub REST API. In
GitHub Actions it uses the workflow's least-privilege token because some
ruleset fields are omitted from anonymous responses. It never creates, updates,
or deletes repository settings.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any


API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
TIMEOUT_SECONDS = 15


class PolicyCheckError(RuntimeError):
    """An API or input error prevented the policy audit from completing."""


def get_json(path: str) -> Any:
    """Fetch a GitHub REST resource, using a supplied read-only token if present."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "Cache-Control": "no-cache",
        "User-Agent": "devobs-repository-policy-audit",
        "X-GitHub-Api-Version": API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{API_URL}/{path.lstrip('/')}",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(  # nosec B310 - fixed HTTPS GitHub API host; GET-only with optional read-only token.
            request, timeout=TIMEOUT_SECONDS
        ) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code == 401:
            detail = (
                "GitHub rejected the authentication. Check that the configured token is valid, "
                "unexpired, and authorized for this repository; do not print the token."
            )
        elif error.code == 403:
            detail = (
                "GitHub denied this request. Check repository access, Administration: read "
                "permission for ruleset details, and API rate limits."
            )
        elif error.code == 429:
            detail = (
                "GitHub rate limits this request. Check the Retry-After or "
                "X-RateLimit-Reset response header before retrying."
            )
        elif error.code == 404:
            detail = (
                "Check the repository name and whether the configured token can access it."
            )
        else:
            detail = "Check GitHub API availability and repository access."
        raise PolicyCheckError(
            f"GitHub API returned HTTP {error.code} for {path}. {detail}"
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", None)
        if isinstance(reason, str):
            detail = reason
        else:
            detail = type(error).__name__
        raise PolicyCheckError(f"GitHub API request failed for {path}: {detail}.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PolicyCheckError(f"GitHub API returned invalid JSON for {path}.") from None


def _rule_map(ruleset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        return {}
    return {
        rule["type"]: rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("type"), str)
    }


def _pattern_matches_default_branch(pattern: Any, branch_ref: str) -> bool:
    if isinstance(pattern, str) and pattern in {"~ALL", "~DEFAULT_BRANCH"}:
        return True
    return isinstance(pattern, str) and fnmatch.fnmatchcase(branch_ref, pattern)


def _targets_default_branch(ruleset: dict[str, Any], default_branch: str) -> bool:
    conditions = ruleset.get("conditions")
    ref_name = conditions.get("ref_name") if isinstance(conditions, dict) else None
    if not isinstance(ref_name, dict):
        return False
    included = ref_name.get("include")
    excluded = ref_name.get("exclude", [])
    if not isinstance(included, list) or not isinstance(excluded, list):
        return False

    branch_ref = f"refs/heads/{default_branch}"
    includes_default = any(_pattern_matches_default_branch(item, branch_ref) for item in included)
    excludes_default = any(_pattern_matches_default_branch(item, branch_ref) for item in excluded)
    return includes_default and not excludes_default


def audit_repository(
    repository: str,
    *,
    ruleset_name: str = "Protect main",
    required_check: str = "validate",
    review_mode: str = "solo",
    api_get: Callable[[str], Any] | None = None,
) -> tuple[str, list[str]]:
    """Return a short scope summary and all policy deviations found."""
    if review_mode not in {"solo", "team"}:
        raise PolicyCheckError("review_mode must be 'solo' or 'team'.")
    get = api_get or get_json
    parts = repository.split("/")
    if len(parts) != 2 or any(not part or part in {".", ".."} for part in parts):
        raise PolicyCheckError("Repository must use owner/name format.")
    owner, name = (urllib.parse.quote(part, safe="") for part in parts)
    repo_path = f"repos/{owner}/{name}"

    metadata = get(repo_path)
    if not isinstance(metadata, dict) or not isinstance(metadata.get("default_branch"), str):
        raise PolicyCheckError("Repository metadata did not include a default branch.")
    default_branch = metadata["default_branch"]
    if not default_branch:
        raise PolicyCheckError("Repository metadata contained an empty default branch.")
    encoded_branch = urllib.parse.quote(default_branch, safe="")
    branch = get(f"{repo_path}/branches/{encoded_branch}")
    if not isinstance(branch, dict):
        raise PolicyCheckError("GitHub returned an invalid default-branch response.")

    findings: list[str] = []
    if branch.get("protected") is not True:
        findings.append(f"Default branch `{default_branch}` is not reported as protected.")

    summaries = get(f"{repo_path}/rulesets?includes_parents=true")
    if not isinstance(summaries, list):
        raise PolicyCheckError("GitHub returned an invalid ruleset list.")
    matches = [
        item
        for item in summaries
        if isinstance(item, dict) and item.get("name") == ruleset_name
    ]
    if not matches:
        findings.append(f"Required ruleset `{ruleset_name}` was not found.")
        return f"{repository} (default branch `{default_branch}`)", findings
    if len(matches) != 1:
        findings.append(f"Ruleset name `{ruleset_name}` is ambiguous ({len(matches)} matches).")
        return f"{repository} (default branch `{default_branch}`)", findings

    ruleset_id = matches[0].get("id")
    if not isinstance(ruleset_id, (int, str)):
        raise PolicyCheckError(f"Ruleset `{ruleset_name}` did not include a valid ID.")
    ruleset = get(f"{repo_path}/rulesets/{ruleset_id}")
    if not isinstance(ruleset, dict):
        raise PolicyCheckError(f"GitHub returned an invalid `{ruleset_name}` ruleset.")

    if ruleset.get("target") != "branch":
        findings.append(f"Ruleset `{ruleset_name}` does not target branches.")
    if ruleset.get("enforcement") != "active":
        findings.append(f"Ruleset `{ruleset_name}` is not active.")
    if not _targets_default_branch(ruleset, default_branch):
        findings.append(
            f"Ruleset `{ruleset_name}` does not include the default branch `{default_branch}`."
        )
    if "bypass_actors" not in ruleset:
        raise PolicyCheckError(
            f"Ruleset `{ruleset_name}` response did not include bypass actors. "
            "Set the POLICY_AUDIT_TOKEN Actions secret to a fine-grained token "
            "with Administration: read access to this repository."
        )
    bypass_actors = ruleset["bypass_actors"]
    # GitHub Actions has returned JSON null for an empty bypass list, while the
    # same public endpoint returns []; both representations mean no actors.
    if bypass_actors is None:
        bypass_actors = []
    if not isinstance(bypass_actors, list):
        raise PolicyCheckError(
            f"Ruleset `{ruleset_name}` response contained an invalid bypass-actor list."
        )
    if bypass_actors:
        findings.append(f"Ruleset `{ruleset_name}` has one or more bypass actors configured.")

    rules = _rule_map(ruleset)
    for rule_type, label in (
        ("deletion", "branch deletion block"),
        ("non_fast_forward", "force-push block"),
        ("pull_request", "pull-request requirement"),
    ):
        if rule_type not in rules:
            findings.append(f"Ruleset `{ruleset_name}` is missing the {label}.")

    # GitHub PR authors cannot approve their own PRs. A solo maintainer cannot
    # meet an independent-review requirement until a second human joins.
    # Still fail closed for invalid GitHub API values in either mode.
    pr_rule = rules.get("pull_request")
    pr_parameters = pr_rule.get("parameters") if pr_rule else None
    approval_count = (
        pr_parameters.get("required_approving_review_count")
        if isinstance(pr_parameters, dict)
        else None
    )
    if type(approval_count) is not int or approval_count < 0:
        findings.append(
            f"Ruleset `{ruleset_name}` has an invalid required approving PR review "
            "count; expected a non-negative integer."
        )
    elif review_mode == "team" and approval_count < 1:
        findings.append(
            f"Ruleset `{ruleset_name}` does not require at least one approving "
            "PR review. CI success alone is not an independent approval."
        )

    status_rule = rules.get("required_status_checks")
    status_parameters = status_rule.get("parameters") if status_rule else None
    statuses = (
        status_parameters.get("required_status_checks")
        if isinstance(status_parameters, dict)
        else None
    )
    if not isinstance(statuses, list) or not any(
        isinstance(status, dict) and status.get("context") == required_check
        for status in statuses
    ):
        findings.append(
            f"Ruleset `{ruleset_name}` does not require the `{required_check}` status check."
        )
    elif status_parameters.get("strict_required_status_checks_policy") is not True:
        findings.append(
            f"Ruleset `{ruleset_name}` does not require branches to be up to date before merging."
        )

    scanning_rule = rules.get("code_scanning")
    scanning_parameters = scanning_rule.get("parameters") if scanning_rule else None
    scanning_tools = (
        scanning_parameters.get("code_scanning_tools")
        if isinstance(scanning_parameters, dict)
        else None
    )
    codeql = None
    if isinstance(scanning_tools, list):
        codeql = next(
            (
                tool
                for tool in scanning_tools
                if isinstance(tool, dict) and tool.get("tool") == "CodeQL"
            ),
            None,
        )
    if not codeql:
        findings.append(f"Ruleset `{ruleset_name}` has no CodeQL scanning threshold.")
    else:
        if codeql.get("security_alerts_threshold") != "high_or_higher":
            findings.append("CodeQL must block high-or-higher security alerts.")
        if codeql.get("alerts_threshold") != "errors":
            findings.append("CodeQL must block findings at the error threshold.")

    return f"{repository} (default branch `{default_branch}`)", findings


def write_step_summary(status: str, scope: str, findings: list[str] | None = None) -> None:
    """Append the audit result to GitHub Actions' per-run summary when available."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = ["## Repository policy audit", "", f"- Status: **{status}**", f"- Scope: {scope}"]
    if findings:
        lines.extend(["", "Findings:", *[f"- {finding}" for finding in findings]])
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub owner/name (defaults to GITHUB_REPOSITORY).",
    )
    parser.add_argument("--ruleset-name", default="Protect main")
    parser.add_argument("--required-check", default="validate")
    parser.add_argument(
        "--review-mode", choices=("solo", "team"), default="solo",
        help="solo permits zero PR approvals; team requires at least one independent approval.",
    )
    arguments = parser.parse_args(argv)
    if not arguments.repository:
        parser.error("--repository or GITHUB_REPOSITORY is required")

    try:
        scope, findings = audit_repository(
            arguments.repository,
            ruleset_name=arguments.ruleset_name,
            required_check=arguments.required_check,
            review_mode=arguments.review_mode,
        )
    except PolicyCheckError as error:
        print(f"Repository policy audit could not complete: {error}", file=sys.stderr)
        write_step_summary("inconclusive", arguments.repository, [str(error)])
        return 2

    if findings:
        print(f"Repository policy drift detected for {scope}:")
        for finding in findings:
            print(f"- {finding}")
        write_step_summary("drift detected", scope, findings)
        return 1

    print(f"Repository policy audit passed for {scope} (review mode: {arguments.review_mode}).")
    if arguments.review_mode == "solo":
        print(
            "ADVISORY: Solo mode permits zero required PR approvals. "
            "CI success cannot replace an independent human review; "
            "protect production with a separately configured deployment approval."
        )
    print(
        "Checked branch protection, active ruleset scope, required checks, PR, "
        "deletion, force-push, review-mode policy, and CodeQL rules."
    )
    write_step_summary("passed", scope)
    return 0


if __name__ == "__main__":
    sys.exit(main())
