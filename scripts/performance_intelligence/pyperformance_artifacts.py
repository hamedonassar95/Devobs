"""Pinned source and wheelhouse verification for the pyperformance adapter."""
from __future__ import annotations

import email.parser
import hashlib
import importlib.metadata
import os
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile

from performance_intelligence.pyperformance_contract import (
    PY_PERFORMANCE_ARCHIVE_SHA256,
    PY_PERFORMANCE_ARCHIVE_URL,
    PY_PERFORMANCE_COMMIT,
    PY_PERFORMANCE_VERSION,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "requirements-performance-suite-toolchain.lock"
SOURCE_LOCK_PATH = ROOT / "requirements-performance-suite-source.lock"
HASH_RE = re.compile(r"--hash=sha256:([0-9a-f]{64})\Z")
REQ_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9!+_.-]+)\s+(.+)$")
ALLOWED_PACKAGES = {
    "packaging": "26.4", "pyperf": "2.11.0", "psutil": "7.2.2",
    "setuptools": "84.2.1", "wheel": "0.48.0",
}
POSIX_INHERITED_PIP = (
    "PIP_NO_INDEX", "PIP_FIND_LINKS", "PIP_CONFIG_FILE", "PIP_CACHE_DIR",
    "PIP_DISABLE_PIP_VERSION_CHECK", "PIP_NO_INPUT",
)
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_BYTES = 40 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 1000


class PyPerformanceValidationError(ValueError):
    """Fixed, non-sensitive validation error."""


class PyPerformanceExecutionError(RuntimeError):
    """Fixed error for bounded suite execution failures."""


def _normalise_package(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_suite_toolchain_lock(lock_path: pathlib.Path = LOCK_PATH) -> dict[str, tuple[str, frozenset[str]]]:
    """Read the small committed hash lock without importing pip internals."""
    root = ROOT.resolve()
    result: dict[str, tuple[str, frozenset[str]]] = {}
    active: set[pathlib.Path] = set()

    def read(path: pathlib.Path) -> None:
        resolved = path.resolve(strict=True)
        if resolved != root and root not in resolved.parents:
            raise PyPerformanceValidationError("lock_include_outside_repository")
        if resolved in active:
            raise PyPerformanceValidationError("lock_include_cycle")
        active.add(resolved)
        try:
            physical = resolved.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            raise PyPerformanceValidationError("suite_lock_unavailable") from None
        logical: list[str] = []
        pending = ""
        for line in physical:
            cleaned = line.split("#", 1)[0].strip()
            if not cleaned:
                continue
            continued = cleaned.endswith("\\")
            pending += " " + cleaned[:-1].strip() if continued else " " + cleaned
            if not continued:
                logical.append(pending.strip())
                pending = ""
        if pending:
            raise PyPerformanceValidationError("invalid_suite_lock_continuation")
        for line in logical:
            if line.startswith("-r "):
                relative = pathlib.Path(line[3:].strip())
                if relative.is_absolute() or ".." in relative.parts:
                    raise PyPerformanceValidationError("invalid_suite_lock_include")
                read(resolved.parent / relative)
                continue
            match = REQ_RE.fullmatch(line)
            if not match:
                raise PyPerformanceValidationError("invalid_suite_lock_requirement")
            name, version, options = match.groups()
            normalized = _normalise_package(name)
            hashes = set()
            for item in options.split():
                hash_match = HASH_RE.fullmatch(item)
                if not hash_match:
                    raise PyPerformanceValidationError("invalid_suite_lock_hash")
                hashes.add(hash_match.group(1))
            if not hashes or normalized in result:
                raise PyPerformanceValidationError("duplicate_or_unhashed_suite_package")
            result[normalized] = (version, frozenset(hashes))
        active.remove(resolved)

    try:
        read(pathlib.Path(lock_path))
    except (OSError, RuntimeError):
        raise PyPerformanceValidationError("suite_lock_unavailable") from None
    if {name: value[0] for name, value in result.items()} != ALLOWED_PACKAGES:
        raise PyPerformanceValidationError("suite_lock_package_set_mismatch")
    return result


def validate_source_lock(lock_path: pathlib.Path = SOURCE_LOCK_PATH) -> None:
    try:
        content = pathlib.Path(lock_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise PyPerformanceValidationError("suite_source_lock_unavailable") from None
    normalized = " ".join(
        line.split("#", 1)[0].strip().removesuffix("\\").strip()
        for line in content.splitlines()
        if line.split("#", 1)[0].strip()
    )
    expected = (
        f"pyperformance @ {PY_PERFORMANCE_ARCHIVE_URL} "
        f"--hash=sha256:{PY_PERFORMANCE_ARCHIVE_SHA256}"
    )
    if normalized != expected:
        raise PyPerformanceValidationError("suite_source_lock_mismatch")


def _wheel_metadata(path: pathlib.Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as wheel:
            candidates = [name for name in wheel.namelist()
                          if len(name.split("/")) == 2 and name.endswith(".dist-info/METADATA")]
            if len(candidates) != 1 or wheel.getinfo(candidates[0]).file_size > 128 * 1024:
                raise PyPerformanceValidationError("invalid_wheel_metadata")
            message = email.parser.Parser().parsestr(wheel.read(candidates[0]).decode("utf-8"))
    except (OSError, UnicodeError, zipfile.BadZipFile, KeyError):
        raise PyPerformanceValidationError("invalid_wheel_artifact") from None
    name, version = message.get("Name"), message.get("Version")
    if not isinstance(name, str) or not isinstance(version, str):
        raise PyPerformanceValidationError("invalid_wheel_metadata")
    return _normalise_package(name), version


def _require_external_temp_path(path: pathlib.Path, *, must_exist: bool) -> pathlib.Path:
    if not isinstance(path, pathlib.Path):
        raise PyPerformanceValidationError("invalid_temporary_path")
    absolute = path.absolute()
    resolved = path.resolve(strict=must_exist)
    temp_root = pathlib.Path(tempfile.gettempdir()).resolve()
    if (absolute != resolved or (resolved != temp_root and temp_root not in resolved.parents)
            or resolved == ROOT or ROOT in resolved.parents):
        raise PyPerformanceValidationError("temporary_path_required")
    return resolved


def validate_wheelhouse(wheelhouse: pathlib.Path) -> dict[str, str]:
    wheelhouse = _require_external_temp_path(wheelhouse, must_exist=True)
    if not wheelhouse.is_dir() or wheelhouse.is_symlink():
        raise PyPerformanceValidationError("invalid_wheelhouse")
    lock = load_suite_toolchain_lock()
    wheel_files = list(wheelhouse.iterdir())
    if (len(wheel_files) != len(ALLOWED_PACKAGES)
            or any(path.is_symlink() or not path.is_file() or path.suffix != ".whl" for path in wheel_files)):
        raise PyPerformanceValidationError("invalid_wheelhouse_contents")
    seen: dict[str, str] = {}
    for path in wheel_files:
        if path.stat().st_size > 100 * 1024 * 1024:
            raise PyPerformanceValidationError("wheelhouse_artifact_size_limit")
        name, version = _wheel_metadata(path)
        if name not in lock or name in seen or version != lock[name][0]:
            raise PyPerformanceValidationError("unapproved_wheel_package")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest not in lock[name][1]:
            raise PyPerformanceValidationError("wheel_hash_mismatch")
        seen[name] = version
    if seen != ALLOWED_PACKAGES:
        raise PyPerformanceValidationError("incomplete_wheelhouse")
    return seen


def verify_source_archive(archive_path: pathlib.Path) -> pathlib.Path:
    archive_path = _require_external_temp_path(archive_path, must_exist=True)
    if archive_path.is_symlink() or not archive_path.is_file() or archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PyPerformanceValidationError("invalid_source_archive")
    digest = hashlib.sha256()
    try:
        with archive_path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError:
        raise PyPerformanceValidationError("source_archive_unavailable") from None
    if digest.hexdigest() != PY_PERFORMANCE_ARCHIVE_SHA256:
        raise PyPerformanceValidationError("source_archive_hash_mismatch")
    return archive_path


def extract_verified_source(archive_path: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    archive_path = verify_source_archive(archive_path)
    destination = _require_external_temp_path(pathlib.Path(destination), must_exist=False)
    if destination.exists() or destination.is_symlink():
        raise PyPerformanceValidationError("source_destination_exists")
    destination.mkdir(parents=True, exist_ok=False)
    expected_prefix = f"pyperformance-{PY_PERFORMANCE_COMMIT}"
    root = destination / expected_prefix
    total = 0
    members_seen = set()
    allowed_links = {
        f"{expected_prefix}/benchmarks": "pyperformance/data-files/benchmarks",
        f"{expected_prefix}/requirements.txt": "pyperformance/requirements/requirements.txt",
    }
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            if not members or len(members) > MAX_ARCHIVE_MEMBERS:
                raise PyPerformanceValidationError("invalid_source_archive_members")
            for member in members:
                pure = pathlib.PurePosixPath(member.name)
                if pure.is_absolute() or any(part in {"..", ""} for part in pure.parts):
                    raise PyPerformanceValidationError("unsafe_source_archive_path")
                if pure.parts[0] != expected_prefix or member.name in members_seen:
                    raise PyPerformanceValidationError("invalid_source_archive_layout")
                members_seen.add(member.name)
                if member.issym() or member.islnk():
                    if allowed_links.get(member.name) != member.linkname:
                        raise PyPerformanceValidationError("unsafe_source_archive_link")
                    continue
                if not (member.isdir() or member.isfile()):
                    raise PyPerformanceValidationError("unsupported_source_archive_entry")
                if member.isfile():
                    total += member.size
                    if member.size < 0 or total > MAX_EXTRACTED_BYTES:
                        raise PyPerformanceValidationError("source_archive_size_limit")
                target = destination.joinpath(*pure.parts)
                if destination.resolve() not in target.resolve().parents and target.resolve() != destination.resolve():
                    raise PyPerformanceValidationError("unsafe_source_archive_path")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        raise PyPerformanceValidationError("source_archive_read_failed")
                    with source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
    except PyPerformanceValidationError:
        raise
    except (OSError, tarfile.TarError, ValueError):
        raise PyPerformanceValidationError("invalid_source_archive") from None
    package_root = root / "pyperformance"
    version_file = package_root / "__init__.py"
    project_file = root / "pyproject.toml"
    if not version_file.is_file() or not project_file.is_file():
        raise PyPerformanceValidationError("source_archive_layout_mismatch")
    try:
        version_text = version_file.read_text(encoding="utf-8")
        project_text = project_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise PyPerformanceValidationError("source_archive_read_failed") from None
    version_tuple = tuple(int(part) for part in PY_PERFORMANCE_VERSION.split("."))
    version_marker = f"VERSION = ({', '.join(map(str, version_tuple))})"
    if version_marker not in version_text or 'name = "pyperformance"' not in project_text:
        raise PyPerformanceValidationError("source_archive_version_mismatch")
    return root


def require_runtime_toolchain() -> None:
    if sys.version_info[:2] != (3, 12):
        raise PyPerformanceExecutionError("python_312_required")
    if os.name != "posix":
        raise PyPerformanceExecutionError("posix_platform_required")
    for package, expected in ALLOWED_PACKAGES.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            raise PyPerformanceExecutionError("suite_toolchain_missing") from None
        if actual != expected:
            raise PyPerformanceExecutionError("suite_toolchain_version_mismatch")


def build_child_environment(work_dir: pathlib.Path, wheelhouse: pathlib.Path,
                            source_root: pathlib.Path) -> dict[str, str]:
    python_dir = str(pathlib.Path(sys.executable).resolve().parent)
    temporary = str(work_dir.resolve())
    return {
        "HOME": temporary,
        "PATH": python_dir + os.pathsep + os.defpath,
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(source_root.resolve()),
        "TMPDIR": temporary,
        "TEMP": temporary,
        "TMP": temporary,
        "PIP_NO_INDEX": "1",
        "PIP_FIND_LINKS": str(wheelhouse.resolve()),
        "PIP_CACHE_DIR": str(work_dir.resolve() / "pip-cache"),
        "PIP_CONFIG_FILE": os.devnull,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
    }
