"""Behavioral tests for isolated, path-safe multi-repository orchestration."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify import multi_repo as mr  # noqa: E402


def write_graph(path, source_file="app.py"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "app", "source_file": source_file, "label": "app"},
                    {"id": "app_main", "source_file": source_file, "label": "main()"},
                ],
                "edges": [
                    {
                        "source": "app",
                        "target": "app_main",
                        "relation": "contains",
                        "confidence": "EXTRACTED",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


class FakeExtraction:
    def __init__(self, graph_path, source_before=None, source_after=None):
        self.graph_path = graph_path
        self.graph_sha256 = "b" * 64
        self.graph_bytes = 512
        self.elapsed_ms = 12
        self.tool_version = mr.PINNED_GRAPHIFY_VERSION
        self.source_before = source_before or {"kind": "directory", "digest": "same"}
        self.source_after = source_after or {"kind": "directory", "digest": "same"}
        self.argv = ("graphify", "extract")

    def as_dict(self):
        return {
            "source_unchanged": self.source_before == self.source_after,
        }


class FakeRunner:
    def __init__(self, binary="graphify", version=mr.PINNED_GRAPHIFY_VERSION, timeout=900):
        self.binary = binary
        self.version = version
        self.fail_tags = set()
        self.sensitive_tags = set()
        self.current_tag = None
        self.calls = []

    def verify_version(self):
        return self.version

    def extract(self, source, output_root, force=False, excludes=mr.DEFAULT_EXCLUDES):
        tag = pathlib.Path(output_root).name
        self.current_tag = tag
        self.calls.append(("extract", tag, tuple(excludes)))
        if tag in self.fail_tags:
            raise mr.RepositoryIntelligenceError("graphify_extract_failed exit=1 stderr_sha256=deadbeef")
        graph = pathlib.Path(output_root) / "graphify-out" / "graph.json"
        source_file = ".env" if tag in self.sensitive_tags else "app.py"
        write_graph(graph, source_file)
        return FakeExtraction(graph)

    def search(self, graph_path, kind, term=None, term2=None, depth=2):
        self.calls.append(("search", pathlib.Path(graph_path).parent.parent.name, kind, term))
        return {
            "kind": kind,
            "status": "ok",
            "exit_code": 0,
            "elapsed_ms": 4,
            "result": "synthetic",
        }


class MultiRepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devobs-graphify-multi-")
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.primary = self.base / "primary"
        self.portfolio = self.base / "portfolio"
        self.index_root = self.base / "indexes"
        self.report_path = self.base / "report.json"
        for root in (self.primary, self.portfolio, self.index_root):
            root.mkdir()
        for name in ("alpha", "beta", "empty"):
            source = self.primary / name
            source.mkdir()
            if name != "empty":
                (source / "app.py").write_text("def main(): return 1\n", encoding="utf-8")
        self.manifest = self.base / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "policy": mr.POLICY_ID,
                    "repositories": [
                        {
                            "tag": "alpha",
                            "github": "owner/alpha",
                            "directory": "alpha",
                            "source_root": "primary",
                            "enabled": True,
                            "search_terms": ["main"],
                        },
                        {
                            "tag": "beta",
                            "github": "owner/beta",
                            "directory": "beta",
                            "source_root": "primary",
                            "enabled": True,
                        },
                        {
                            "tag": "empty",
                            "github": "owner/empty",
                            "directory": "empty",
                            "source_root": "primary",
                            "enabled": True,
                        },
                        {
                            "tag": "off",
                            "github": "owner/off",
                            "directory": "alpha",
                            "source_root": "primary",
                            "enabled": False,
                            "reason": "not_authorized_yet",
                        },
                        {
                            "tag": "gamma",
                            "github": "owner/gamma",
                            "directory": "gamma",
                            "source_root": "portfolio",
                            "enabled": True,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.runner = FakeRunner()

    def run_cli(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = mr.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def invoke(self, extra=None):
        argv = [
            "run",
            "--manifest",
            str(self.manifest),
            "--index-root",
            str(self.index_root),
            "--source-root",
            f"primary={self.primary}",
            "--source-root",
            f"portfolio={self.portfolio}",
            "--json-out",
            str(self.report_path),
        ]
        argv.extend(extra or [])
        with mock.patch.object(mr, "GraphifyRunner", lambda *a, **k: self.runner):
            return self.run_cli(argv)

    def test_manifest_validate_lists_all_repositories(self):
        code, stdout, stderr = self.run_cli(["validate", "--manifest", str(self.manifest)])
        self.assertEqual((code, stderr), (0, ""))
        document = json.loads(stdout)
        self.assertEqual(len(document["repositories"]), 5)
        self.assertEqual(document["repositories"][0]["tag"], "alpha")

    def test_manifest_rejects_duplicate_tag(self):
        document = json.loads(self.manifest.read_text(encoding="utf-8"))
        document["repositories"][1]["tag"] = "alpha"
        self.manifest.write_text(json.dumps(document), encoding="utf-8")
        code, _stdout, stderr = self.run_cli(["validate", "--manifest", str(self.manifest)])
        self.assertEqual(code, 2)
        self.assertIn("manifest_invalid_or_duplicate_tag", stderr)

    def test_run_isolates_failed_repository_and_reports_statuses(self):
        self.runner.fail_tags = {"beta"}
        code, _stdout, stderr = self.invoke()
        self.assertEqual((code, stderr), (3, ""))
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        statuses = {item["tag"]: item["status"] for item in report["repositories"]}
        self.assertEqual(statuses, {
            "alpha": "success",
            "beta": "blocked",
            "empty": "skipped",
            "off": "skipped",
            "gamma": "blocked",
        })
        self.assertEqual(report["summary"], {"success": 1, "blocked": 2, "skipped": 2, "total": 5})

    def test_run_skips_tree_without_indexable_source(self):
        code, _stdout, _stderr = self.invoke()
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        empty = next(item for item in report["repositories"] if item["tag"] == "empty")
        self.assertEqual((code, empty["reason"]), (3, "no_indexable_source"))

    def test_run_blocks_sensitive_source_file(self):
        self.runner.sensitive_tags = {"alpha"}
        self.invoke()
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        alpha = next(item for item in report["repositories"] if item["tag"] == "alpha")
        self.assertEqual(alpha["reason"], "sensitive_source_file_indexed")
        self.assertEqual(alpha["sensitive_source_file_count"], 2)

    def test_report_contains_no_absolute_local_paths(self):
        self.invoke()
        payload = self.report_path.read_text(encoding="utf-8")
        self.assertNotIn(str(self.base), payload)
        self.assertNotIn(str(self.index_root), payload)

    def test_run_records_search_and_impact(self):
        self.invoke()
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        alpha = next(item for item in report["repositories"] if item["tag"] == "alpha")
        self.assertEqual(len(alpha["searches"]), 1)
        self.assertEqual(alpha["searches"][0]["term"], "main")
        self.assertEqual(len(alpha["impact"]["matched_node_id_sha256"]), 64)

    def test_run_refuses_index_root_inside_source(self):
        with mock.patch.object(mr, "GraphifyRunner", lambda *a, **k: self.runner):
            with self.assertRaises(mr.RepositoryIntelligenceError):
                mr.run(
                    mr.load_manifest(self.manifest)[1],
                    {"primary": self.primary, "portfolio": self.portfolio},
                    {},
                    self.primary / "alpha" / "index",
                    None,
                    "graphify",
                )

    def test_empty_source_file_is_not_a_privacy_violation(self):
        document = {
            "nodes": [
                {"source_file": ""},
                {"source_file": None},
                {"source_file": "app.py"},
            ]
        }
        count = mr._sensitive_source_file_count(document, self.primary / "alpha")
        self.assertEqual(count, 0)

    def test_repo_spec_as_dict_is_logical_only(self):
        spec = mr.load_manifest(self.manifest)[1][0]
        self.assertNotIn(str(self.primary), json.dumps(spec.as_dict()))


if __name__ == "__main__":
    unittest.main()
