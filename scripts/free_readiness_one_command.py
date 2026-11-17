#!/usr/bin/env python3
"""Offline coordinator for already-reviewed Devobs free-resource checks.

Only executes a fixed local allowlist of existing repository scripts. No remote
calls, secrets, files written, paid operations, deployment or authorization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess  # nosec B404: fixed local script allowlist; no shell, no inherited environment
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    ("milestone_ledger", "milestone_ledger.py", ("--summary",), (0,)),
    ("free_resource_manifest", "check_free_resource_plan.py", ("--json",), (0,)),
    ("portfolio_candidate_manifest", "portfolio_free_readiness.py", ("--json",), (0,)),
    ("render_supabase_snapshot", "check_free_staging_health.py", ("--json",), (1,)),
    ("render_free_expiry", "check_render_free_expiry.py", ("--json",), (0, 1)),
)


def inspect_offline(root: Path = ROOT, runner=subprocess.run) -> dict:
    """Exit codes prove only execution of local checks; never live readiness."""
    checks = []
    valid = True
    for name, filename, args, accepted in CHECKS:
        path = root / "scripts" / filename
        # Reject missing or symlinked entrypoints and do not execute outside root.
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            code = None
        else:
            try:
                proc = runner(
                    [sys.executable, str(path), *args],
                    cwd=root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
                    timeout=25,
                    check=False,
                )
                code = proc.returncode
            except (OSError, subprocess.SubprocessError, ValueError):
                code = None
        ok = type(code) is int and code in accepted
        valid &= ok
        checks.append({
            "check": name,
            "state": (
                "INVALID_OR_UNAVAILABLE" if not ok else
                "REVIEW_REQUIRED" if name == "render_supabase_snapshot" or
                (name == "render_free_expiry" and code == 1) else
                "VALIDATED_OFFLINE"
            ),
        })
    return {
        "status": "REVIEW_REQUIRED" if valid else "INVALID_CHECKS",
        "scope": "devobs-free-offline-only",
        "checks": checks,
        "external_providers_contacted": False,
        "other_repositories_queried": False,
        "live_integration_verified": False,
        "production_ready": False,
        "paid_activation_authorized": False,
        "automatic_merge_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = inspect_offline()
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(result["status"] + ": five local checks; no live or production authorization")
        for check in result["checks"]:
            print(check["check"] + ": " + check["state"])
    return 1 if result["status"] == "REVIEW_REQUIRED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
