#!/usr/bin/env python3
"""Read GitLab default-branch CI states without writing or exposing project identities."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_ORIGIN = "https://gitlab.com/api/v4/"
MAX_RESPONSE_BYTES = 65536
MAX_PROJECTS = 10
KNOWN_STATES = frozenset({
    "created", "waiting_for_resource", "preparing", "pending", "running",
    "success", "failed", "canceled", "skipped", "manual", "scheduled",
})


class AuditError(Exception):
    """A fixed, non-sensitive diagnostic that is safe for CI output."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _get_json(path: str, token: str) -> object:
    # Fixed HTTPS host, GET only, no redirects, and no request body.
    url = API_ORIGIN + path
    request = Request(url, headers={"PRIVATE-TOKEN": token, "Accept": "application/json"}, method="GET")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=10) as response:
            if response.status != 200 or response.geturl() != url:
                raise AuditError("upstream_rejected")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, OSError, TimeoutError):
        raise AuditError("upstream_unavailable") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise AuditError("oversized_response")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise AuditError("invalid_response") from None


def audit_projects(project_ids: list[str], token: str, fetcher=None) -> dict[str, object]:
    """Return status-only records, never project names, paths, tokens, or URLs."""
    if not token or not token.strip():
        raise AuditError("missing_auth")
    if not 1 <= len(project_ids) <= MAX_PROJECTS:
        raise AuditError("invalid_projects")
    if (any(not value.isascii() or not value.isdecimal() or int(value) < 1
            for value in project_ids) or len(set(project_ids)) != len(project_ids)):
        raise AuditError("invalid_projects")
    fetch = _get_json if fetcher is None else fetcher
    results = []
    for slot, project_id in enumerate(project_ids, start=1):
        project = fetch(f"projects/{project_id}", token)
        if not isinstance(project, dict) or project.get("id") != int(project_id):
            raise AuditError("invalid_project_response")
        branch = project.get("default_branch")
        if not isinstance(branch, str) or not branch or len(branch) > 255:
            raise AuditError("invalid_project_response")
        ref = quote(branch, safe="")
        branch_record = fetch(f"projects/{project_id}/repository/branches/{ref}", token)
        if not isinstance(branch_record, dict) or branch_record.get("name") != branch:
            raise AuditError("invalid_branch_response")
        head = branch_record.get("commit")
        sha = head.get("id") if isinstance(head, dict) else None
        if (not isinstance(sha, str) or len(sha) not in (40, 64)
                or any(digit not in "0123456789abcdef" for digit in sha)):
            raise AuditError("invalid_branch_response")
        data = fetch(
            f"projects/{project_id}/pipelines?ref={ref}&per_page=1&order_by=id&sort=desc",
            token,
        )
        if not isinstance(data, list) or len(data) > 1:
            raise AuditError("invalid_pipeline_response")
        state = "missing"
        if data:
            pipeline = data[0]
            if (not isinstance(pipeline, dict)
                    or pipeline.get("project_id") != int(project_id)
                    or pipeline.get("ref") != branch
                    or pipeline.get("status") not in KNOWN_STATES):
                raise AuditError("invalid_pipeline_response")
            state = pipeline["status"] if pipeline.get("sha") == sha else "stale"
        results.append({"slot": slot, "pipeline_state": state})
    return {"schema_version": 1, "all_passed": all(row["pipeline_state"] == "success" for row in results),
            "results": results}


def main() -> int:
    # Values are supplied at execution time, never committed or echoed.
    ids = os.environ.get("GITLAB_PROJECT_IDS", "").split(",")
    token = os.environ.get("GITLAB_READONLY_TOKEN", "")
    try:
        summary = audit_projects(ids, token)
    except AuditError as error:
        print(f"audit_error={error}", file=sys.stderr)
        return 2
    except Exception:
        # In particular, never echo HTTP exception bodies or credentials.
        print("audit_error=unexpected_failure", file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
