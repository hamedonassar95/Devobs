import unittest
import json
from scripts.investigation_contract import MARKER, parse


def comment(data='{"decision":"FIX_FORWARD","confidence":0.95,"reversible":true,"repository_scoped":true,"proposed_change":"repair site validation"}'):
    return f"## AI Incident Investigation\n{MARKER}\n\x60\x60\x60json\n{data}\n\x60\x60\x60"


class InvestigationContractTests(unittest.TestCase):
    def test_accepts_exact_contract(self):
        self.assertTrue(parse(comment()).valid)

    def test_rejects_missing_marker(self):
        self.assertFalse(parse(comment().replace(MARKER, "")).valid)

    def test_rejects_duplicate_marker(self):
        self.assertFalse(parse(comment() + MARKER).valid)

    def test_rejects_invalid_json(self):
        self.assertFalse(parse(comment("{bad")).valid)

    def test_rejects_extra_key(self):
        self.assertFalse(parse(comment('{"decision":"FIX_FORWARD","confidence":0.9,"reversible":true,"repository_scoped":true,"proposed_change":"x","extra":1}')).valid)

    def test_rejects_boolean_confidence(self):
        self.assertFalse(parse(comment('{"decision":"FIX_FORWARD","confidence":true,"reversible":true,"repository_scoped":true,"proposed_change":"x"}')).valid)

    def test_rejects_empty_change(self):
        self.assertFalse(parse(comment('{"decision":"FIX_FORWARD","confidence":0.9,"reversible":true,"repository_scoped":true,"proposed_change":""}')).valid)

    def test_rejects_bad_decision(self):
        self.assertFalse(parse(comment('{"decision":"AUTO_MERGE","confidence":0.9,"reversible":true,"repository_scoped":true,"proposed_change":"x"}')).valid)

    def test_rejects_string_scope_flag(self):
        self.assertFalse(parse(comment('{"decision":"FIX_FORWARD","confidence":0.9,"reversible":"true","repository_scoped":true,"proposed_change":"x"}')).valid)

    def test_rejects_multiple_json_fences(self):
        self.assertFalse(parse(comment() + "\n\x60\x60\x60json\n{}\n\x60\x60\x60").valid)


if __name__ == "__main__":
    unittest.main()


class InvestigationContractV2Tests(unittest.TestCase):
    def _text(self, incident_number=34, run_id="simulation-37537017304"):
        data = {
            "incident_number": incident_number,
            "incident_run_id": run_id,
            "decision": "MANUAL_REVIEW",
            "confidence": 1.0,
            "reversible": True,
            "repository_scoped": True,
            "proposed_change": "No repository change; human review only.",
        }
        return "<!-- devobs-investigation-contract:v2 -->\n\x60\x60\x60json\n" + json.dumps(data) + "\n\x60\x60\x60"

    def test_v2_accepts_exact_trusted_binding(self):
        result = parse(self._text(), expected_incident_number=34, expected_run_id="simulation-37537017304")
        self.assertTrue(result.valid)

    def test_v2_rejects_wrong_incident_number(self):
        result = parse(self._text(35), expected_incident_number=34, expected_run_id="simulation-37537017304")
        self.assertFalse(result.valid)

    def test_v2_rejects_wrong_run_id(self):
        result = parse(self._text(run_id="simulation-other"), expected_incident_number=34, expected_run_id="simulation-37537017304")
        self.assertFalse(result.valid)

    def test_v2_rejects_missing_trusted_binding_context(self):
        result = parse(self._text())
        self.assertFalse(result.valid)

    def test_v2_rejects_boolean_incident_number(self):
        result = parse(self._text(True), expected_incident_number=34, expected_run_id="simulation-37537017304")
        self.assertFalse(result.valid)
