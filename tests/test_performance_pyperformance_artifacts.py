"""Offline tests for source provenance and wheelhouse artifact checks."""
from __future__ import annotations

import hashlib
import io
import os
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from performance_intelligence import pyperformance_artifacts as artifacts  # noqa: E402


class PyPerformanceArtifactTests(unittest.TestCase):
    def test_source_lock_matches_pinned_upstream_revision_and_digest(self):
        artifacts.validate_source_lock()
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "source.lock"
            lock.write_text(
                "pyperformance @ https://invalid.example/source.tar.gz --hash=sha256:" + "0" * 64,
                encoding="utf-8",
            )
            with self.assertRaisesRegex(artifacts.PyPerformanceValidationError, "source_lock_mismatch"):
                artifacts.validate_source_lock(lock)

    def test_archive_digest_symlinks_and_path_escapes_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive = base / "source.tar.gz"
            archive.write_bytes(b"synthetic archive")
            with self.assertRaisesRegex(artifacts.PyPerformanceValidationError, "hash_mismatch"):
                artifacts.verify_source_archive(archive)
            archive.unlink()
            archive.symlink_to(Path(__file__))
            with self.assertRaises(artifacts.PyPerformanceValidationError):
                artifacts.verify_source_archive(archive)

            unsafe = base / "unsafe.tar.gz"
            with tarfile.open(unsafe, "w:gz") as output:
                member = tarfile.TarInfo("../escape.txt")
                payload = b"synthetic"
                member.size = len(payload)
                output.addfile(member, io.BytesIO(payload))
            digest = hashlib.sha256(unsafe.read_bytes()).hexdigest()
            with mock.patch.object(artifacts, "PY_PERFORMANCE_ARCHIVE_SHA256", digest):
                with self.assertRaisesRegex(artifacts.PyPerformanceValidationError, "unsafe_source_archive_path"):
                    artifacts.extract_verified_source(unsafe, base / "extracted")
            self.assertFalse((base / "escape.txt").exists())

    def test_pinned_synthetic_source_archive_extracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive_path = base / "source.tar.gz"
            prefix = f"pyperformance-{artifacts.PY_PERFORMANCE_COMMIT}"
            source_root = base / "input" / prefix
            package = source_root / "pyperformance"
            package.mkdir(parents=True)
            (source_root / "pyproject.toml").write_text('name = "pyperformance"\n', encoding="utf-8")
            (package / "__init__.py").write_text("VERSION = (1, 14, 0)\n", encoding="utf-8")
            with tarfile.open(archive_path, "w:gz") as output:
                output.add(source_root, arcname=prefix)
            digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            with mock.patch.object(artifacts, "PY_PERFORMANCE_ARCHIVE_SHA256", digest):
                extracted = artifacts.extract_verified_source(archive_path, base / "extracted")
            self.assertTrue((extracted / "pyperformance" / "__init__.py").is_file())

    def test_wheelhouse_accepts_only_exact_hash_pinned_runtime_and_build_wheels(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            wheelhouse = base / "wheels"
            wheelhouse.mkdir()
            lock = {}
            for name, version in artifacts.ALLOWED_PACKAGES.items():
                wheel = wheelhouse / f"{name}-{version}-py3-none-any.whl"
                with zipfile.ZipFile(wheel, "w") as output:
                    output.writestr(
                        f"{name}-{version}.dist-info/METADATA",
                        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\n",
                    )
                lock[name] = (version, frozenset({hashlib.sha256(wheel.read_bytes()).hexdigest()}))
            with mock.patch.object(artifacts, "load_suite_toolchain_lock", return_value=lock):
                self.assertEqual(artifacts.validate_wheelhouse(wheelhouse), artifacts.ALLOWED_PACKAGES)

            wheel.unlink()
            unexpected = wheelhouse / "unknown-9.9-py3-none-any.whl"
            unexpected.write_bytes(b"unverified")
            with mock.patch.object(artifacts, "load_suite_toolchain_lock", return_value=lock):
                with self.assertRaises(artifacts.PyPerformanceValidationError):
                    artifacts.validate_wheelhouse(wheelhouse)

    def test_partial_and_unhashed_wheelhouses_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            wheelhouse = Path(temporary) / "wheels"
            wheelhouse.mkdir()
            wheel = wheelhouse / "pyperf-2.11.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as output:
                output.writestr(
                    "pyperf-2.11.0.dist-info/METADATA",
                    "Metadata-Version: 2.1\nName: pyperf\nVersion: 2.11.0\n\n",
                )
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            lock = {
                "pyperf": ("2.11.0", frozenset({digest})),
                "packaging": ("26.4", frozenset({"0" * 64})),
                "psutil": ("7.2.2", frozenset({"1" * 64})),
                "setuptools": ("84.2.1", frozenset({"2" * 64})),
                "wheel": ("0.48.0", frozenset({"3" * 64})),
            }
            with mock.patch.object(artifacts, "load_suite_toolchain_lock", return_value=lock):
                with self.assertRaises(artifacts.PyPerformanceValidationError):
                    artifacts.validate_wheelhouse(wheelhouse)

    def test_explicit_child_environment_does_not_inherit_parent_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            with mock.patch.dict(os.environ, {"API_TOKEN": "do-not-copy", "PIP_INDEX_URL": "https://invalid"}):
                env = artifacts.build_child_environment(base, base / "wheels", base / "source")
        self.assertEqual(env["PIP_NO_INDEX"], "1")
        self.assertEqual(env["PIP_FIND_LINKS"], str(base / "wheels"))
        self.assertIn("PIP_CACHE_DIR", env)
        self.assertNotIn("API_TOKEN", env)
        self.assertNotIn("PIP_INDEX_URL", env)
        self.assertNotIn("GITHUB_TOKEN", env)


if __name__ == "__main__":
    unittest.main()
