#!/usr/bin/env python3
"""Read-only classification of GitLab merge-request policy, NOT Git push policy.

Exit 0 means project metadata was validated; MR mode may still be unsuitable.
Exit 2 means unverified/malformed metadata (fail closed).
No result authorizes Git push, changing protected branches, or a merge.

Failure reasons are fixed tokens scoped to a specific field, for example
``missing_field:merge_method`` or ``mismatched_field:path_with_namespace``.
They never include provider-supplied values, so diagnostics stay sanitized.
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

# Field name, required value, required exact type. Checked in this order so a
# failure names the first field that cannot be trusted.
IDENTITY_SPEC = (
    ("id", PROJECT_ID, int),
    ("path_with_namespace", PROJECT_PATH, str),
    ("default_branch", "main", str),
    ("visibility", "public", str),
)
MERGE_METHODS = ("ff", "merge", "rebase_merge")


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


def blocked(reason: str) -> dict[str, object]:
    """Sanitized fail-closed result; ``reason`` is a fixed token, never a value."""
    return {"status": "BLOCKED", "reason": reason,
            "write_performed": False, "gitlab_pipeline_started": False}


def audit(raw: bytes) -> tuple[dict[str, object], int]:
    """Reject missing, malformed, mismatched or unauditable project evidence."""
    if type(raw) is not bytes or not raw:
        return blocked("invalid_payload"), 2
    if len(raw) > MAX_RESPONSE:
        return blocked("response_too_large"), 2
    try:
        data = json.loads(raw.decode("utf-8", "strict"))
    except (ValueError, UnicodeError):
        return blocked("invalid_json"), 2
    if type(data) is not dict:
        return blocked("invalid_payload"), 2
    for name, expected, kind in IDENTITY_SPEC:
        if name not in data:
            return blocked(f"missing_field:{name}"), 2
        value = data[name]
        if type(value) is not kind:
            return blocked(f"wrong_type:{name}"), 2
        if value != expected:
            return blocked(f"mismatched_field:{name}"), 2
    # The merge method governs merge requests only, NOT an authorized direct Git
    # fast-forward push. It is permission-gated in the public project projection,
    # so an absent field is unverifiable, never a default.
    if "merge_method" not in data:
        return blocked("missing_field:merge_method"), 2
    method = data["merge_method"]
    if type(method) is not str:
        return blocked("wrong_type:merge_method"), 2
    if method not in MERGE_METHODS:
        return blocked("unsupported_merge_method"), 2
    # In either case, no repository mutation is approved.
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
        result, code = blocked("public_metadata_unavailable"), 2
    except Exception:
        result, code = blocked("unexpected_failure"), 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    sys.exit(main())
