#!/usr/bin/env python3
"""Read-only gate for a faithful GitHub -> GitLab merge-request replica.

Exit 0 means GitLab's merge method can preserve source commit identity,
not that source SHA/branch protection, transfer or owner approval was checked.
Exit 2 means fail closed (including a merge method that adds commits).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API_URL = "https://gitlab.com/api/v4/projects/89037773"
PROJECT_ID = 89037773
PROJECT_PATH = "hamedonassar95/Devobs"
MAX_RESPONSE = 65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def load_public_project() -> bytes:
    """No credentials, redirects or mutable endpoints; only fixed public metadata."""
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(API_URL, headers={"Accept": "application/json"}, method="GET")
    with opener.open(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError("unexpected_http_status")
        content = response.read(MAX_RESPONSE + 1)
        if not content or len(content) > MAX_RESPONSE:
            raise ValueError("invalid_response_size")
        return content


def audit(raw: bytes) -> tuple[dict[str, object], int]:
    """Reject missing, malformed, mismatched or unauditable project evidence."""
    blocked = {"status": "BLOCKED", "reason": "unverified_project_metadata",
               "write_performed": False, "gitlab_pipeline_started": False}
    if type(raw) is not bytes or len(raw) > MAX_RESPONSE or not raw:
        return blocked, 2
    try:
        data = json.loads(raw.decode("utf-8", "strict"))
    except (ValueError, UnicodeError):
        return blocked, 2
    if (type(data) is not dict or type(data.get("id")) is not int
            or data["id"] != PROJECT_ID or data.get("path_with_namespace") != PROJECT_PATH
            or data.get("default_branch") != "main" or data.get("visibility") != "public"):
        return blocked, 2
    method = data.get("merge_method")
    if method not in ("ff", "merge", "rebase_merge"):
        return blocked, 2
    if method != "ff":
        return {"status": "BLOCKED", "reason": "merge_method_creates_merge_commit",
                "merge_method": method, "write_performed": False,
                "gitlab_pipeline_started": False}, 2
    return {"status": "REVIEW_REQUIRED", "reason": "fast_forward_merge_method_configured",
            "merge_method": "ff", "write_performed": False,
            "gitlab_pipeline_started": False,
            "approval_required_for_replica_transfer": True}, 0


def main() -> int:
    try:
        raw = load_public_project()
        result, code = audit(raw)
    except (OSError, ValueError, urllib.error.URLError):
        result, code = {"status": "BLOCKED", "reason": "public_metadata_unavailable",
                        "write_performed": False, "gitlab_pipeline_started": False}, 2
    except Exception:
        result, code = {"status": "BLOCKED", "reason": "unexpected_failure",
                        "write_performed": False, "gitlab_pipeline_started": False}, 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    sys.exit(main())
