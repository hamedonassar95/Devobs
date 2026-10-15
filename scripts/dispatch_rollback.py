"""Dispatch and wait for the dedicated rollback workflow run."""
from __future__ import annotations
import json
import os
import time
from urllib.parse import quote
from urllib.request import Request, urlopen


def api_request(url: str, token: str, method: str = "GET", body: dict | None = None):
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "devobs-one-click-deploy"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = Request(url, headers=headers, data=data, method=method)
    with urlopen(request, timeout=20) as response:  # nosec B310: URL is built from the GitHub API base and fixed route.
        payload = response.read()
        return response.status, json.loads(payload) if payload else None


def dispatch_and_wait() -> tuple[str, str]:
    token = os.environ["GH_TOKEN"]
    repository = os.environ["GH_REPOSITORY"]
    rollback_sha = os.environ["ROLLBACK_SHA"]
    rollback_tag = os.environ["ROLLBACK_TAG"]
    base = f"{os.environ.get('GH_API_URL', 'https://api.github.com').rstrip('/')}/repos/{repository}"
    workflow = quote("rollback-pages.yml", safe="")
    before = time.time()
    api_request(f"{base}/actions/workflows/{workflow}/dispatches", token, "POST", {
        "ref": rollback_sha,
        "inputs": {"release_tag": rollback_tag, "confirmation": "ROLLBACK"},
    })
    created_after = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(before - 5))
    deadline = before + 18 * 60
    run = None
    while time.time() < deadline:
        _, result = api_request(
            f"{base}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=100", token)
        candidates = [r for r in result.get("workflow_runs", [])
                      if r.get("head_sha") == rollback_sha and r.get("created_at", "") >= created_after]
        if candidates:
            run = max(candidates, key=lambda r: r.get("run_number", 0))
            if run.get("status") == "completed":
                return run.get("conclusion") or "failure", run.get("html_url", "")
        time.sleep(10)
    return "timeout", run.get("html_url", "") if run else ""


def main() -> int:
    try:
        status, run_url = dispatch_and_wait()
    except Exception as exc:
        # Avoid logging exception text: HTTP errors may include request details.
        print(f"::error::Rollback dispatch or monitoring failed ({type(exc).__name__}).")
        status, run_url = "dispatch_failed", ""
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"status={status}\nrun_url={run_url}\n")
    if run_url:
        print(f"Rollback workflow run: {run_url}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
