"""AI module inventory must be explicit about unverified customer-readiness gates."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class InventoryTests(unittest.TestCase):
    def test_offline_inventory_is_self_consistent_and_does_not_claim_live_ops(self):
        inventory=json.loads((ROOT/"docs/ai/ai-bom-2027.json").read_text())
        self.assertEqual(inventory["schema_version"],1)
        self.assertEqual(inventory["source_control"]["repository"],"hamedonassar95/Devobs")
        flags=inventory["controls"]
        for key in ("allow_production_execution","external_model_invocation",
                    "verified_human_approval","externally_anchored_audit"):
            self.assertIs(flags[key],False)
        self.assertFalse(inventory["model_execution"]["live_inference_verified"])

    def test_inventory_paths_are_relative_and_exist(self):
        inventory=json.loads((ROOT/"docs/ai/ai-bom-2027.json").read_text())
        paths=[x["path"] for x in inventory["components"]]+[
            x["file"] for x in inventory["datasets"]]+inventory["dependency_manifests"]
        self.assertEqual(len(paths),len(set(paths)))
        for relative in paths:
            with self.subTest(file=relative):
                p=Path(relative)
                self.assertFalse(p.is_absolute())
                self.assertNotIn("..",p.parts)
                self.assertTrue((ROOT/p).is_file())


if __name__=="__main__": unittest.main()
