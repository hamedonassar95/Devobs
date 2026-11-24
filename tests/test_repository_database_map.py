"""Offline structural and reference checks for the consolidation inventory."""

import json
import re
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "docs/architecture/repository_database_map.json"
ALLOWED_STATUSES = {"VERIFIED", "UNVERIFIED", "BLOCKED", "PLANNED"}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class RepositoryDatabaseMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    def test_declares_expected_schema_and_top_level_types(self):
        self.assertEqual(self.data["map_format"], "devobs.repository-database-map")
        date.fromisoformat(self.data["generated_at"])
        self.assertEqual(self.data["schema_version"], 1)
        self.assertEqual(
            self.data["status_values"],
            ["VERIFIED", "UNVERIFIED", "BLOCKED", "PLANNED"],
        )
        for key in (
            "repositories",
            "components",
            "database_resources",
            "relationships",
            "comparisons",
            "safe_import_candidates",
            "migration_plan",
            "prohibitions",
        ):
            self.assertIn(key, self.data)
        self.assertIsInstance(self.data["repositories"], list)
        self.assertIsInstance(self.data["database_resources"], list)

    def test_status_fields_use_the_declared_vocabulary(self):
        for item in walk(self.data):
            for key, value in item.items():
                if key == "status" or key.endswith("_status"):
                    self.assertIn(value, ALLOWED_STATUSES, (key, value))

    def test_repository_refs_and_github_links_are_pinned_and_consistent(self):
        repos = self.data["repositories"]
        ids = [repo["id"] for repo in repos]
        self.assertEqual(len(ids), len(set(ids)))
        for repo in repos:
            self.assertRegex(repo["ref"], SHA_PATTERN)
            parsed = urlparse(repo["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "github.com")
            self.assertEqual(parsed.path.strip("/"), repo["name"])
            self.assertIn("/", repo["name"])

    def test_component_repository_and_local_paths_resolve(self):
        repository_ids = {repo["id"] for repo in self.data["repositories"]}
        for component in self.data["components"]:
            self.assertIn(component["repository_id"], repository_ids)
            if component["repository_id"] == self.data["canonical_repository"].split("/")[-1].lower():
                local_path = ROOT / component["path"]
                self.assertTrue(local_path.is_dir(), component["path"])

    def test_relationship_endpoints_resolve_to_inventory_nodes(self):
        node_ids = {
            *(repo["id"] for repo in self.data["repositories"]),
            *(component["id"] for component in self.data["components"]),
            *(resource["id"] for resource in self.data["database_resources"]),
        }
        for relation in self.data["relationships"]:
            self.assertIn(relation["from"], node_ids)
            self.assertIn(relation["to"], node_ids)

    def test_required_database_identifiers_and_separation_are_explicit(self):
        resources = {item["id"]: item for item in self.data["database_resources"]}
        firebase = resources["legacy_firebase_source"]
        self.assertEqual(firebase["evidence_classification"], "VERIFIED SOURCE LINK")
        self.assertEqual(firebase["project_id"], "my-apps-hamedo")
        self.assertEqual(
            firebase["firestore_database_id"],
            "ai-studio-promptpal-f1b3ebe9-9826-4fca-9a67-b5376e8669b3",
        )
        self.assertEqual(firebase["live_access_status"], "UNVERIFIED")

        render_db = resources["render_ai_staging_postgres"]
        self.assertEqual(render_db["logical_database_name"], "devobs_ai_staging")
        self.assertEqual(render_db["engine"], "PostgreSQL 17")
        self.assertEqual(render_db["free_expiry"], "2026-12-05")

        phone_repair = resources["phone_repair_supabase"]
        self.assertEqual(phone_repair["attachment_to_devobs"], "BLOCKED")
        self.assertFalse(self.data["baseline"]["live_database_access_performed"])

    def test_migration_steps_are_ordered_and_human_approval_is_last(self):
        plan = self.data["migration_plan"]
        self.assertEqual([step["order"] for step in plan], list(range(1, len(plan) + 1)))
        self.assertIn("human approval", plan[-1]["step"].lower())
        self.assertTrue(all(step["status"] == "PLANNED" for step in plan))

    def test_local_markdown_links_in_review_documents_resolve(self):
        documents = (
            ROOT / "README.md",
            ROOT / "docs/architecture/REPOSITORY_DATABASE_CONSOLIDATION.md",
            ROOT / "docs/architecture/OPS_DEVOBS_INTEGRATION_REVIEW_2026-11-24.md",
            ROOT / "apps/ai-intelligence-console/CONSOLIDATION.md",
        )
        expected = {
            "docs/architecture/REPOSITORY_DATABASE_CONSOLIDATION.md",
            "docs/architecture/repository_database_map.json",
            "docs/architecture/OPS_DEVOBS_INTEGRATION_REVIEW_2026-11-24.md",
        }
        readme = documents[0].read_text(encoding="utf-8")
        self.assertTrue(all(f"]({target})" in readme for target in expected))

        markdown_link = re.compile(r"\]\(([^)]+)\)")
        for document in documents[1:]:
            for target in markdown_link.findall(document.read_text(encoding="utf-8")):
                parsed = urlparse(target)
                if parsed.scheme or parsed.netloc or target.startswith("#"):
                    continue
                local_target = unquote(parsed.path)
                if local_target:
                    resolved = (document.parent / local_target).resolve()
                    self.assertTrue(resolved.exists(), f"{document.relative_to(ROOT)} -> {target}")


if __name__ == "__main__":
    unittest.main()
