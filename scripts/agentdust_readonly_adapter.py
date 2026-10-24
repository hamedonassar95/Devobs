"""Fail-closed reader for a bounded AgentDust doctor JSON report."""

from __future__ import annotations

import errno
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Sequence

MAX_REPORT_BYTES = 2 * 1024 * 1024
MAX_FINDINGS = 10_000
STATUS_REPORT_VALID = "REPORT_VALID"
COUNT_KEYS = frozenset(
    {"managed", "owned-live", "owned-ended", "likely-owned", "suspect", "unknown"}
)

_ERROR_CODES = frozenset(
    {
        "usage",
        "invalid_path",
        "secure_open_unavailable",
        "path_unavailable",
        "symbolic_link_rejected",
        "not_regular_file",
        "file_changed",
        "file_too_large",
        "read_failed",
        "invalid_utf8",
        "invalid_json",
        "duplicate_json_key",
        "report_not_object",
        "version_mismatch",
        "counts_not_object",
        "count_keys_mismatch",
        "count_values_invalid",
        "findings_not_array",
        "findings_limit_exceeded",
    }
)


class AdapterError(Exception):
    """An input rejection represented by a fixed, non-sensitive code."""

    def __init__(self, code: str) -> None:
        self.code = code if code in _ERROR_CODES else "invalid_json"
        super().__init__(self.code)


class _DuplicateKeyError(Exception):
    pass


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError
        result[key] = value
    return result


def _reject_nonstandard_constant(_value: str) -> None:
    raise ValueError


def _quiet_close(fd: int | None) -> None:
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass


def _open_explicit_regular_file(input_path: str | os.PathLike[str]) -> int:
    try:
        path_value = os.fspath(input_path)
    except (TypeError, ValueError):
        raise AdapterError("invalid_path") from None
    if not isinstance(path_value, str) or not path_value or "\x00" in path_value:
        raise AdapterError("invalid_path")

    required_flags = ("O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "O_NONBLOCK")
    if any(not hasattr(os, flag) for flag in required_flags) or os.open not in os.supports_dir_fd:
        raise AdapterError("secure_open_unavailable")

    directory_fd: int | None = None
    file_fd: int | None = None
    try:
        supplied_path = Path(path_value)
        if ".." in supplied_path.parts:
            raise AdapterError("invalid_path")
        absolute_path = (
            path_value
            if supplied_path.is_absolute()
            else os.path.join(os.getcwd(), path_value)
        )
        parts = Path(absolute_path).parts
        if len(parts) < 2 or parts[0] != os.sep:
            raise AdapterError("invalid_path")

        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory_fd = os.open(os.sep, directory_flags)
        for component in parts[1:-1]:
            try:
                metadata = os.stat(component, dir_fd=directory_fd, follow_symlinks=False)
            except OSError:
                raise AdapterError("path_unavailable") from None
            if stat.S_ISLNK(metadata.st_mode):
                raise AdapterError("symbolic_link_rejected")
            if not stat.S_ISDIR(metadata.st_mode):
                raise AdapterError("path_unavailable")

            next_directory_fd: int | None = None
            try:
                next_directory_fd = os.open(component, directory_flags, dir_fd=directory_fd)
                opened_metadata = os.fstat(next_directory_fd)
                if (opened_metadata.st_dev, opened_metadata.st_ino) != (
                    metadata.st_dev,
                    metadata.st_ino,
                ):
                    raise AdapterError("file_changed")
            except AdapterError:
                _quiet_close(next_directory_fd)
                raise
            except OSError:
                _quiet_close(next_directory_fd)
                raise AdapterError("path_unavailable") from None
            if next_directory_fd is None:
                raise AdapterError("path_unavailable")
            _quiet_close(directory_fd)
            directory_fd = next_directory_fd

        filename = parts[-1]
        try:
            before_open = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            raise AdapterError("path_unavailable") from None
        if stat.S_ISLNK(before_open.st_mode):
            raise AdapterError("symbolic_link_rejected")
        if not stat.S_ISREG(before_open.st_mode):
            raise AdapterError("not_regular_file")

        file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
        try:
            file_fd = os.open(filename, file_flags, dir_fd=directory_fd)
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise AdapterError("symbolic_link_rejected") from None
            raise AdapterError("path_unavailable") from None

        after_open = os.fstat(file_fd)
        if not stat.S_ISREG(after_open.st_mode):
            raise AdapterError("not_regular_file")
        if (after_open.st_dev, after_open.st_ino) != (before_open.st_dev, before_open.st_ino):
            raise AdapterError("file_changed")

        result = file_fd
        file_fd = None
        return result
    except AdapterError:
        raise
    except (OSError, TypeError, ValueError):
        raise AdapterError("path_unavailable") from None
    finally:
        _quiet_close(file_fd)
        _quiet_close(directory_fd)


def _read_bounded_report(fd: int) -> bytes:
    try:
        if os.fstat(fd).st_size > MAX_REPORT_BYTES:
            raise AdapterError("file_too_large")
        contents = bytearray()
        while len(contents) <= MAX_REPORT_BYTES:
            remaining = MAX_REPORT_BYTES + 1 - len(contents)
            chunk = os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            contents.extend(chunk)
        if len(contents) > MAX_REPORT_BYTES:
            raise AdapterError("file_too_large")
        return bytes(contents)
    except AdapterError:
        raise
    except OSError:
        raise AdapterError("read_failed") from None


def _parse_report(raw_report: bytes) -> dict[str, Any]:
    try:
        text = raw_report.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise AdapterError("invalid_utf8") from None

    try:
        report = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except _DuplicateKeyError:
        raise AdapterError("duplicate_json_key") from None
    except (json.JSONDecodeError, RecursionError, ValueError):
        raise AdapterError("invalid_json") from None

    if type(report) is not dict:
        raise AdapterError("report_not_object")
    if type(report.get("version")) is not int or report["version"] != 1:
        raise AdapterError("version_mismatch")

    counts = report.get("counts")
    if type(counts) is not dict:
        raise AdapterError("counts_not_object")
    if set(counts) != COUNT_KEYS:
        raise AdapterError("count_keys_mismatch")
    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise AdapterError("count_values_invalid")

    findings = report.get("findings")
    if type(findings) is not list:
        raise AdapterError("findings_not_array")
    if len(findings) > MAX_FINDINGS:
        raise AdapterError("findings_limit_exceeded")

    return {
        "status_code": STATUS_REPORT_VALID,
        "processes_detected": sum(counts.values()),
        "findings_count": len(findings),
    }


def summarize_report(input_path: str | os.PathLike[str]) -> dict[str, int | str]:
    """Read and validate one explicitly supplied report, returning aggregate data only."""
    fd = _open_explicit_regular_file(input_path)
    try:
        raw_report = _read_bounded_report(fd)
    finally:
        _quiet_close(fd)
    return _parse_report(raw_report)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        sys.stderr.write("adapter_error=usage\n")
        return 2
    try:
        summary = summarize_report(arguments[0])
    except AdapterError as error:
        sys.stderr.write(f"adapter_error={error.code}\n")
        return 2
    sys.stdout.write(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
