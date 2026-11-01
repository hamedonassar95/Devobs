"""Inspect a local repair knowledge packet before advisory project handoff.

Offline structural and heuristic checks; NEVER prove redaction or approvals,
transfer an artifact, contact a provider, publish, merge, or deploy anything.
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
from urllib.parse import urlsplit

from project_handoff_gate import evaluate as evaluate_handoff

FIELDS = {
    'schema_version', 'source', 'destination', 'topic_id', 'review_date',
    'device_family', 'symptom', 'safe_next_step', 'evidence',
    'technical_reviewed', 'destination_owner_reviewed', 'rights_reviewed',
    'contains_customer_data', 'contains_secrets', 'classification', 'intent',
}
BOOL_FIELDS = {
    'technical_reviewed', 'destination_owner_reviewed', 'rights_reviewed',
    'contains_customer_data', 'contains_secrets',
}
LEVELS = {'CONFIRMED', 'INFERENCE', 'POSSIBLE', 'UNKNOWN'}
SENSITIVE = re.compile(
    r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'
    r'|\+?\d(?:[\d ()-]{7,}\d)'
    r'|\b(?:imei|password|secret|bearer|authorization|token|serial(?:\s+number)?|api[ _-]?key)\b'
    r'|\bsk-[A-Za-z0-9_-]{8,}\b', re.IGNORECASE,
)
TOPIC = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')


def deny(reason):
    return {'decision': 'DENY', 'reason': reason}


def plain_text(value, limit):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit and not SENSITIVE.search(value)


def evaluate_package(package):
    """Return an advisory review candidate plus digest, or a generic denial."""
    if not isinstance(package, dict) or set(package) != FIELDS:
        return deny('invalid packet schema')
    if type(package['schema_version']) is not int or package['schema_version'] != 1:
        return deny('unsupported schema version')
    if any(type(package[key]) is not bool for key in BOOL_FIELDS):
        return deny('invalid declarations')
    if not package['rights_reviewed']:
        return deny('rights review missing')
    topic = package['topic_id']
    if not isinstance(topic, str) or len(topic) > 72 or not TOPIC.fullmatch(topic):
        return deny('invalid topic identifier')
    try:
        date = package['review_date']
        if not isinstance(date, str) or len(date) != 10:
            raise ValueError('invalid date')
        dt.date.fromisoformat(date)
    except ValueError:
        return deny('invalid review date')
    if not all(plain_text(package[key], 300) for key in ('device_family', 'symptom', 'safe_next_step')):
        return deny('invalid or sensitive-looking content')
    evidence = package['evidence']
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 8:
        return deny('invalid evidence count')
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {'level', 'statement', 'source_reference'}:
            return deny('invalid evidence fields')
        if not isinstance(item['level'], str) or item['level'] not in LEVELS or not plain_text(item['statement'], 300):
            return deny('invalid evidence claim')
        reference = item['source_reference']
        if not isinstance(reference, str) or len(reference) > 200 or SENSITIVE.search(reference):
            return deny('invalid or sensitive-looking source reference')
        if reference:
            try:
                url = urlsplit(reference)
                valid_reference = (url.scheme == 'https' and bool(url.hostname)
                                   and not url.username and not url.password
                                   and not url.query and '@' not in url.netloc)
            except ValueError:
                valid_reference = False
            if not valid_reference:
                return deny('source reference must use clean HTTPS URL')
        if item['level'] == 'CONFIRMED' and not reference:
            return deny('confirmed claim requires a reference')
    candidate = {
        'source': package['source'], 'destination': package['destination'],
        'artifact_type': 'knowledge_package', 'intent': package['intent'],
        'classification': package['classification'],
        'contains_customer_data': package['contains_customer_data'],
        'contains_secrets': package['contains_secrets'],
        'technical_reviewed': package['technical_reviewed'],
        'destination_owner_reviewed': package['destination_owner_reviewed'],
    }
    result = evaluate_handoff(candidate)
    if result['decision'] != 'REVIEW_ONLY':
        return result
    canonical = json.dumps(package, sort_keys=True, ensure_ascii=False,
                           separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(canonical) > 8192:
        return deny('packet exceeds size limit')
    return {'decision': 'REVIEW_ONLY',
            'reason': 'candidate for independent human review; no transfer or publication',
            'package_sha256': hashlib.sha256(canonical).hexdigest()}


def unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key')
        value[key] = item
    return value


def reject_constant(value):
    raise ValueError('invalid JSON constant')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        if args.package.stat().st_size > 8192:
            raise ValueError('oversized packet')
        packet = json.loads(args.package.read_text(encoding='utf-8'),
                            object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except (OSError, UnicodeError, ValueError):
        print(json.dumps(deny('unreadable or invalid JSON packet')))
        return 2
    result = evaluate_package(packet)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['decision'] == 'REVIEW_ONLY' else 1


if __name__ == '__main__':
    sys.exit(main())
