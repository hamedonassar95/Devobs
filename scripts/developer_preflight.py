#!/usr/bin/env python3
"""Read-only developer environment preflight for documented local checks.

This tool checks whether documented local verification commands have their
tool and repository prerequisites. It never runs those commands, installs
anything, starts containers, calls cloud tools, reads environment variable
values, or reads secrets. Version probes use a fixed allowlist and only the
parsed version is retained; unexpected probe output is never printed.

Official references for the probe boundary and flags used here:

- Python --version: https://docs.python.org/3/using/cmdline.html#cmdoption-version
- Node.js --version: https://nodejs.org/api/cli.html#node---version
- Git --version: https://git-scm.com/docs/git#Documentation/git.txt---version
- Docker --version: https://docs.docker.com/reference/cli/docker/version/
- Terraform version: https://developer.hashicorp.com/terraform/cli/commands/version
- npm --version: https://docs.npmjs.com/cli/v7/commands/npm-version
- Bandit version via distribution metadata:
  https://docs.python.org/3/library/importlib.metadata.html#importlib.metadata.version
- Executable lookup without invocation: https://docs.python.org/3/library/shutil.html#shutil.which
- Bounded subprocess boundary: https://docs.python.org/3/library/subprocess.html#subprocess.run
"""
from __future__ import annotations

import argparse
from importlib import metadata
import json
import pathlib
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed allowlisted version probes only, no shell
import sys

SCHEMA_VERSION = 1
STATUSES = frozenset(("VERIFIED", "BLOCKED", "UNVERIFIED"))
EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_FAILURE = 2
VERSION_TIMEOUT_SECONDS = 10
PROBE_PATTERN = re.compile(r"\d+\.\d+(?:\.\d+)?\Z")

TOOL_SPECS = (
    {
        "id": "python",
        "label": "Python",
        "executables": ("python", "python3"),
        "version_args": ("--version",),
        "distribution": None,
    },
    {
        "id": "node",
        "label": "Node.js",
        "executables": ("node",),
        "version_args": ("--version",),
        "distribution": None,
    },
    {
        "id": "git",
        "label": "Git",
        "executables": ("git",),
        "version_args": ("--version",),
        "distribution": None,
    },
    {
        "id": "docker",
        "label": "Docker",
        "executables": ("docker",),
        "version_args": ("--version",),
        "distribution": None,
    },
    {
        "id": "terraform",
        "label": "Terraform",
        "executables": ("terraform",),
        "version_args": ("version",),
        "distribution": None,
    },
    {
        "id": "npm",
        "label": "npm",
        "executables": ("npm",),
        "version_args": ("--version",),
        "distribution": None,
    },
    {
        "id": "bandit",
        "label": "Bandit",
        "executables": (),
        "version_args": (),
        "distribution": "bandit",
    },
)

VERSION_PATTERNS = {
    "python": re.compile(r"Python\s+(\d+\.\d+(?:\.\d+)?)"),
    "node": re.compile(r"v(\d+\.\d+(?:\.\d+)?)"),
    "git": re.compile(r"git version\s+(\d+\.\d+(?:\.\d+)?)"),
    "docker": re.compile(r"Docker version\s+(\d+\.\d+(?:\.\d+)?)"),
    "terraform": re.compile(r"Terraform\s+v?(\d+\.\d+(?:\.\d+)?)"),
    "npm": re.compile(r"(\d+\.\d+(?:\.\d+)?)"),
}

ALLOWED_VERSION_PROBES = frozenset(
    tuple((executable,) + spec["version_args"])
    for spec in TOOL_SPECS
    for executable in spec["executables"]
)

COMMAND_SPECS = (
    {
        "id": "python_targeted_tests",
        "command": 'python -m unittest discover -s tests -p "test_developer_preflight.py" -v',
        "source": "docs/agents/DEVELOPER_PREFLIGHT.md",
        "required_tools": ("python",),
        "required_paths": ("tests", "tests/test_developer_preflight.py"),
    },
    {
        "id": "python_full_suite",
        "command": 'python -m unittest discover -s tests -p "test_*.py" -v',
        "source": "docs/ai-quality-gate.md",
        "required_tools": ("python",),
        "required_paths": ("tests",),
    },
    {
        "id": "python_compileall",
        "command": "python -m compileall -q scripts",
        "source": "docs/agents/DEVELOPER_PREFLIGHT.md",
        "required_tools": ("python",),
        "required_paths": ("scripts",),
    },
    {
        "id": "git_diff_check",
        "command": "git diff --check",
        "source": "docs/agents/AGENT_TASK_STATUS_REPORT.md",
        "required_tools": ("git",),
        "required_paths": (".git",),
    },
    {
        "id": "console_tests",
        "command": "npm test",
        "source": "apps/ai-intelligence-console/README.md",
        "required_tools": ("node", "npm"),
        "required_paths": (
            "apps/ai-intelligence-console/package.json",
            "apps/ai-intelligence-console/package-lock.json",
        ),
    },
    {
        "id": "console_lint",
        "command": "npm run lint",
        "source": "apps/ai-intelligence-console/README.md",
        "required_tools": ("node", "npm"),
        "required_paths": (
            "apps/ai-intelligence-console/package.json",
            "apps/ai-intelligence-console/package-lock.json",
        ),
    },
    {
        "id": "console_build",
        "command": "npm run build",
        "source": "apps/ai-intelligence-console/README.md",
        "required_tools": ("node", "npm"),
        "required_paths": (
            "apps/ai-intelligence-console/package.json",
            "apps/ai-intelligence-console/package-lock.json",
        ),
    },
    {
        "id": "bandit_scan",
        "command": "python -m bandit -r scripts tools -x scripts/check_site.py",
        "source": "docs/agents/AGENT_TASK_STATUS_REPORT.md",
        "required_tools": ("python", "bandit"),
        "required_paths": ("scripts", "tools", "scripts/check_site.py"),
    },
    {
        "id": "terraform_fmt_check",
        "command": "terraform -chdir=infra/terraform fmt -check",
        "source": "infra/terraform/README.md",
        "required_tools": ("terraform",),
        "required_paths": ("infra/terraform",),
    },
    {
        "id": "terraform_validate",
        "command": "terraform -chdir=infra/terraform validate",
        "source": "infra/terraform/README.md",
        "required_tools": ("terraform",),
        "required_paths": ("infra/terraform",),
    },
)


def default_version_probe(argv):
    """Run one fixed, allowlisted version probe and return sanitized output."""
    probe = tuple(str(arg) for arg in argv)
    if not probe:
        raise ValueError("version_probe_not_allowlisted")
    executable = pathlib.PurePath(probe[0]).name
    lowered = executable.lower()
    for suffix in (".cmd", ".bat", ".exe"):
        if lowered.endswith(suffix):
            executable = executable[:-len(suffix)]
            lowered = executable.lower()
            break
    normalized = (executable,) + probe[1:]
    if normalized not in ALLOWED_VERSION_PROBES:
        raise ValueError("version_probe_not_allowlisted")
    completed = subprocess.run(  # nosec B603 - fixed argv, no shell, no env passed
        list(probe),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=VERSION_TIMEOUT_SECONDS,
        check=False,
        shell=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def default_distribution_version(name):
    """Return an installed distribution version without exposing its metadata."""
    if name != "bandit":
        raise ValueError("distribution_not_allowlisted")
    return metadata.version(name)


def _valid_version(value):
    return isinstance(value, str) and bool(PROBE_PATTERN.fullmatch(value.strip()))


def _extract_version(tool_id, stdout):
    pattern = VERSION_PATTERNS.get(tool_id)
    if pattern is None or not isinstance(stdout, str):
        return None
    first_line = stdout.splitlines()[0] if stdout.splitlines() else ""
    match = pattern.search(first_line.strip())
    if match is None:
        return None
    version = match.group(1)
    return version if _valid_version(version) else None


def _probe_tool(spec, which, run_version_probe, distribution_version):
    entry = {
        "id": spec["id"],
        "label": spec["label"],
        "status": "UNVERIFIED",
        "version": None,
        "probe": None,
        "reason": None,
    }
    distribution = spec["distribution"]
    if distribution is not None:
        entry["probe"] = "distribution:" + distribution
        try:
            version = distribution_version(distribution)
        except Exception:
            entry["status"] = "BLOCKED"
            entry["reason"] = "distribution_not_found"
            return entry
        if not _valid_version(version):
            entry["reason"] = "unexpected_version_output"
            return entry
        entry["status"] = "VERIFIED"
        entry["version"] = version.strip()
        return entry

    executable = None
    resolved_path = None
    for candidate in spec["executables"]:
        try:
            found = which(candidate)
        except Exception:
            entry["status"] = "UNVERIFIED"
            entry["reason"] = "probe_error"
            return entry
        if found:
            executable = candidate
            resolved_path = str(found)
            break
    if executable is None or resolved_path is None:
        entry["status"] = "BLOCKED"
        entry["reason"] = "executable_not_found"
        return entry

    probe = (executable,) + tuple(spec["version_args"])
    entry["probe"] = " ".join(probe)
    try:
        result = run_version_probe((resolved_path,) + tuple(spec["version_args"]))
        returncode, stdout, _stderr = result
    except Exception:
        entry["reason"] = "probe_error"
        return entry
    if returncode != 0:
        entry["status"] = "BLOCKED"
        entry["reason"] = "version_probe_failed"
        return entry
    version = _extract_version(spec["id"], stdout)
    if version is None:
        entry["reason"] = "unexpected_version_output"
        return entry
    entry["status"] = "VERIFIED"
    entry["version"] = version
    return entry


def _check_command(spec, tools, path_exists, errors):
    missing_paths = []
    for relative in spec["required_paths"]:
        try:
            present = bool(path_exists(relative))
        except Exception:
            present = False
            errors.append("path_check_failed")
        if not present:
            missing_paths.append(relative)

    missing_tools = [
        tool_id for tool_id in spec["required_tools"]
        if tools[tool_id]["status"] == "BLOCKED"
    ]
    unverified_tools = [
        tool_id for tool_id in spec["required_tools"]
        if tools[tool_id]["status"] == "UNVERIFIED"
    ]
    if missing_tools:
        status, reason = "BLOCKED", "required_tool_unavailable"
    elif missing_paths:
        status, reason = "BLOCKED", "required_path_missing"
    elif unverified_tools:
        status, reason = "UNVERIFIED", "required_tool_unverified"
    else:
        status, reason = "UNVERIFIED", "not_executed_by_preflight"
    return {
        "id": spec["id"],
        "command": spec["command"],
        "source": spec["source"],
        "status": status,
        "reason": reason,
        "required_tools": list(spec["required_tools"]),
        "missing_tools": missing_tools,
        "unverified_tools": unverified_tools,
        "missing_paths": missing_paths,
        "executed": False,
    }


def build_report(
    repo_root=None,
    which=shutil.which,
    run_version_probe=default_version_probe,
    distribution_version=default_distribution_version,
    path_exists=None,
    platform_name=None,
):
    """Build a fail-closed, sanitized prerequisite report without running checks."""
    root = pathlib.Path(repo_root) if repo_root is not None else pathlib.Path.cwd()
    if path_exists is None:
        def path_exists(relative):
            return (root / relative).exists()

    errors = []
    tools = [
        _probe_tool(spec, which, run_version_probe, distribution_version)
        for spec in TOOL_SPECS
    ]
    tools_by_id = {item["id"]: item for item in tools}
    commands = [
        _check_command(spec, tools_by_id, path_exists, errors)
        for spec in COMMAND_SPECS
    ]
    entries = tools + commands
    statuses = [entry["status"] for entry in entries]
    overall_status = "BLOCKED" if "BLOCKED" in statuses else "UNVERIFIED"
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "READ_ONLY",
        "repository_root": str(root),
        "platform": platform_name if platform_name is not None else platform.system(),
        "overall_status": overall_status,
        "commands_executed": False,
        "environment_values_read": False,
        "tools": tools,
        "documented_commands": commands,
        "summary": {
            "verified": sum(status == "VERIFIED" for status in statuses),
            "blocked": sum(status == "BLOCKED" for status in statuses),
            "unverified": sum(status == "UNVERIFIED" for status in statuses),
        },
        "errors": errors,
    }


def exit_code(report):
    """Map the overall status to an exit code; unknown values fail closed."""
    status = report.get("overall_status") if isinstance(report, dict) else None
    if status == "UNVERIFIED":
        return EXIT_OK
    if status == "BLOCKED":
        return EXIT_BLOCKED
    return EXIT_FAILURE


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--repo",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Existing local Devobs checkout to inspect (read-only)",
    )
    args = parser.parse_args(argv)
    try:
        report = build_report(repo_root=args.repo)
        code = exit_code(report)
    except Exception:
        report = {
            "schema_version": SCHEMA_VERSION,
            "mode": "READ_ONLY",
            "overall_status": "BLOCKED",
            "commands_executed": False,
            "environment_values_read": False,
            "tools": [],
            "documented_commands": [],
            "summary": {"verified": 0, "blocked": 1, "unverified": 0},
            "errors": ["unexpected_failure"],
        }
        code = EXIT_FAILURE
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
