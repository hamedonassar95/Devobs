"""Host-capability discovery shared by cross-platform tests.

These helpers only probe capabilities; they never weaken production checks.
Tests that need a capability call the matching ``require_*`` helper so a
missing host feature produces an explicit, narrow skip instead of a misleading
product failure.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
import tempfile
from typing import Protocol, runtime_checkable

_REQUIRED_OPEN_FLAGS = ("O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "O_NONBLOCK")


@runtime_checkable
class _SkipCapable(Protocol):
    def skipTest(self, reason: str) -> None: ...


def to_bash_path(path: str | os.PathLike[str]) -> str:
    """Convert a native path to the POSIX form Git Bash understands."""
    value = os.fspath(path)
    if os.name != "nt":
        return value
    normalized = value.replace("\\", "/")
    drive = re.match(r"^([A-Za-z]):/(.*)$", normalized)
    if drive:
        return f"/{drive.group(1).lower()}/{drive.group(2)}"
    return normalized


def find_bash() -> str | None:
    """Return an absolute Bash path, including the Git Bash installed on Windows."""
    candidates = [shutil.which("bash")]
    if os.name == "nt":
        for base in (
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramW6432"),
            os.environ.get("ProgramFiles(x86)"),
        ):
            if base:
                candidates.append(str(Path(base) / "Git" / "bin" / "bash.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def has_secure_open_capability() -> bool:
    """Report whether the POSIX open flags used by the adapter are available."""
    return all(hasattr(os, flag) for flag in _REQUIRED_OPEN_FLAGS) and (
        os.open in os.supports_dir_fd
    )


def symlink_creation_supported() -> bool:
    """Probe whether the current process can create symlinks in a temp dir."""
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "target"
        link = Path(directory) / "link"
        target.write_text("probe", encoding="utf-8")
        try:
            link.symlink_to(target)
        except (AttributeError, NotImplementedError, OSError):
            return False
        return True


def fifo_creation_supported() -> bool:
    """Report whether os.mkfifo exists on this host."""
    return hasattr(os, "mkfifo")


def executable_mode_bit_supported() -> bool:
    """Probe whether chmod exposes POSIX executable mode bits on this host."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "executable-probe"
        path.write_text("probe", encoding="utf-8")
        try:
            path.chmod(0o755)
            return bool(path.stat().st_mode & stat.S_IXUSR)
        except OSError:
            return False


def write_python_cli_shim(directory: str | os.PathLike[str], name: str,
                          script: str | os.PathLike[str]) -> Path:
    """Write a POSIX shell shim that runs a Python CLI with the test interpreter."""
    script_path = Path(script)
    if not script_path.is_file():
        raise FileNotFoundError(script_path)
    shim = Path(directory) / name
    body = "#!/bin/sh\n" + " ".join(
        (
            "exec",
            shlex.quote(sys.executable),
            shlex.quote(os.fspath(script_path)),
            '"$@"',
        )
    ) + "\n"
    shim.write_bytes(body.encode("utf-8"))
    shim.chmod(0o755)
    return shim


def write_python3_shim(directory: str | os.PathLike[str]) -> Path:
    """Write a python3 shim that uses the active Python instead of WindowsApps."""
    shim = Path(directory) / "python3"
    body = "#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n'
    shim.write_bytes(body.encode("utf-8"))
    shim.chmod(0o755)
    return shim


def require_bash(case: _SkipCapable) -> str:
    bash = find_bash()
    if bash is None:
        case.skipTest("bash is required for this shell contract test")
    return bash


def require_secure_open(case: _SkipCapable) -> None:
    if not has_secure_open_capability():
        case.skipTest("POSIX secure-open flags are unavailable on this host")


def require_symlink_creation(case: _SkipCapable) -> None:
    if not symlink_creation_supported():
        case.skipTest("symlink creation requires Developer Mode or elevation on Windows")


def require_fifo_creation(case: _SkipCapable) -> None:
    if not fifo_creation_supported():
        case.skipTest("os.mkfifo is unavailable on this host")


def require_executable_mode_bit(case: _SkipCapable) -> None:
    if not executable_mode_bit_supported():
        case.skipTest("POSIX executable mode bits are unavailable on this host")
