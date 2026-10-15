"""Dispatch an isolated rollback workflow and return its run link without waiting.

The parent and rollback workflows share the production concurrency group. The
child must be allowed to queue until the parent run exits, so this helper only
confirms dispatch and identifies the queued run.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from urllib.parse import quote
from urllib.request import Request, urlopen


def api_request(url: str, token: str, method: str = "GET", body: dict | None = None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "devobs-one-click-deploy",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = Request(url, headers=headers, data=data, method=method)
    with urlopen(request, timeout=20) as response:  # nosec B310: URL is built from GitHub API base and fixed route.
        payload = response.read()
        return response.status, json.loads(payload) if payload else None


def dispatch_and_find_run() -> tuple[str, str]:
    token = os.environ["GH_TOKEN"]
    repository = os.environ["GH_REPOSITORY"]
    rollback_sha = os.environ["ROLLBACK_SHA"]
    rollback_tag = os.environ["ROLLBACK_TAG"]
    api_base = os.environ.get("GH_API_URL", "https://api.github.com").rstrip("/")
    base = f"{api_base}/repos/{repository}"
    workflow = quote("rollback-pages.yml", safe="")
    dispatch_id = uuid.uuid4().hex
    run_title = f"Rollback Pages / {dispatch_id}"

    # Use the release tag as workflow_dispatch ref. The child validates that
    # the tag still points to this exact SHA before deploying its static site.
    api_request(
        f"{base}/actions/workflows/{workflow}/dispatches",
        token,
        "POST",
        {
            "ref": rollback_tag,
            "inputs": {
                "release_tag": rollback_tag,
                "expected_commit_sha": rollback_sha,
                "confirmation": "ROLLBACK",
                "dispatch_id": dispatch_id,
            },
        },
    )

    # workflow_dispatch returns HTTP 204 without a run ID. The unique run-name
    # lets us find precisely our queued child; do not wait for it to complete.
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        _, result = api_request(
            f"{base}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=100",
            token,
        )
        for run in result.get("workflow_runs", []):
            if run.get("head_sha") == rollback_sha and run.get("display_title") == run_title:
                return "dispatched", run.get("html_url", "")
        time.sleep(3)
    return "accepted", ""


def main() -> int:
    try:
        status, run_url = dispatch_and_find_run()
    except Exception as exc:
        # Avoid logging exception text: API errors can include request details.
        print(f"::error::Rollback workflow dispatch failed ({type(exc).__name__}).")
        status, run_url = "dispatch_failed", ""
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"status={status}\nrun_url={run_url}\n")
    if run_url:
        print(f"Rollback workflow queued: {run_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
