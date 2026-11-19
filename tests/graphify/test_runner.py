"""Fail-closed subprocess, pinning and privacy tests for GraphifyRunner."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify import repository_intelligence as ri  # noqa: E402

SENTINEL = "SENTINEL_VALUE_12345"


def graph_json(node_count=1):
    nodes = [
        {"id": f"n{index}", "label": f"file{index}.py", "source_file": f"file{index}.py"}
        for index in range(node_count)
    ]
    edges = (
        [
            {
                "source": "n0",
                "target": "n1",
                "relation": "imports",
                "confidence": "EXTRACTED",
            }
        ]
        if node_count > 1
        else []
    )
    return {"nodes": nodes, "edges": edges}


class FakeRunner(ri.GraphifyRunner):
    """A subprocess double that writes only the expected graph artifacts."""

    def __init__(self, version=ri.PINNED_GRAPHIFY_VERSION, status=0, mutate=False, reported=None):
        self.binary = "graphify"
        self.version = version
        self.timeout = 30
        self.status = status
        self.mutate = mutate
        self.reported = reported or version
        self.calls = []

    def _run(self, args, allowed_codes=frozenset({0}), env=None):
        self.calls.append((list(args), dict(env or {})))
        if args[0] == "--version":
            return subprocess.CompletedProcess(args, 0, f"graphify {self.reported}\n", "")
        if args[0] == "extract":
            if self.mutate:
                source = pathlib.Path(args[1])
                (source / "mutated.txt").write_text("x", encoding="utf-8")
            output = pathlib.Path(args[args.index("--out") + 1]) / "graphify-out"
            output.mkdir(parents=True, exist_ok=True)
            (output / "graph.json").write_text(json.dumps(graph_json(2)), encoding="utf-8")
            return subprocess.CompletedProcess(args, self.status, "extracted\n", "")
        if args[0] == "merge-graphs":
            output = pathlib.Path(args[args.index("--out") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "directed": True,
                        "multigraph": False,
                        "nodes": graph_json(2)["nodes"],
                        "links": graph_json(2)["edges"],
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(args, 0, "merged\n", "")
        if args[0] in {"query", "path", "explain", "affected", "god-nodes", "diagnose"}:
            code = self.status
            if code == 0 and args[0] == "god-nodes":
                return subprocess.CompletedProcess(args, 0, "[]", "")
            if code == 0 and args[0] == "diagnose":
                return subprocess.CompletedProcess(args, 0, '{"summary":{"node_count":2}}', "")
            return subprocess.CompletedProcess(args, code, f"answer for {args[1] if len(args)>1 else ''}\n", "")
        raise AssertionError(f"unexpected args: {args}")


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devobs-graphify-runner-")
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        (self.source / "module.py").write_text("def f(): return 1\n", encoding="utf-8")
        self.output = self.base / "external"

    def test_version_is_pinned(self):
        runner = FakeRunner(reported="0.9.112")
        with self.assertRaisesRegex(ri.GraphifyRunnerError, "version_mismatch"):
            runner.verify_version()
        self.assertEqual(FakeRunner().verify_version(), ri.PINNED_GRAPHIFY_VERSION)

    def test_extract_uses_offline_code_only_invocation(self):
        runner = FakeRunner()
        result = runner.extract(self.source, self.output, excludes=(".env",))
        args, env = runner.calls[0]
        self.assertEqual(args[0], "extract")
        self.assertIn("--code-only", args)
        self.assertIn("--no-cluster", args)
        self.assertIn("--exclude", args)
        self.assertIn(".env", args)
        self.assertEqual(env["GRAPHIFY_BACKEND"], "none")
        self.assertEqual(env["GRAPHIFY_QUERY_LOG_DISABLE"], "1")
        for key in ri.PROVIDER_KEY_VARS:
            self.assertEqual(env[key], "")
        self.assertTrue(result.as_dict()["source_unchanged"])
        self.assertEqual(result.stats.node_count, 2)
        self.assertEqual(result.stats.edge_key, "edges")

    def test_extract_refuses_overlapping_output(self):
        runner = FakeRunner()
        with self.assertRaisesRegex(ri.RepositoryIntelligenceError, "overlaps_source"):
            runner.extract(self.source, self.source / "graphify-out")
        with self.assertRaisesRegex(ri.RepositoryIntelligenceError, "overlaps_source"):
            runner.extract(self.source, self.base)

    def test_extract_fails_on_source_mutation(self):
        runner = FakeRunner(mutate=True)
        with self.assertRaisesRegex(ri.RepositoryIntelligenceError, "source_tree_mutated"):
            runner.extract(self.source, self.output)
        self.assertFalse((self.source / "graphify-out").exists())

    def test_search_maps_graphify_exit_codes(self):
        graph = self.output / "graphify-out" / "graph.json"
        graph.parent.mkdir(parents=True)
        graph.write_text(json.dumps(graph_json(2)), encoding="utf-8")
        ok = FakeRunner().search(graph, "query", "needle")
        self.assertEqual(ok["status"], "ok")
        self.assertEqual(FakeRunner(status=3).search(graph, "query", "needle")["status"], "ambiguous")
        self.assertEqual(FakeRunner(status=4).search(graph, "query", "needle")["status"], "no_match")
        hubs = FakeRunner().search(graph, "god-nodes")
        self.assertEqual(hubs["result"], [])
        diag = FakeRunner().search(graph, "diagnose")
        self.assertEqual(diag["result"]["summary"]["node_count"], 2)

    def test_native_merge_writes_and_validates_links_graph(self):
        first = self.base / "a.json"
        second = self.base / "b.json"
        for path in (first, second):
            path.write_text(json.dumps(graph_json(2)), encoding="utf-8")
        merged = self.base / "merged.json"
        result = FakeRunner().merge_graphs([first, second], merged)
        self.assertTrue(result["native_graphify_feature"])
        self.assertEqual(result["stats"]["edge_key"], "links")
        self.assertEqual(result["nodes"], 2)

    def test_subprocess_error_is_sanitized(self):
        runner = object.__new__(ri.GraphifyRunner)
        runner.binary = "graphify"
        runner.version = ri.PINNED_GRAPHIFY_VERSION
        runner.timeout = 5
        failure = subprocess.CompletedProcess(["graphify", "extract"], 1, "", SENTINEL)
        with mock.patch.object(ri.subprocess, "run", return_value=failure):
            with self.assertRaises(ri.GraphifyRunnerError) as caught:
                runner._run(["extract", "source"])
        message = str(caught.exception)
        self.assertNotIn(SENTINEL, message)
        self.assertIn("stderr_sha256", message)


if __name__ == "__main__":
    unittest.main()
