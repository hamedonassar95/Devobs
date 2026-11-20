"""Behavioral contract for the offline jq fixture used by health-check tests."""

from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest

from tests.fixtures import fake_jq

ROOT = Path(__file__).resolve().parents[1]


class FakeJqTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "contract.json"
        self.path.write_text(
            json.dumps({"required_text_any": ["Devobs"]}), encoding="utf-8"
        )

    def test_fixture_expressions_track_the_production_script(self):
        script = (ROOT / "scripts" / "check_vercel_site.sh").read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", script)
        for expression in fake_jq.FILTER_EXPRESSIONS:
            self.assertIn(re.sub(r"\s+", " ", expression), normalized)

    def test_contract_filters(self):
        output = StringIO()
        self.assertEqual(
            fake_jq.main(
                ["-e", fake_jq.CONTRACT_SHAPE_FILTER, str(self.path)], stdout=output
            ),
            0,
        )
        output = StringIO()
        self.assertEqual(
            fake_jq.main(
                ["-e", fake_jq.CONTRACT_MARKER_FILTER, str(self.path)], stdout=output
            ),
            0,
        )
        output = StringIO()
        self.assertEqual(
            fake_jq.main(["-r", fake_jq.CONTRACT_ITEMS_FILTER, str(self.path)], stdout=output),
            0,
        )
        self.assertEqual(output.getvalue(), "Devobs\n")
        output = StringIO()
        self.assertEqual(
            fake_jq.main(["-c", fake_jq.CONTRACT_JSON_FILTER, str(self.path)], stdout=output),
            0,
        )
        self.assertEqual(json.loads(output.getvalue()), ["Devobs"])

    def test_multiline_filter_whitespace_is_equivalent(self):
        multiline = fake_jq.CONTRACT_SHAPE_FILTER.replace(
            " and ", "\n  and "
        )
        self.assertEqual(
            fake_jq.main(["-e", multiline, str(self.path)], stdout=StringIO()), 0
        )

    def test_marker_filter_fails_closed(self):
        self.path.write_text(
            json.dumps({"required_text_any": ["Different brand"]}), encoding="utf-8"
        )
        self.assertEqual(
            fake_jq.main(
                ["-e", fake_jq.CONTRACT_MARKER_FILTER, str(self.path)], stdout=StringIO()
            ),
            1,
        )

    def test_manifest_filter_requires_the_exact_schema_and_sha(self):
        sha = "a" * 40
        self.path.write_text(
            json.dumps({"schema_version": 1, "source_sha": sha}), encoding="utf-8"
        )
        output = StringIO()
        self.assertEqual(
            fake_jq.main(["-er", fake_jq.MANIFEST_SHA_FILTER, str(self.path)], stdout=output),
            0,
        )
        self.assertEqual(output.getvalue(), sha + "\n")
        self.path.write_text(
            json.dumps({"schema_version": 2, "source_sha": sha}), encoding="utf-8"
        )
        self.assertEqual(
            fake_jq.main(["-er", fake_jq.MANIFEST_SHA_FILTER, str(self.path)]), 4
        )

    def test_unknown_filter_fails_closed(self):
        stderr = StringIO()
        code = fake_jq.main(
            ["-e", ".unsupported", str(self.path)], stderr=stderr
        )
        self.assertEqual(code, 2)
        self.assertIn("unsupported jq filter", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
