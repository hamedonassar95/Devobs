import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


class CIReleaseGateContractTests(unittest.TestCase):
    def test_pages_release_survives_skipped_optional_checks_but_requires_validation(self):
        expected = (
            "if: ${{ !cancelled() && github.event_name == 'push' && "
            "github.ref == 'refs/heads/main' && needs.validate.result == 'success' }}"
        )
        self.assertIn(expected, WORKFLOW)


if __name__ == "__main__":
    unittest.main()
