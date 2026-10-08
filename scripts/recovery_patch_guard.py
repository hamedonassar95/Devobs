#!/usr/bin/env python3
"""Fail-closed guard for Phase 8B isolated recovery patch preparation."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath

# Phase 8B's initial allowlist is intentionally narrow. Expand only through a
# separately reviewed policy change.
ALLOWED_EXACT = {"index.html"}
ALLOWED_PREFIXES = ("assets/",)
BRANCH_RE = re.compile(r"^recovery/incident-[1-9][0-9]*-[a-z0-9][a-z0-9-]{0,47}$")


@dataclass(frozen=True)
class PatchDecision:
    allowed: bool
    status: str
    reason: str
    final_state: str = "PENDING HUMAN APPROVAL"


def _safe_path(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw or "\\" in raw or raw.startswith("/"):
        return None
    path = PurePosixPath(raw)
    normalized = str(path)
    if raw != normalized or ".." in path.parts or "." in path.parts:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in raw):
        return None
    return normalized


def _allowlisted(path: str) -> bool:
    return path in ALLOWED_EXACT or any(
        path.startswith(prefix) and len(path) > len(prefix)
        for prefix in ALLOWED_PREFIXES
    )


def evaluate(request: dict) -> PatchDecision:
    required = ("planner_status", "branch", "base_branch", "files")
    missing = [key for key in required if key not in request]
    if missing:
        return PatchDecision(False, "DENY", f"missing required fields: {', '.join(missing)}")
    if request["planner_status"] != "ELIGIBLE":
        return PatchDecision(False, "DENY", "recovery planner did not authorize patch preparation")
    if request["base_branch"] != "main":
        return PatchDecision(False, "DENY", "recovery branch must be based on main")
    branch = request["branch"]
    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        return PatchDecision(False, "DENY", "invalid isolated recovery branch name")
    files = request["files"]
    if not isinstance(files, list) or not files:
        return PatchDecision(False, "DENY", "at least one explicit file is required")
    if len(files) > 10:
        return PatchDecision(False, "DENY", "patch scope exceeds 10 files")

    normalized = []
    for raw in files:
        path = _safe_path(raw)
        if path is None:
            return PatchDecision(False, "DENY", f"unsafe path: {raw!r}")
        if not _allowlisted(path):
            return PatchDecision(False, "DENY", f"path is outside the approved allowlist: {path}")
        normalized.append(path)

    if len(set(normalized)) != len(normalized):
        return PatchDecision(False, "DENY", "duplicate file paths are not allowed")
    return PatchDecision(True, "ALLOW", "isolated patch scope passed deterministic guardrails")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request")
    args = parser.parse_args()
    try:
        with open(args.request, encoding="utf-8") as handle:
            request = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        decision = PatchDecision(False, "DENY", f"invalid input: {exc}")
    else:
        decision = evaluate(request)
    print(json.dumps(asdict(decision), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
