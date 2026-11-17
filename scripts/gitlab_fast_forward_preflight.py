#!/usr/bin/env python3
"""Read-only preflight for a human-approved GitHub -> GitLab main fast-forward.

Exit 0: ALREADY_MATCHED, 1: FAST_FORWARD_CANDIDATE, 2: BLOCKED.
This script never fetches, pushes, edits refs, reads credentials, or changes remotes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess  # nosec B404 - invoke only reviewed, no-shell Git read commands

GITHUB_URL = "https://github.com/hamedonassar95/Devobs.git"
GITLAB_URL = "https://gitlab.com/hamedonassar95/Devobs.git"
BRANCH_REF = "refs/heads/main"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
TIMEOUT_SECONDS = 20


class PreflightBlocked(Exception):
    """A safe, non-sensitive preflight failure code."""


def _git(*args: str, repo: Path | None = None) -> subprocess.CompletedProcess[str]:
    if not args or args[0] not in {"ls-remote", "rev-parse", "cat-file", "merge-base"}:
        raise PreflightBlocked("git_operation_not_allowed")
    command = ["git", "-c", "credential.helper=", "-c", "core.askPass=",
               "-c", "http.followRedirects=false", *args]
    if repo is not None:
        command[1:1] = ["-C", str(repo)]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    try:
        return subprocess.run(  # nosec B603 - fixed Git executable; validated operations, no shell
            command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
            check=False, env=env, encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        raise PreflightBlocked("git_unavailable_or_timeout") from None


def _remote_head(url: str, label: str) -> str:
    if (url, label) not in ((GITHUB_URL, "github"), (GITLAB_URL, "gitlab")):
        raise PreflightBlocked("endpoint_not_allowed")
    result = _git("ls-remote", "--exit-code", url, BRANCH_REF)
    if result.returncode != 0:
        raise PreflightBlocked(f"{label}_unavailable")
    parts = result.stdout.strip().splitlines()
    if len(parts) != 1:
        raise PreflightBlocked(f"{label}_invalid_ref")
    columns = parts[0].split()
    if len(columns) != 2 or not SHA_PATTERN.fullmatch(columns[0]) or columns[1] != BRANCH_REF:
        raise PreflightBlocked(f"{label}_invalid_ref")
    return columns[0]


def check_preflight(repo: Path, get_remote=_remote_head) -> dict[str, str | bool]:
    """Validate remote tips and local ancestry without modifying any ref."""
    repo = repo.resolve(strict=False)
    if not repo.is_dir():
        raise PreflightBlocked("checkout_unavailable")
    inside = _git("rev-parse", "--is-inside-work-tree", repo=repo)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise PreflightBlocked("checkout_unavailable")

    github_sha = get_remote(GITHUB_URL, "github")
    gitlab_sha = get_remote(GITLAB_URL, "gitlab")
    if not all(isinstance(x, str) and SHA_PATTERN.fullmatch(x) for x in (github_sha, gitlab_sha)):
        raise PreflightBlocked("invalid_remote_sha")
    if github_sha == gitlab_sha:
        return {"status": "ALREADY_MATCHED", "github_sha": github_sha,
                "gitlab_sha": gitlab_sha, "write_performed": False}

    for label, sha in (("github", github_sha), ("gitlab", gitlab_sha)):
        exists = _git("cat-file", "-e", f"{sha}^{{commit}}", repo=repo)
        if exists.returncode != 0:
            raise PreflightBlocked(f"{label}_commit_not_in_local_checkout")

    local_main = _git("rev-parse", "--verify", BRANCH_REF, repo=repo)
    if local_main.returncode != 0 or local_main.stdout.strip() != github_sha:
        raise PreflightBlocked("local_main_not_at_github_sha")

    ancestry = _git("merge-base", "--is-ancestor", gitlab_sha, github_sha, repo=repo)
    if ancestry.returncode == 1:
        raise PreflightBlocked("gitlab_main_not_ancestor_do_not_overwrite")
    if ancestry.returncode != 0:
        raise PreflightBlocked("git_ancestry_unavailable")
    return {"status": "FAST_FORWARD_CANDIDATE", "github_sha": github_sha,
            "gitlab_sha": gitlab_sha, "write_performed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Trusted existing local Devobs checkout")
    parser.add_argument("--json", action="store_true", help="Print only sanitized public SHA statuses")
    args = parser.parse_args(argv)
    try:
        result = check_preflight(args.repo)
        exit_code = 0 if result["status"] == "ALREADY_MATCHED" else 1
    except PreflightBlocked as exc:
        result = {"status": "BLOCKED", "reason": str(exc), "write_performed": False}
        exit_code = 2
    except Exception:
        result = {"status": "BLOCKED", "reason": "unexpected_failure", "write_performed": False}
        exit_code = 2
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"{result['status']}: " + (
            f"GitHub={result['github_sha']} GitLab={result['gitlab_sha']}" if "github_sha" in result
            else result["reason"]
        ))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
