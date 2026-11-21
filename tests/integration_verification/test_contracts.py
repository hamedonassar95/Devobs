import unittest
from devobs.integration_verification.contracts import validate_component_contracts, validate_evidence
from devobs.integration_verification.models import Finding

class ContractTests(unittest.TestCase):
    def test_invalid_schema_version(self):
        findings=[]
        comps = validate_component_contracts([{"name":"a","schema_version":2,"verification_status":"IMPLEMENTED_AND_TESTED","integration_dependencies":[]}], findings)
        self.assertTrue(any(f.code=='INVALID_SCHEMA_VERSION' for f in findings))
        self.assertEqual(comps[0]['name'],'a')

    def test_malformed_evidence(self):
        findings=[]
        ev = validate_evidence([{"source":"s"}], findings)
        self.assertEqual(ev, [])
        self.assertTrue(any(f.code=='MISSING_EVIDENCE_FIELDS' for f in findings))

    def test_contradictory_evidence(self):
        findings=[]
        ev = validate_evidence([
            {"source":"ci","evidence_id":"1","component":"c","verification_method":"ci","verification_timestamp":"t","result":"PASS"},
            {"source":"ci","evidence_id":"2","component":"c","verification_method":"ci","verification_timestamp":"t","result":"FAIL"},
        ], findings)
        self.assertEqual(len(ev),2)
        self.assertTrue(any(f.code=='CONTRADICTORY_EVIDENCE' for f in findings))

    def test_secret_redaction(self):
        findings=[]
        ev = validate_evidence([{"source":"ci","evidence_id":"1","component":"c","verification_method":"ci","verification_timestamp":"t","result":"PASS","token":"ghp_abcdefghijklmnopqrstuvwxyz123456"}], findings)
        self.assertNotIn('ghp_abcdefghijklmnopqrstuvwxyz123456', str(ev))

if __name__ == '__main__':
    unittest.main()
