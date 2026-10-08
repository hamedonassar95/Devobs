#!/usr/bin/env python3
"""Validate a manually supplied Phase 8B patch against live Phase 8A evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.phase8_live_planner import evaluate_live
from scripts.recovery_patch_guard import evaluate as evaluate_patch


def prepare(live_record: dict, payload: dict) -> dict:
    plan = evaluate_live(live_record)
    if not plan.get("eligible") or plan.get("status") != "ELIGIBLE":
        return {"allowed": False, "status": "DENY", "reason": "live Phase 8A evidence is not eligible"}

    if not isinstance(payload, dict) or set(payload) != {"files"}:
        return {"allowed": False, "status": "DENY", "reason": "patch payload must contain only a files array"}
    files = payload.get("files")
    if not isinstance(files, list):
        return {"allowed": False, "status": "DENY", "reason": "files must be an array"}

    paths = []
    total_bytes = 0
    prepared_files = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            return {"allowed": False, "status": "DENY", "reason": "each file needs exactly path and content"}
        path, content = item["path"], item["content"]
        if not isinstance(path, str) or not isinstance(content, str) or not content:
            return {"allowed": False, "status": "DENY", "reason": "file path/content is invalid or empty"}
        size = len(content.encode("utf-8"))
        total_bytes += size
        if size > 100_000 or total_bytes > 200_000:
            return {"allowed": False, "status": "DENY", "reason": "patch content exceeds the size limit"}
        paths.append(path)
        prepared_files.append({"path": path, "content": content})

    guarded = evaluate_patch({
        "planner_status": plan["status"],
        "branch": plan["proposal"]["branch"],
        "base_branch": "main",
        "files": paths,
    })
    if not guarded.allowed:
        return {"allowed": False, "status": "DENY", "reason": guarded.reason}

    return {
        "allowed": True,
        "status": "READY",
        "branch": plan["proposal"]["branch"],
        "incident_number": plan["evidence"]["incident_number"],
        "run_id": plan["evidence"]["incident_run_id"],
        "files": prepared_files,
        "final_state": "PENDING HUMAN APPROVAL",
    }


def main() -> int:
    try:
        live = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        result = prepare(live, payload)
    except (IndexError, OSError, json.JSONDecodeError):
        result = {"allowed": False, "status": "DENY", "reason": "invalid or unreadable patch input"}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
