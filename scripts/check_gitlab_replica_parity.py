#!/usr/bin/env python3
"""Manually compare public Devobs main commit SHAs without authentication or writes.

Exit codes: 0 MATCH, 1 DRIFT, 2 UNKNOWN (fail closed).
Only fixed public GitHub/GitLab branch endpoints are contacted via HTTPS GET.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

GITHUB_BRANCH_URL = "https://api.github.com/repos/hamedonassar95/Devobs/branches/main"
GITLAB_BRANCH_URL = "https://gitlab.com/api/v4/projects/89037773/repository/branches/main"
ALLOWED_ENDPOINTS = {GITHUB_BRANCH_URL: "github", GITLAB_BRANCH_URL: "gitlab"}
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
MAX_RESPONSE_BYTES = 64 * 1024
REQUEST_TIMEOUT_SECONDS = 10


class ParityError(Exception):
    """Safe, fixed error classification; never include untrusted upstream text."""


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _get_json(url: str) -> object:
    """Fetch one allowlisted public API endpoint without tokens or redirects."""
    provider = ALLOWED_ENDPOINTS.get(url)
    if provider is None:
        raise ParityError("invalid_endpoint")
    req = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Devobs-public-parity-readonly"},
        method="GET",
    )
    try:
        with build_opener(_RejectRedirect()).open(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200 or response.geturl() != url:
                raise ParityError(f"{provider}_invalid_response")
            if response.headers.get_content_type() != "application/json":
                raise ParityError(f"{provider}_invalid_response")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except ParityError:
        raise
    except (HTTPError, URLError, OSError, TimeoutError):
        raise ParityError(f"{provider}_unavailable") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ParityError(f"{provider}_invalid_response")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise ParityError(f"{provider}_invalid_response") from None


def _get_sha(response: object, provider: str) -> str:
    if not isinstance(response, dict) or response.get("name") != "main":
        raise ParityError(f"{provider}_invalid_response")
    commit = response.get("commit")
    if not isinstance(commit, dict):
        raise ParityError(f"{provider}_invalid_response")
    sha = commit.get("sha" if provider == "github" else "id")
    if not isinstance(sha, str) or SHA_RE.fullmatch(sha) is None:
        raise ParityError(f"{provider}_invalid_response")
    return sha


def check_parity(fetcher=None) -> dict[str, str]:
    """Return SHA equality, not mirroring configuration or pipeline health."""
    fetch = _get_json if fetcher is None else fetcher
    # A transient merge between reads may result in DRIFT. No atomic snapshot is claimed.
    github_sha = _get_sha(fetch(GITHUB_BRANCH_URL), "github")
    gitlab_sha = _get_sha(fetch(GITLAB_BRANCH_URL), "gitlab")
    return {
        "status": "MATCH" if github_sha == gitlab_sha else "DRIFT",
        "github_sha": github_sha,
        "gitlab_sha": gitlab_sha,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print a machine-readable public-SHA result")
    args = parser.parse_args(argv)
    try:
        result = check_parity()
        code = 0 if result["status"] == "MATCH" else 1
    except ParityError as error:
        result = {"status": "UNKNOWN", "error": str(error)}
        code = 2
    except Exception:
        # Never echo network exceptions, upstream response bodies, or proxy details.
        result = {"status": "UNKNOWN", "error": "unexpected_failure"}
        code = 2
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    elif result["status"] == "UNKNOWN":
        print(f"UNKNOWN: {result['error']}")
    else:
        print(f"{result['status']}: GitHub main {result['github_sha']} / GitLab main {result['gitlab_sha']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
