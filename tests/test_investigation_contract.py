import unittest
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
