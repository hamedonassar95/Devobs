"""Behavioral and adversarial tests for a read-only repair knowledge review packet."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from repair_knowledge_handoff import evaluate_package  # noqa: E402


class KnowledgeHandoffTests(unittest.TestCase):
    def setUp(self):
        self.packet = {
            'schema_version': 1,
            'source': 'phone-repair-assistant-v2',
            'destination': 'al-dala-mobile',
            'topic_id': 'safe-observation-example',
            'review_date': '2026-11-01',
            'device_family': 'Example phone family',
            'symptom': 'The device does not start consistently.',
            'safe_next_step': 'Record the observation for a trained reviewer.',
            'evidence': [{
                'level': 'POSSIBLE',
                'statement': 'A configuration issue is one possible explanation.',
                'source_reference': 'https://example.org/technical-reference',
            }],
            'technical_reviewed': True,
            'destination_owner_reviewed': True,
            'rights_reviewed': True,
            'contains_customer_data': False,
            'contains_secrets': False,
            'classification': 'public_redacted',
            'intent': 'review',
        }

    def test_valid_packet_is_advisory_only_with_stable_digest(self):
        result = evaluate_package(self.packet)
        self.assertEqual(result['decision'], 'REVIEW_ONLY')
        self.assertEqual(len(result['package_sha256']), 64)
        shuffled = dict(reversed(list(self.packet.items())))
        self.assertEqual(result['package_sha256'], evaluate_package(shuffled)['package_sha256'])

    def test_unauthorized_direction_or_intent_denied(self):
        for key, value in [('source', 'devobs'), ('destination', 'devobs-saas'),
                           ('intent', 'publish'), ('classification', 'internal')]:
            with self.subTest(key=key):
                self.assertEqual(evaluate_package({**self.packet, key: value})['decision'], 'DENY')

    def test_missing_reviews_and_sensitive_claim_denied(self):
        for field, value in [('technical_reviewed', False), ('destination_owner_reviewed', False),
                             ('rights_reviewed', False), ('contains_customer_data', True),
                             ('contains_secrets', True), ('technical_reviewed', 1)]:
            with self.subTest(field=field):
                self.assertEqual(evaluate_package({**self.packet, field: value})['decision'], 'DENY')

    def test_reject_unexpected_fields_and_invalid_schema(self):
        for mutation in ({**self.packet, 'customer_address': 'redacted'},
                         {k:v for k,v in self.packet.items() if k != 'evidence'},
                         {**self.packet, 'schema_version': True},
                         {**self.packet, 'topic_id': '../bad-path'}):
            self.assertEqual(evaluate_package(mutation)['decision'], 'DENY')

    def test_reject_invalid_evidence_and_fake_confidence(self):
        for evidence in ([], [{}], [{'level':'CONFIRMED','statement':'Certain','source_reference':''}],
                         [{'level':'CERTAIN','statement':'Certain','source_reference':'https://example.org'}],
                         [{'level':'INFERENCE','statement':'Claim','source_reference':'http://example.org'}]):
            with self.subTest(evidence=evidence):
                self.assertEqual(evaluate_package({**self.packet, 'evidence': evidence})['decision'], 'DENY')

    def test_reject_suspected_pii_or_credentials_without_echoing_it(self):
        for secret in ('someone@example.net', 'IMEI 123456789012345',
                       'Authorization: Bearer ABCDEFGH', '+962 79 123 4567'):
            with self.subTest(kind=secret[:3]):
                result = evaluate_package({**self.packet, 'symptom': secret})
                self.assertEqual(result['decision'], 'DENY')
                self.assertNotIn(secret, json.dumps(result))

    def test_malformed_evidence_types_fail_closed(self):
        for level in ([], {}, None, 7):
            packet = copy.deepcopy(self.packet)
            packet['evidence'][0]['level'] = level
            self.assertEqual(evaluate_package(packet)['decision'], 'DENY')

    def test_reference_cannot_embed_credentials_or_query_string(self):
        for reference in ('https://person:pass@example.org/page',
                          'https://example.org/path?session=anything', 'https://',
                          'https://example.org@other.net/page'):
            packet = copy.deepcopy(self.packet)
            packet['evidence'][0]['source_reference'] = reference
            self.assertEqual(evaluate_package(packet)['decision'], 'DENY')

    def test_reject_prompt_injected_extra_keys(self):
        packet = copy.deepcopy(self.packet)
        packet['evidence'][0]['execute_action'] = 'publish'
        self.assertEqual(evaluate_package(packet)['decision'], 'DENY')

    def test_cli_rejects_duplicate_keys_and_bad_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / 'payload.json'
            for data in ('{"schema_version":1,"schema_version":2}', '{INVALID'):
                path.write_text(data, encoding='utf8')
                run = subprocess.run([sys.executable, str(ROOT/'scripts/repair_knowledge_handoff.py'),
                                      '--package', str(path)], text=True, capture_output=True)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(json.loads(run.stdout)['decision'], 'DENY')

    def test_cli_valid_and_no_sensitive_text_in_output(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / 'payload.json'
            path.write_text(json.dumps(self.packet), encoding='utf8')
            run = subprocess.run([sys.executable, str(ROOT/'scripts/repair_knowledge_handoff.py'),
                                  '--package', str(path)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0)
            self.assertEqual(json.loads(run.stdout)['decision'], 'REVIEW_ONLY')
            self.assertNotIn(self.packet['symptom'], run.stdout)

    def test_cli_oversized_input_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / 'payload.json'
            path.write_text('x' * 8200, encoding='utf8')
            run = subprocess.run([sys.executable, str(ROOT/'scripts/repair_knowledge_handoff.py'),
                                  '--package', str(path)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout)['decision'], 'DENY')


if __name__ == '__main__':
    unittest.main()
