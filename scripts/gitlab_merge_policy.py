#!/usr/bin/env python3
"""Read-only classification of GitLab merge-request policy, NOT Git push policy.

Exit 0 means project metadata was validated; MR mode may still be unsuitable.
Exit 2 means unverified/malformed metadata (fail closed).
No result authorizes Git push, changing protected branches, or a merge.
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
    # Merge methods govern merge requests only, NOT an authorized direct Git
    # fast-forward push. In either case, no repository mutation is approved.
    mr_path = "FF_MR_POLICY_ONLY" if method == "ff" else "MR_ADDS_COMMIT"
    return {"status": "REVIEW_REQUIRED", "mr_path": mr_path,
            "merge_method": method, "direct_git_push": "NOT_EVALUATED",
            "write_performed": False, "gitlab_pipeline_started": False,
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
