"""CLI-level behavior tests with isolated subprocess doubles."""
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

from tools.graphify import repository_intelligence as ri  # noqa: E402


def stats():
    return ri.GraphStats(
        node_count=2,
        edge_count=1,
        edge_key="edges",
        relation_counts={"contains": 1},
        confidence_counts={"EXTRACTED": 1},
        relation_confidence_counts={"contains": {"EXTRACTED": 1}},
        source_file_count=1,
        orphan_node_ids=(),
        dangling_edge_count=0,
        cycle_back_edges=0,
        cycle_samples=(),
    )


class FakeExtraction:
    def __init__(self, graph_path):
        self.graph_path = graph_path
        self.graph_sha256 = "a" * 64
        self.graph_bytes = 100
        self.stats = stats()
        self.elapsed_ms = 25
        self.tool_version = ri.PINNED_GRAPHIFY_VERSION
        self.source_before = {"kind": "directory", "digest": "before"}
        self.source_after = {"kind": "directory", "digest": "before"}
        self.argv = ("graphify", "extract")

    def as_dict(self):
        return {
            "graph_path": str(self.graph_path),
            "graph_sha256": self.graph_sha256,
            "graph_bytes": self.graph_bytes,
            "stats": self.stats.as_dict(),
            "elapsed_ms": self.elapsed_ms,
            "source_unchanged": True,
        }


class FakeCliRunner:
    def __init__(self, binary="graphify", version=ri.PINNED_GRAPHIFY_VERSION, timeout=900):
        self.binary = binary
        self.version = version
        self.timeout = timeout
        self.calls = []

    def verify_version(self):
        return self.version

    def extract(self, source, output_root, force=False, excludes=ri.DEFAULT_EXCLUDES):
        self.calls.append(("extract", str(source), str(output_root), force))
        graph = pathlib.Path(output_root) / "graphify-out" / "graph.json"
        graph.parent.mkdir(parents=True, exist_ok=True)
        graph.write_text(
            json.dumps(
                {
                    "nodes": [
                        {"id": "calc", "source_file": "calc.py", "label": "calc.py"},
                        {"id": "calc_add", "source_file": "calc.py", "label": "add()"},
                    ],
                    "edges": [
                        {
                            "source": "calc",
                            "target": "calc_add",
                            "relation": "contains",
                            "confidence": "EXTRACTED",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return FakeExtraction(graph)

    def search(self, graph_path, kind, term=None, term2=None, depth=2):
        self.calls.append(("search", str(graph_path), kind, term, depth))
        return {
            "kind": kind,
            "term": term,
            "status": "ok",
            "exit_code": 0,
            "elapsed_ms": 5,
            "result": "synthetic answer",
        }

    def merge_graphs(self, graph_paths, output_path):
        self.calls.append(("merge", [str(path) for path in graph_paths], str(output_path)))
        return {"native_graphify_feature": True, "output_path": str(output_path)}


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devobs-graphify-cli-")
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        (self.source / "calc.py").write_text("def add(): return 1\n", encoding="utf-8")
        self.output = self.base / "out"

    def run_cli(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = ri.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_build_writes_report_outside_source(self):
        report_path = self.output / "report.json"
        with mock.patch.object(ri, "GraphifyRunner", FakeCliRunner):
            code, stdout, stderr = self.run_cli(
                [
                    "build",
                    "--source",
                    str(self.source),
                    "--output-root",
                    str(self.output),
                    "--json-out",
                    str(report_path),
                ]
            )
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(stdout, "")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["product"]["pinned_version"], ri.PINNED_GRAPHIFY_VERSION)
        self.assertEqual(report["graph"]["stats"]["node_count"], 2)

    def test_build_refuses_report_inside_source(self):
        with mock.patch.object(ri, "GraphifyRunner", FakeCliRunner):
            code, _stdout, stderr = self.run_cli(
                [
                    "build",
                    "--source",
                    str(self.source),
                    "--output-root",
                    str(self.output),
                    "--json-out",
                    str(self.source / "report.json"),
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("report_path_overlaps_source", stderr)

    def test_search_command_prints_structured_result(self):
        graph = self.base / "graph.json"
        graph.write_text(
            json.dumps(
                {
                    "nodes": [{"id": "a"}],
                    "edges": [],
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.object(ri, "GraphifyRunner", FakeCliRunner):
            code, stdout, stderr = self.run_cli(
                ["search", "--graph", str(graph), "--kind", "query", "--term", "needle"]
            )
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["result"], "synthetic answer")

    def test_impact_maps_changed_file_to_graph_nodes(self):
        graph = self.output / "graphify-out" / "graph.json"
        graph.parent.mkdir(parents=True)
        graph.write_text(
            json.dumps(
                {
                    "nodes": [
                        {"id": "calc", "source_file": "calc.py"},
                        {"id": "calc_add", "source_file": "calc.py"},
                    ],
                    "edges": [],
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.object(ri, "GraphifyRunner", FakeCliRunner):
            code, stdout, stderr = self.run_cli(
                ["impact", "--graph", str(graph), "--changed-file", "calc.py"]
            )
        self.assertEqual((code, stderr), (0, ""))
        result = json.loads(stdout)
        self.assertEqual(result["matched_node_ids"], ["calc", "calc_add"])
        self.assertEqual(len(result["results"]), 2)

    def test_benchmark_reports_extraction_and_search_latency(self):
        with mock.patch.object(ri, "GraphifyRunner", FakeCliRunner):
            code, stdout, stderr = self.run_cli(
                [
                    "benchmark",
                    "--source",
                    str(self.source),
                    "--output-root",
                    str(self.output),
                    "--iterations",
                    "2",
                    "--search-term",
                    "add",
                ]
            )
        self.assertEqual((code, stderr), (0, ""))
        report = json.loads(stdout)
        self.assertEqual(len(report["runs"]), 2)
        self.assertEqual(report["runs"][0]["elapsed_ms"], 25)
        self.assertEqual(report["searches"][0]["elapsed_ms"], 5)

    def test_cross_repo_refuses_merge_output_inside_source(self):
        config = self.base / "cross.json"
        graph = self.base / "graph.json"
        graph.write_text(json.dumps({"nodes": [{"id": "a"}], "edges": []}), encoding="utf-8")
        config.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repositories": [
                        {"tag": "devobs", "source": str(self.source), "graph": str(graph)}
                    ],
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.object(ri, "GraphifyRunner", FakeCliRunner):
            code, _stdout, stderr = self.run_cli(
                [
                    "cross-repo",
                    "--config",
                    str(config),
                    "--merge-out",
                    str(self.source / "merged.json"),
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("report_path_overlaps_source", stderr)


if __name__ == "__main__":
    unittest.main()
