"""Behavioral tests for the Devobs-owned adapters (no Graphify subprocess)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.graphify.repository_intelligence import (  # noqa: E402
    RepositoryIntelligenceError,
    branch_adapter,
    cross_repo_view,
    dependency_adapter,
    docs_adapter,
    inspect_repository,
    tree_adapter,
    workflow_adapter,
)

SENTINEL = "SENTINEL_VALUE_12345"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def make_repo(base):
    repo = pathlib.Path(base) / "synthetic"
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\n"
        "on: push\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-24.04\n"
        "    steps:\n"
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n"
        "  build:\n"
        "    needs: test\n"
        "    runs-on: ubuntu-24.04\n",
        encoding="utf-8",
    )
    (repo / "docs" / "index.md").write_text(
        "# Local\n\nSee [calc](../calc.py) and [absent](missing.md).\n", encoding="utf-8"
    )
    (repo / ".env").write_text(SENTINEL + "\n", encoding="utf-8")
    git_init = subprocess.run(
        ["git", "init", "-q", "-b", "main", str(repo)], capture_output=True, text=True
    )
    if git_init.returncode != 0:
        git_init = subprocess.run(["git", "init", "-q", str(repo)], capture_output=True, text=True)
    git(repo, "config", "user.name", "RI Adapter Test")
    git(repo, "config", "user.email", "ri-adapter@example.invalid")
    git(repo, "add", "calc.py", ".github/workflows/ci.yml", "docs/index.md")
    git(repo, "commit", "-q", "-m", "synthetic")
    return repo


def write_graph(path, tag_prefix=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": f"{tag_prefix}calc", "label": "calc.py", "source_file": "calc.py"},
                    {"id": f"{tag_prefix}add", "label": "add()", "source_file": "calc.py"},
                ],
                "edges": [
                    {
                        "source": f"{tag_prefix}calc",
                        "target": f"{tag_prefix}add",
                        "relation": "contains",
                        "confidence": "EXTRACTED",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="devobs-graphify-adapters-")
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.repo = make_repo(self.base)
        self.graph = write_graph(self.base / "out" / "graph.json")

    def test_tree_adapter_excludes_environment_files(self):
        result = tree_adapter(self.repo)
        self.assertEqual(result["native_graphify_feature"], False)
        self.assertEqual(result["file_count"], 3)
        self.assertNotIn(".env", result["sample_paths"])
        self.assertIn("code", result["categories"])
        self.assertIn("docs", result["categories"])
        self.assertIn("workflow", result["categories"])

    def test_workflow_adapter_reads_job_graph(self):
        result = workflow_adapter(self.repo)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["jobs"], ["build", "test"])
        self.assertEqual(result["edges"], [{"from": "test", "to": "build"}])
        self.assertTrue(any("actions/checkout" in item for item in result["uses"]))

    def test_workflow_adapter_fails_closed_without_jobs_block(self):
        (self.repo / ".github" / "workflows" / "broken.yml").write_text("name: broken\n", encoding="utf-8")
        git(self.repo, "add", ".github/workflows/broken.yml")
        git(self.repo, "commit", "-q", "-m", "broken workflow")
        with self.assertRaises(RepositoryIntelligenceError):
            workflow_adapter(self.repo)

    def test_docs_adapter_detects_broken_relative_link(self):
        result = docs_adapter(self.repo)
        self.assertEqual(result["document_count"], 1)
        self.assertEqual(result["broken_local_links"], [{"file": "docs/index.md", "target": "missing.md"}])

    def test_branch_adapter_is_local_only(self):
        result = branch_adapter(self.repo)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["branch"], "main")
        self.assertEqual(result["network_calls"], 0)
        # The synthetic .env fixture is intentionally untracked, so the local
        # branch adapter truthfully reports a dirty tree without contacting a remote.
        self.assertTrue(result["dirty"])
        (self.repo / "untracked.txt").write_text("local\n", encoding="utf-8")
        self.assertTrue(branch_adapter(self.repo)["dirty"])

    def test_dependency_adapter_maps_graph_files_to_tracked_tree(self):
        result = dependency_adapter(self.graph, self.repo)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["graph_source_file_count"], 1)
        self.assertEqual(result["source_files_not_in_tracked_tree"], [])
        self.assertEqual(result["relation_counts"], {"contains": 1})

    def test_inspect_repository_combines_adapters(self):
        result = inspect_repository(self.repo, self.graph)
        self.assertEqual(set(result), {"tree", "workflows", "branches", "docs", "dependencies"})
        payload = json.dumps(result)
        self.assertNotIn(SENTINEL, payload)

    def test_cross_repo_view_prefixes_tags_and_rejects_bad_tag(self):
        second = write_graph(self.base / "out2" / "graph.json", "api::")
        config = self.base / "cross.json"
        config.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repositories": [
                        {"tag": "devobs", "source": str(self.repo), "graph": str(self.graph)},
                        {"tag": "api", "source": str(self.repo), "graph": str(second)},
                    ],
                }
            ),
            encoding="utf-8",
        )
        view = cross_repo_view(config)
        self.assertEqual(len(view["repositories"]), 2)
        self.assertEqual(view["bounded_view"]["nodes"][0]["id"], "devobs::calc")
        self.assertFalse(view["native_graphify_feature"])
        self.assertTrue(all("stats" in item for item in view["repositories"]))
        config.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repositories": [
                        {"tag": "BAD TAG", "source": str(self.repo), "graph": str(self.graph)}
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(RepositoryIntelligenceError):
            cross_repo_view(config)


if __name__ == "__main__":
    unittest.main()
