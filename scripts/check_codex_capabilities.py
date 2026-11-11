#!/usr/bin/env python3
"""Offline Codex capability inventory: source evidence is NOT runtime acceptance."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tomllib
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs' / 'CODEX_CAPABILITY_INVENTORY.json'
IDS = (
    'codex-cli-ide', 'codex-cloud-github', 'repo-instructions', 'skills',
    'subagents', 'goals', 'worktrees', 'docs-mcp', 'hooks', 'codex-security',
    'codex-sdk', 'app-server', 'agents-api', 'automations',
    'remote-mobile', 'record-replay',
)
STATES = {
    'SOURCE_PRESENT', 'CONFIGURED_RUNTIME_UNVERIFIED',
    'DOCUMENTED_RUNTIME_UNVERIFIED', 'NO_RUNTIME_PROOF',
}
SOURCED = STATES - {'NO_RUNTIME_PROOF'}


class CapabilityError(ValueError):
    """A missing/unsafe source or overclaimed status: stop instead of pass."""


def _safe_source(root: pathlib.Path, name: object) -> None:
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name):
        raise CapabilityError('Invalid source path')
    parts = pathlib.PurePosixPath(name).parts
    if any(part in ('.', '..') for part in parts):
        raise CapabilityError('Source path traversal')
    target = root.joinpath(*parts)
    if not target.is_file() or target.is_symlink():
        raise CapabilityError('Required source file unavailable or symlinked: ' + name)


def validate(manifest: object, root: pathlib.Path = ROOT) -> dict[str, int]:
    if not isinstance(manifest, dict) or set(manifest) != {
        'schema_version', 'repository', 'reviewed_main_sha', 'scope',
        'gate_status', 'permissions', 'features',
    }:
        raise CapabilityError('Unexpected manifest shape')
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise CapabilityError('Schema version mismatch')
    if manifest['repository'] != 'hamedonassar95/Devobs' or manifest['scope'] != 'OFFLINE_REPOSITORY_EVIDENCE_ONLY':
        raise CapabilityError('Wrong repository or unsupported scope')
    if not isinstance(manifest['reviewed_main_sha'], str) or not re.fullmatch(r'[0-9a-f]{40}', manifest['reviewed_main_sha']):
        raise CapabilityError('Missing immutable review SHA')
    if manifest['gate_status'] != {'P01': 'BLOCKED', 'AI-9': 'BLOCKED'}:
        raise CapabilityError('Unapproved readiness gate promotion')
    required_perms = {'merge', 'deploy', 'paid_inference', 'schedule', 'modify_secrets'}
    if not isinstance(manifest['permissions'], dict) or set(manifest['permissions']) != required_perms:
        raise CapabilityError('Permission map incomplete')
    if any(manifest['permissions'][key] is not False for key in required_perms):
        raise CapabilityError('Unauthorized external action claim')

    records = manifest['features']
    if not isinstance(records, list) or len(records) != len(IDS):
        raise CapabilityError('Feature count mismatch')
    for expected, record in zip(IDS, records):
        if not isinstance(record, dict) or set(record) != {
            'id', 'status', 'runtime_verified', 'source_paths', 'next_proof',
            'official_reference',
        }:
            raise CapabilityError('Unexpected feature record shape')
        if record['id'] != expected or record['status'] not in STATES:
            raise CapabilityError('Unknown/out-of-order feature or status')
        if record['runtime_verified'] is not False:
            raise CapabilityError('Runtime cannot be declared proven by repository inventory')
        refs = record['source_paths']
        if not isinstance(refs, list) or len(refs) != len(set(map(str, refs))) or len(refs) > 8:
            raise CapabilityError('Invalid/duplicate reference list')
        if record['status'] in SOURCED and not refs:
            raise CapabilityError('Sourced capability lacks source evidence')
        for source in refs:
            _safe_source(root, source)
        hint = record['next_proof']
        if not isinstance(hint, str) or not hint.strip() or len(hint) > 450:
            raise CapabilityError('Next proof missing or too long')
        url = record['official_reference']
        if not isinstance(url, str):
            raise CapabilityError('Official documentation reference missing')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in ('developers.openai.com', 'learn.chatgpt.com') or parsed.username or parsed.password:
            raise CapabilityError('Untrusted documentation reference')

    config_file = root / '.codex' / 'config.toml'
    try:
        config = tomllib.loads(config_file.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise CapabilityError('Codex configuration missing or malformed') from exc
    agents = config.get('agents', {})
    if agents.get('enabled') is not True or agents.get('max_concurrent_threads_per_session') != 2:
        raise CapabilityError('Multi-agent settings drifted; rereview inventory')
    docs = config.get('mcp_servers', {}).get('openaiDeveloperDocs', {})
    if docs != {'url': 'https://developers.openai.com/mcp'}:
        raise CapabilityError('Public Docs MCP configuration drifted')
    if 'hooks' in config or (root / '.codex' / 'hooks.json').exists():
        raise CapabilityError('Codex hooks changed: review trust and adjust inventory')
    ledger = json.loads((root / 'docs' / 'MILESTONE_LEDGER.json').read_text(encoding='utf-8'))
    current_gates = {g['id']: g['status'] for g in ledger['gates']}
    if current_gates.get('p01-managed-saas') != 'BLOCKED' or current_gates.get('ai9-detection-quality') != 'BLOCKED':
        raise CapabilityError('Current ledger and inventory gate disagreement')
    return {
        'total': len(IDS),
        'source_or_configuration_present': sum(r['status'] in SOURCED for r in records),
        'needs_runtime_or_external_proof': sum(r['status'] != 'SOURCE_PRESENT' for r in records),
        'runtime_verified': 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=pathlib.Path, default=MANIFEST)
    parser.add_argument('--root', type=pathlib.Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.file.read_text(encoding='utf-8'))
        result = validate(data, root=args.root)
    except (OSError, UnicodeError, json.JSONDecodeError, CapabilityError, TypeError) as exc:
        print('BLOCKED: Codex capability evidence invalid (' + type(exc).__name__ + ')', file=sys.stderr)
        return 1
    print(json.dumps({'result': 'SOURCE_AUDIT_ONLY', 'gates': 'P01/AI-9 BLOCKED', **result}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
