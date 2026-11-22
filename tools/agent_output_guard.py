"""Offline, read-only policy gate for explicitly selected local agent artifacts."""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata

# Trusted repository helpers only; never import an input artifact or emit bytecode.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAX_ARTIFACTS = 32
MAX_PATH_CHARS = 4096
SUPPORTED_TYPES = frozenset({".json", ".md", ".txt", ".py", ".yaml", ".yml", ".toml", ".diff", ".patch"})
STATUS_ORDER = ("PASS", "BLOCKED", "FAIL")  # Position is the CLI exit code.
PRIVATE_KEY_MARKER = re.compile("PRIVATE KEY-----", re.IGNORECASE)


class Rejection(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


class QuietParser(argparse.ArgumentParser):
    def error(self, _message):
        raise Rejection("FAIL", "INVALID_ARGUMENTS")


def _dependencies():
    from scripts import agentdust_readonly_adapter as reader
    from scripts.ci_failure_intelligence import SECRET_PATTERNS
    from tools.graphify import common as path_policy
    return reader, SECRET_PATTERNS, path_policy


def _report(status, artifacts=None, reason=None):
    return {"schema_version": 1, "policy": "agent-output-guard/1", "status": status,
            "offline": True, "content_redacted": True, "artifacts": artifacts or [],
            "reason_codes": [reason] if reason else []}


def _unsafe_text(text):
    return any(character not in "\t\r\n" and unicodedata.category(character) in {"Cc", "Cf", "Cs"}
               for character in text)


def _credential_like(text, patterns):
    # Reject even truncated headers before the inherited multiline rule can scan
    # repeated BEGIN markers quadratically. No credential values are retained.
    if PRIVATE_KEY_MARKER.search(text) is not None:
        return True
    return any(pattern.search(text) is not None for pattern in patterns)


def _strict_json(text, reader):
    try:
        reader._preflight_json_limits(text)
        value = json.loads(text, object_pairs_hook=reader._object_without_duplicate_keys,
                           parse_constant=reader._reject_nonstandard_constant,
                           parse_int=reader._parse_bounded_integer)
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, str) and _unsafe_text(item):
                raise ValueError
            elif isinstance(item, float) and not math.isfinite(item):
                raise ValueError
        # Decode escaped credential-bearing keys as well as string values.
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (ValueError, RecursionError, reader.AdapterError,
            reader._DuplicateKeyError, reader._IntegerLimitError):
        raise Rejection("BLOCKED", "INVALID_JSON") from None


def _assess_one(workspace, raw_path, reader, patterns, path_policy):
    if (not isinstance(raw_path, str) or not 0 < len(raw_path) <= MAX_PATH_CHARS
            or "\\" in raw_path or ":" in raw_path or _unsafe_text(raw_path)
            or any(character in "\t\r\n" for character in raw_path)
            or Path(raw_path).is_absolute()
            or any(part in {"", ".", ".."} for part in raw_path.split("/"))):
        raise Rejection("BLOCKED", "UNSAFE_PATH")
    path = workspace / raw_path
    if path.suffix.lower() not in SUPPORTED_TYPES:
        raise Rejection("BLOCKED", "UNSUPPORTED_TYPE")
    try:
        excluded = path_policy.is_excluded(path, workspace)
    except (OSError, ValueError, RuntimeError):
        raise Rejection("BLOCKED", "UNSAFE_PATH") from None
    if excluded:
        raise Rejection("BLOCKED", "EXCLUDED_PATH")
    descriptor = reader._open_explicit_regular_file(path)
    try:
        metadata = os.fstat(descriptor)
        if metadata.st_nlink != 1:
            raise Rejection("BLOCKED", "HARDLINK_REJECTED")
        if not metadata.st_mode & 0o444:
            raise Rejection("BLOCKED", "UNREADABLE_FILE")
        raw = reader._read_bounded_report(descriptor)
    finally:
        reader._quiet_close(descriptor)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise Rejection("BLOCKED", "UNEXPECTED_BINARY") from None
    if _unsafe_text(text):
        raise Rejection("BLOCKED", "UNEXPECTED_BINARY")
    normalized = _strict_json(text, reader) if path.suffix.lower() == ".json" else text
    if _credential_like(text, patterns) or (normalized != text and _credential_like(normalized, patterns)):
        raise Rejection("BLOCKED", "CREDENTIAL_PATTERN")


def assess_artifacts(workspace, paths):
    """Return indices and fixed reasons only; no paths, contents or exceptions."""
    try:
        if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_ARTIFACTS:
            raise Rejection("FAIL", "INVALID_ARTIFACT_COUNT")
        root = Path(workspace).absolute()
        if ".." in root.parts or not stat.S_ISDIR(root.lstat().st_mode):
            raise Rejection("FAIL", "INVALID_WORKSPACE")
        reader, patterns, path_policy = _dependencies()
        # Keep known exclusions when a caller chooses a deeper workspace.
        # Agent worktree ancestry is allowed; artifact-relative exclusions remain.
        for part in root.parts:
            if part == ".worktrees":
                continue
            if (part in path_policy._EXCLUDED_PARTS
                    or any(fnmatch.fnmatch(part, pattern)
                           for pattern in path_policy._EXCLUDED_NAME_PATTERNS)):
                raise Rejection("FAIL", "EXCLUDED_WORKSPACE")
        rows = []
        for index, path in enumerate(paths, 1):
            status, codes = "PASS", []
            try:
                _assess_one(root, path, reader, patterns, path_policy)
            except Rejection as error:
                status, codes = error.status, [error.code]
            except reader.AdapterError as error:
                status = "FAIL" if error.code == "secure_open_unavailable" else "BLOCKED"
                codes = [error.code.upper()]
            rows.append({"index": index, "status": status, "reason_codes": codes})
        status = ("FAIL" if any(row["status"] == "FAIL" for row in rows) else
                  "BLOCKED" if any(row["status"] == "BLOCKED" for row in rows) else "PASS")
        return _report(status, rows)
    except Rejection as error:
        return _report(error.status, reason=error.code)
    except OSError:
        return _report("FAIL", reason="WORKSPACE_UNAVAILABLE")
    except Exception:
        return _report("FAIL", reason="INTERNAL_ERROR")


def main(argv=None):
    parser = QuietParser(prog="agent_output_guard.py", description=__doc__, allow_abbrev=False)
    parser.add_argument("--workspace", required=True, help="Trusted artifact-only workspace directory")
    parser.add_argument("artifacts", nargs="+", help="Explicit normalized paths relative to the workspace")
    try:
        arguments = parser.parse_args(argv)
        report = assess_artifacts(arguments.workspace, arguments.artifacts)
    except Rejection as error:
        report = _report(error.status, reason=error.code)
    except Exception:
        report = _report("FAIL", reason="INTERNAL_ERROR")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return STATUS_ORDER.index(report["status"])


if __name__ == "__main__":
    raise SystemExit(main())
