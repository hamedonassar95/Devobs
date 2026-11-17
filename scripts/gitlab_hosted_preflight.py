#!/usr/bin/env python3
"""Surface a safe GitLab ancestry verdict from a manual public GitHub Actions run.

Exit 0 means a read-only check completed, NEVER that a replica was synchronized.
Exit 2 means BLOCKED, including malformed or inconsistent observations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from gitlab_fast_forward_preflight import PreflightBlocked, check_preflight

SHA = re.compile(r"[0-9a-f]{40}\Z")
SAFE_REASONS = frozenset({
    "checkout_unavailable", "github_unavailable", "gitlab_unavailable",
    "github_invalid_ref", "gitlab_invalid_ref", "invalid_remote_sha",
    "github_commit_not_in_local_checkout", "gitlab_commit_not_in_local_checkout",
    "local_main_not_at_github_sha", "gitlab_main_not_ancestor_do_not_overwrite",
    "git_ancestry_unavailable", "git_unavailable_or_timeout",
    "endpoint_not_allowed", "git_operation_not_allowed",
})


def evaluate(repo: Path, probe=None) -> tuple[dict, int]:
    """Validate a real or synthetic read-only preflight without Git writes."""
    try:
        observed = (probe or check_preflight)(repo)
    except PreflightBlocked as exc:
        code = str(exc)
        return {"status": "BLOCKED", "reason": code if code in SAFE_REASONS else "preflight_blocked",
                "write_performed": False}, 2
    except Exception:
        return {"status": "BLOCKED", "reason": "unexpected_failure", "write_performed": False}, 2

    if (type(observed) is not dict or set(observed) != {"status", "github_sha", "gitlab_sha", "write_performed"}
            or observed["write_performed"] is not False
            or type(observed["github_sha"]) is not str or not SHA.fullmatch(observed["github_sha"])
            or type(observed["gitlab_sha"]) is not str or not SHA.fullmatch(observed["gitlab_sha"])):
        return {"status": "BLOCKED", "reason": "invalid_probe_result", "write_performed": False}, 2

    relation = observed["status"]
    matched = observed["github_sha"] == observed["gitlab_sha"]
    if (relation == "ALREADY_MATCHED" and not matched) or (relation == "FAST_FORWARD_CANDIDATE" and matched) or relation not in {"ALREADY_MATCHED", "FAST_FORWARD_CANDIDATE"}:
        return {"status": "BLOCKED", "reason": "inconsistent_probe_result", "write_performed": False}, 2
    return {
        "status": "ALREADY_MATCHED" if matched else "REVIEW_REQUIRED",
        "observed_relation": relation,
        "github_sha": observed["github_sha"],
        "gitlab_sha": observed["gitlab_sha"],
        "write_performed": False,
        "gitlab_pipeline_started": False,
        "production_gates_changed": False,
        "human_approval_required_for_sync": True,
    }, 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    payload, exit_code = evaluate(args.repo)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
