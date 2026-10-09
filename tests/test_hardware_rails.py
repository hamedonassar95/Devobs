"""Validate reference metadata for configured device power rails.

These checks validate the reference-data contract. They do not measure a
physical device; populated values must come from the device documentation or
verified measurements.
"""

import json
import math
import unittest
from pathlib import Path


REFERENCE_DATA = Path(__file__).with_name("reference_rails.json")


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


class HardwareRailsReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with REFERENCE_DATA.open(encoding="utf-8") as reference_file:
            cls.data = json.load(reference_file)

    def test_reference_file_has_supported_top_level_structure(self):
        self.assertEqual(self.data.get("schema_version"), 1)
        self.assertIsInstance(self.data.get("rail_template"), dict)
        self.assertIsInstance(self.data.get("rails"), list)

    def test_template_declares_device_and_measurement_fields(self):
        template = self.data["rail_template"]
        self.assertEqual(
            set(template),
            {
                "device_model",
                "board_revision",
                "name",
                "target_effort",
                "resistance",
                "tolerance_range",
            },
        )
        self.assertEqual(set(template["target_effort"]), {"value", "unit"})
        self.assertEqual(
            set(template["resistance"]),
            {"value", "unit", "measurement_condition"},
        )
        self.assertEqual(
            set(template["tolerance_range"]), {"min", "max", "unit"}
        )

    def test_configured_rails_have_complete_valid_reference_values(self):
        seen = set()
        for rail in self.data["rails"]:
            with self.subTest(rail=rail.get("name")):
                self.assertIsInstance(rail.get("device_model"), str)
                self.assertTrue(rail["device_model"].strip())
                self.assertIsInstance(rail.get("board_revision"), str)
                self.assertTrue(rail["board_revision"].strip())
                self.assertIsInstance(rail.get("name"), str)
                self.assertTrue(rail["name"].strip())

                identity = (
                    rail["device_model"],
                    rail["board_revision"],
                    rail["name"],
                )
                self.assertNotIn(identity, seen, "duplicate device rail")
                seen.add(identity)

                target = rail["target_effort"]
                resistance = rail["resistance"]
                tolerance = rail["tolerance_range"]
                self.assertTrue(_is_finite_number(target["value"]))
                self.assertIsInstance(target["unit"], str)
                self.assertTrue(target["unit"].strip())

                self.assertTrue(_is_finite_number(resistance["value"]))
                self.assertGreaterEqual(resistance["value"], 0)
                self.assertIsInstance(resistance["unit"], str)
                self.assertTrue(resistance["unit"].strip())
                self.assertIsInstance(resistance["measurement_condition"], str)
                self.assertTrue(resistance["measurement_condition"].strip())

                lower = tolerance["min"]
                upper = tolerance["max"]
                self.assertTrue(_is_finite_number(lower))
                self.assertTrue(_is_finite_number(upper))
                self.assertLessEqual(lower, upper)
                self.assertLessEqual(lower, target["value"])
                self.assertLessEqual(target["value"], upper)
                self.assertEqual(tolerance["unit"], target["unit"])


if __name__ == "__main__":
    unittest.main()
