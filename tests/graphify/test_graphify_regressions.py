"""Regression tests for Graphify integration graph validation and diagnostics.

Deterministic, offline tests using fixtures. No external APIs, no Graphify
binary required. Covers valid graphs, missing nodes/dangling references,
duplicate edges, dependency cycles, and malformed inputs.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify.common import GraphSchemaError, RepositoryIntelligenceError, read_graph, validate_graph  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))


class GraphifyRegressionTests(unittest.TestCase):
    def test_valid_graph_fixture_passes_validation(self):
        stats = validate_graph(load_fixture("valid_graph.json"))
        self.assertEqual(stats.node_count, 2)
        self.assertEqual(stats.edge_count, 1)
        self.assertEqual(stats.edge_key, "edges")
        self.assertEqual(stats.confidence_counts, {"EXTRACTED": 1})
        self.assertEqual(stats.dangling_edge_count, 0)
        self.assertEqual(stats.cycle_back_edges, 0)

    def test_missing_node_reference_fails_closed_with_actionable_diagnostic(self):
        with self.assertRaises(GraphSchemaError) as ctx:
            validate_graph(load_fixture("missing_node.json"))
        message = str(ctx.exception)
        self.assertIn("dangling", message.lower())
        self.assertRegex(message, r"graph_has_\d+_dangling_edges")

    def test_duplicate_edges_are_deterministic_and_reported_in_stats(self):
        # Current contract: duplicate edges are structurally valid node-link edges.
        # Regression ensures deterministic counting/diagnostics; behavior is preserved.
        document = load_fixture("duplicate_edges.json")
        first = validate_graph(document)
        second = validate_graph(document)
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertEqual(first.edge_count, 2)
        self.assertEqual(first.relation_counts, {"imports": 2})
        self.assertEqual(first.confidence_counts, {"EXTRACTED": 2})
        self.assertEqual(first.dangling_edge_count, 0)

    def test_dependency_cycle_is_detected_with_actionable_sample(self):
        stats = validate_graph(load_fixture("dependency_cycle.json"))
        self.assertGreaterEqual(stats.cycle_back_edges, 1)
        self.assertTrue(stats.cycle_samples)
        sample = stats.cycle_samples[0]
        self.assertIn("a", sample)
        self.assertIn("b", sample)
        as_dict = stats.as_dict()
        self.assertIn("cycle_back_edges", as_dict)
        self.assertIn("cycle_samples", as_dict)

    def test_malformed_input_fails_closed_with_actionable_diagnostic(self):
        with self.assertRaises(GraphSchemaError) as ctx:
            validate_graph(load_fixture("malformed_input.json"))
        self.assertIn("graph_edges_or_links_must_be_array", str(ctx.exception))

    def test_read_graph_reports_invalid_json_actionably(self):
        bad = FIXTURES / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        try:
            with self.assertRaises(GraphSchemaError) as ctx:
                read_graph(bad)
            self.assertIn("graph_json_invalid", str(ctx.exception))
        finally:
            bad.unlink(missing_ok=True)

    def test_read_graph_reports_missing_file_actionably(self):
        missing = FIXTURES / "does-not-exist.json"
        with self.assertRaises(RepositoryIntelligenceError) as ctx:
            read_graph(missing)
        self.assertIn("graph_file_not_found", str(ctx.exception))

    def test_read_graph_reports_size_out_of_range_actionably(self):
        empty = FIXTURES / "empty.json"
        empty.write_text("", encoding="utf-8")
        try:
            with self.assertRaises(RepositoryIntelligenceError) as ctx:
                read_graph(empty)
            self.assertIn("graph_file_size_out_of_range", str(ctx.exception))
        finally:
            empty.unlink(missing_ok=True)

    def test_non_object_root_fails_closed(self):
        with self.assertRaises(GraphSchemaError) as ctx:
            validate_graph([])
        self.assertIn("graph_root_must_be_object", str(ctx.exception))

    def test_unknown_confidence_fails_closed(self):
        document = load_fixture("valid_graph.json")
        document["edges"][0]["confidence"] = "GUESSED"
        with self.assertRaises(GraphSchemaError) as ctx:
            validate_graph(document)
        self.assertIn("graph_edge_confidence_not_supported", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
