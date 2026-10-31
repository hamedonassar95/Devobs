#!/usr/bin/env python3
"""Offline-by-default Codex Docs MCP configuration check.

An optional manual `codex mcp list` probe checks *registration*, NEVER a remote
handshake or a successful MCP tool call. Never echoes raw CLI output or tokens.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
# B404 review: only a fixed argv ["codex", "mcp", "list"] is executed;
# no shell, user-controlled command, provider writes, or raw output disclosure.
import subprocess  # nosec B404
import sys
import tomllib

EXPECTED_NAME = "openaiDeveloperDocs"
EXPECTED_URL = "https://developers.openai.com/mcp"
DEFAULT_CONFIG = pathlib.Path(__file__).resolve().parents[1] / ".codex/config.toml"


class ProbeFailure(ValueError):
    """Missing or unexpected evidence; always fail closed."""


def verify_repository_config(path: pathlib.Path) -> None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ProbeFailure("Codex project configuration is missing or invalid") from exc
    if not isinstance(data, dict) or not isinstance(data.get("mcp_servers"), dict):
        raise ProbeFailure("MCP server declaration is absent")
    docs = data["mcp_servers"].get(EXPECTED_NAME)
    if not isinstance(docs, dict) or docs != {"url": EXPECTED_URL}:
        raise ProbeFailure("Docs MCP must use the exact public URL, with no credentials or extra fields")
    if set(data["mcp_servers"]) != {EXPECTED_NAME}:
        raise ProbeFailure("Unexpected repository-wide MCP server is declared")


def verify_local_codex_registration(*, locate=shutil.which, run=subprocess.run) -> None:
    if not locate("codex"):
        raise ProbeFailure("Codex CLI is unavailable on this device")
    try:
        result = run(
            ["codex", "mcp", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeFailure("Codex MCP listing could not be completed") from exc
    if result.returncode != 0:
        raise ProbeFailure("Codex MCP listing returned a nonzero exit code")
    if not isinstance(result.stdout, str) or not all(
        marker in result.stdout for marker in (EXPECTED_NAME, EXPECTED_URL)
    ):
        raise ProbeFailure("Codex listing did not confirm the configured public Docs MCP endpoint")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--codex-list", action="store_true",
        help="Manually check Codex CLI registration; does NOT test a server handshake",
    )
    args = parser.parse_args(argv)
    try:
        verify_repository_config(args.config)
        if args.codex_list:
            verify_local_codex_registration()
    except ProbeFailure as exc:
        print(f"BLOCKED: {exc}; MCP_RUNTIME_UNVERIFIED", file=sys.stderr)
        return 1
    if args.codex_list:
        print("PASS: Codex CLI lists the expected public Docs MCP URL; MCP_RUNTIME_UNVERIFIED")
    else:
        print("PASS: repository Docs MCP configuration verified offline; MCP_RUNTIME_UNVERIFIED")
    print("NEXT: in a trusted Codex session, run one public docs lookup and review tool evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
