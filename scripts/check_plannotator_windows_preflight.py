#!/usr/bin/env python3
"""Read-only, fail-closed Windows preflight for an OPTIONAL local Plannotator review.

No installers, downloaded code, agent calls, subprocesses, secrets, hooks,
configuration changes, cloud requests, or production actions.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys

REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    ".codex/config.toml",
    "docs/integrations/PLANNOTATOR_CODEX_REVIEW.md",
)


def inspect(
    repo: Path,
    *,
    system_name: str,
    python_version: tuple[int, int],
    which,
    environ: dict[str, str],
    home: Path,
) -> dict:
    """Return sanitized prerequisite results. Do not execute discovered binaries."""
    checks: dict[str, str] = {}

    def record(name: str, ready: bool) -> None:
        checks[name] = "PASS" if ready else "BLOCKED"

    record("native_windows", system_name == "Windows")
    record("python_3_12_plus", python_version >= (3, 12))
    record("repository_directory", repo.is_dir() and (repo / ".git").exists())
    record("expected_repository_files", all((repo / name).is_file() for name in REQUIRED_FILES))
    record("git_on_path", bool(which("git")))
    record("plannotator_on_path_unexecuted", bool(which("plannotator")))

    # Presence checks only: hook contents and HOME/CODEX_HOME are never printed.
    record("repository_hooks_absent", not (repo / ".codex/hooks.json").exists())
    codex_home = environ.get("CODEX_HOME")
    if codex_home:
        path = Path(codex_home)
        valid_codex_home = path.is_absolute()
    else:
        path = home / ".codex"
        valid_codex_home = True
    record("codex_home_path_valid", valid_codex_home)
    record("user_hooks_absent", valid_codex_home and not (path / "hooks.json").exists())

    # Do not mutate the operator's environment; report presence of opt-in flags only.
    record("sharing_disabled", environ.get("PLANNOTATOR_SHARE") == "disabled")
    record("remote_mode_disabled", environ.get("PLANNOTATOR_REMOTE", "").lower() in ("", "0", "false"))

    ready = all(value == "PASS" for value in checks.values())
    return {
        "result": "PREREQUISITES_PRESENT_RUNTIME_UNVERIFIED" if ready else "BLOCKED",
        "checks": checks,
        "installation_performed": False,
        "hooks_enabled": False,
        "runtime_verified": False,
        "production_approved": False,
        "next_step": (
            "Manually review a synthetic local Markdown file with a trusted binary; "
            "do not activate hooks or share links."
            if ready else
            "Review BLOCKED checks locally. Do not install, enable hooks, or run an untrusted binary."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = inspect(
            args.repo,
            system_name=platform.system(),
            python_version=sys.version_info[:2],
            which=shutil.which,
            environ=os.environ,
            home=Path.home(),
        )
    except (OSError, ValueError, TypeError):
        result = {"result": "BLOCKED", "error": "Local prerequisite inspection failed",
                  "installation_performed": False, "runtime_verified": False}
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("PLANNOTATOR_WINDOWS_PREFLIGHT: " + result["result"])
        for name, status in result.get("checks", {}).items():
            print("  " + name + ": " + status)
        print(result.get("next_step", "Manual review required."))
    return 0 if result["result"] == "PREREQUISITES_PRESENT_RUNTIME_UNVERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
