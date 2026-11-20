"""Behavioral tests for the canonical portfolio compatibility layer.

The legacy portfolio CLI and the multi-repo CLI share this implementation. These
tests use synthetic repositories and subprocess doubles; no Graphify binary is
installed or executed.
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify import portfolio as canonical  # noqa: E402
from tools.graphify import portfolio_execution as execution  # noqa: E402


def make_repo(base: pathlib.Path, name: str, *, branch: str = "main", dirty: bool = False) -> pathlib.Path:
    path = base / name
    path.mkdir(parents=True)
    subprocess.run(
        ["git", "init", "-q", "-b", branch, str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Graphify Test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "graphify-test@example.invalid"], check=True, capture_output=True)
    (path / "module.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "module.py"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "synthetic"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "remote", "add", "origin", f"https://github.com/hamedonassar95/{name}.git"],
        check=True,
        capture_output=True,
    )
    if dirty:
        (path / "untracked.txt").write_text("pending\n", encoding="utf-8")
    return path


class FakeRunner:
    def __init__(self, version: str = "graphify 0.9.112", *, create_graph: bool = True) -> None:
        self.version = version
        self.create_graph = create_graph
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv[1:] == ["--version"]:
            return subprocess.CompletedProcess(argv, 0, self.version + "\n", "")
        if self.create_graph and "--out" in argv:
            graph = pathlib.Path(argv[argv.index("--out") + 1]) / "graphify-out" / "graph.json"
            graph.parent.mkdir(parents=True, exist_ok=True)
            graph.write_text(
                json.dumps(
                    {
                        "nodes": [{"id": "a"}, {"id": "b"}],
                        "links": [{"source": "a", "target": "b"}],
                    }
                ),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(argv, 0, "extract ok\n", "")


class CanonicalPortfolioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="devobs-canonical-portfolio-")
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.root = self.base / "portfolio"
        self.root.mkdir()
        self.source = make_repo(self.root, "demo")
        self.output = self.base / "graphs"
        self.repository = canonical.inspect_repository(
            self.source, contract=canonical.LEGACY_PORTFOLIO_CONTRACT
        )

    def test_legacy_contract_preserves_pin_policy_and_canonical_pointer(self) -> None:
        contract = canonical.LEGACY_PORTFOLIO_CONTRACT
        self.assertEqual(contract.policy, "devobs-graphify-portfolio-v1")
        self.assertEqual(contract.pinned_version, "0.9.112")
        self.assertTrue(contract.legacy)
        self.assertEqual(contract.canonical["implementation"], "tools/graphify")
        self.assertEqual(contract.canonical["cli"], "scripts/graphify/multi_repo.py")
        self.assertEqual(contract.canonical["pinned_version"], "0.9.113")

    def test_execute_uses_offline_environment_and_writes_compatible_record(self) -> None:
        runner = FakeRunner()
        record = execution.execute_repository(
            self.repository,
            self.output,
            "graphify",
            contract=canonical.LEGACY_PORTFOLIO_CONTRACT,
            run=runner,
        )
        extraction = [call for call in runner.calls if call[1:2] == ["extract"]]
        self.assertEqual(
            extraction[0],
            [
                "graphify",
                "extract",
                str(self.source.resolve()),
                "--code-only",
                "--out",
                str(self.output.resolve() / "demo" / self.repository.head),
            ],
        )
        self.assertNotIn("--backend", extraction[0])
        self.assertEqual(record["policy"], "devobs-graphify-portfolio-v1")
        self.assertEqual(record["graphify_version"], "0.9.112")
        self.assertEqual(record["status"], "extracted")
        run_record = json.loads(
            (self.output / "demo" / self.repository.head / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(run_record, record)

    def test_version_mismatch_blocks_before_extraction(self) -> None:
        runner = FakeRunner(version="graphify 0.9.200")
        with self.assertRaisesRegex(canonical.PortfolioError, "not the pinned 0.9.112"):
            execution.execute_repository(
                self.repository,
                self.output,
                "graphify",
                contract=canonical.LEGACY_PORTFOLIO_CONTRACT,
                run=runner,
            )
        self.assertEqual([call for call in runner.calls if call[1:2] == ["extract"]], [])
        self.assertFalse(self.output.exists())

    def test_main_reports_legacy_metadata_without_execution(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = execution.main(
                [
                    "--root",
                    str(self.root),
                    "--out-root",
                    str(self.output),
                    "--json",
                ],
                contract=canonical.LEGACY_PORTFOLIO_CONTRACT,
            )
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertIn("deprecated", stderr.getvalue().lower())
        self.assertTrue(report["legacy"])
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["graphify"]["expected_version"], "0.9.112")
        self.assertEqual(report["canonical"]["pinned_version"], "0.9.113")
        self.assertFalse(self.output.exists())

if __name__ == "__main__":
    unittest.main()
