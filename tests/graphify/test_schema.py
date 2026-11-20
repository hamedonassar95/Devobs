"""Fail-closed schema, provenance and graph-shape checks."""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify.repository_intelligence import (  # noqa: E402
    GraphSchemaError,
    read_graph,
    validate_graph,
)


def graph(nodes=None, edges=None, edge_key="edges"):
    return {
        "nodes": nodes if nodes is not None else [
            {"id": "a", "label": "a.py", "source_file": "a.py"},
            {"id": "b", "label": "b.py", "source_file": "b.py"},
        ],
        edge_key: edges if edges is not None else [
            {
                "source": "a",
                "target": "b",
                "relation": "calls",
                "confidence": "EXTRACTED",
            }
        ],
    }


class ValidateGraphTests(unittest.TestCase):
    def test_valid_extraction_graph(self):
        stats = validate_graph(graph())
        self.assertEqual(stats.node_count, 2)
        self.assertEqual(stats.edge_count, 1)
        self.assertEqual(stats.edge_key, "edges")
        self.assertEqual(stats.confidence_counts, {"EXTRACTED": 1})
        self.assertEqual(stats.relation_counts, {"calls": 1})
        self.assertEqual(stats.source_file_count, 2)
        self.assertEqual(stats.orphan_node_ids, ())

    def test_real_graphify_null_source_location_is_accepted(self):
        document = graph()
        document["nodes"][0]["source_location"] = None
        stats = validate_graph(document)
        self.assertEqual(stats.node_count, 2)
        self.assertEqual(stats.edge_count, 1)

    def test_merged_links_key_is_supported(self):
        document = graph(edge_key="links")
        document.pop("edges", None)
        stats = validate_graph(document)
        self.assertEqual(stats.edge_key, "links")
        self.assertEqual(stats.edge_count, 1)

    def test_cycle_and_orphan_detection(self):
        document = graph(
            nodes=[
                {"id": "a", "source_file": "a.py"},
                {"id": "b", "source_file": "b.py"},
                {"id": "c", "source_file": "c.py"},
            ],
            edges=[
                {"source": "a", "target": "b", "relation": "calls", "confidence": "INFERRED"},
                {"source": "b", "target": "a", "relation": "calls", "confidence": "EXTRACTED"},
            ],
        )
        stats = validate_graph(document)
        self.assertEqual(stats.cycle_back_edges, 1)
        self.assertEqual(stats.orphan_node_ids, ("c",))
        self.assertEqual(stats.confidence_counts, {"EXTRACTED": 1, "INFERRED": 1})

    def test_rejects_unknown_confidence(self):
        document = graph(edges=[{"source": "a", "target": "b", "relation": "calls", "confidence": "GUESSED"}])
        with self.assertRaisesRegex(GraphSchemaError, "confidence_not_supported"):
            validate_graph(document)

    def test_rejects_duplicate_node_ids(self):
        document = graph(nodes=[{"id": "a"}, {"id": "a"}], edges=[])
        with self.assertRaisesRegex(GraphSchemaError, "duplicate_node_id"):
            validate_graph(document)

    def test_rejects_dangling_edges(self):
        document = graph(edges=[{"source": "a", "target": "missing", "relation": "calls", "confidence": "EXTRACTED"}])
        with self.assertRaisesRegex(GraphSchemaError, "dangling_edges"):
            validate_graph(document)

    def test_rejects_non_object_root(self):
        with self.assertRaisesRegex(GraphSchemaError, "root_must_be_object"):
            validate_graph([])

    def test_read_graph_computes_stable_digest(self):
        document = graph()
        with tempfile.TemporaryDirectory(prefix="devobs-graphify-schema-") as tmp:
            path = pathlib.Path(tmp) / "graph.json"
            path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
            loaded, stats, edge_key, digest = read_graph(path)
            self.assertEqual(loaded, document)
            self.assertEqual(stats.node_count, 2)
            self.assertEqual(edge_key, "edges")
            self.assertEqual(len(digest), 64)

    def test_read_graph_rejects_empty_file(self):
        with tempfile.TemporaryDirectory(prefix="devobs-graphify-schema-") as tmp:
            path = pathlib.Path(tmp) / "graph.json"
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "size_out_of_range|invalid"):
                read_graph(path)


if __name__ == "__main__":
    unittest.main()
