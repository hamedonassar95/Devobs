"""Host-capability discovery shared by cross-platform tests.

These helpers only probe capabilities; they never weaken production checks.
Tests that need a capability call the matching ``require_*`` helper so a
missing host feature produces an explicit, narrow skip instead of a misleading
product failure.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from typing import Protocol, runtime_checkable

_REQUIRED_OPEN_FLAGS = ("O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "O_NONBLOCK")


@runtime_checkable
class _SkipCapable(Protocol):
    def skipTest(self, reason: str) -> None: ...


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
