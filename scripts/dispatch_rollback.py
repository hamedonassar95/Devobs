"""Dispatch a rollback supported by historical workflow revisions.

The target release ref can contain an older rollback workflow definition, so
only its original inputs are sent. After GitHub accepts the dispatch, compare
workflow-run IDs before and after to find the new run without blocking on the
shared production concurrency group.
"""
from __future__ import annotations

import json
import os
import time
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
    server_url = os.environ.get("GH_SERVER_URL", "https://github.com").rstrip("/")
    base = f"{api_base}/repos/{repository}"
    workflow = quote("rollback-pages.yml", safe="")
    runs_url = f"{base}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=100"
    workflow_url = f"{server_url}/{repository}/actions/workflows/rollback-pages.yml"

    # Snapshot IDs before dispatch. Only the original input fields are sent,
    # since the workflow file selected by a release tag may be older.
    _, before_result = api_request(runs_url, token)
    existing_ids = {run.get("id") for run in before_result.get("workflow_runs", [])}
    api_request(
        f"{base}/actions/workflows/{workflow}/dispatches",
        token,
        "POST",
        {"ref": rollback_tag, "inputs": {"release_tag": rollback_tag, "confirmation": "ROLLBACK"}},
    )

    # The dispatch endpoint returns 204 rather than the run ID. Do not wait
    # for completion: the child shares the production concurrency group and
    # must start after the parent deployment workflow releases it.
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        _, result = api_request(runs_url, token)
        new_runs = [
            run for run in result.get("workflow_runs", [])
            if run.get("id") not in existing_ids
            and run.get("head_sha") == rollback_sha
            and run.get("event") == "workflow_dispatch"
        ]
        if len(new_runs) == 1:
            return "dispatched", new_runs[0].get("html_url") or workflow_url
        if len(new_runs) > 1:
            # Several same-release runs appeared at once; avoid linking the
            # parent report to a possibly unrelated rollback run.
            return "accepted", workflow_url
        time.sleep(3)
    return "accepted", workflow_url


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
        print(f"Rollback workflow accepted: {run_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
