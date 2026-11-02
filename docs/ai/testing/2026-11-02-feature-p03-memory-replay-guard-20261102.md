---
phase: testing
title: Approval replay guard test plan
description: Offline contract tests for atomic process-local consumption
---

# Testing

## Planned scenarios

- Signed import requires an explicit valid registry.
- First valid import succeeds; reusing the same ID in the same registry fails closed.
- Invalid signatures, duplicate rows, and invalid batch members do not partially consume IDs.
- Capacity exhaustion fails closed and preserves earlier claims without evicting them.
- Concurrent imports of one signed envelope have exactly one successful consumer.
- Existing signature, tenant/project/curator scope, expiry, retrieval provenance, and demo behavior remain covered.

All fixtures use generated local Ed25519 keys and synthetic metadata. No real incident data, network, model, or external service is used.

## Verification

Focused results: approval suite — 14 tests passed; demo suite — 9 tests passed; module `compileall` passed. The first required-registry test failed against the prior API with `TypeError: unexpected keyword argument 'consumption_registry'`; after implementation the focused suite passed. The repeat-consumption test then failed before the registry implementation with `ContextError not raised`, confirming the replay behavior gap.

Full verification: `/tmp/devobs-p01-ac02-validation/bin/python -m unittest discover -s tests -q` — `Ran 790 tests in 15.127s`, `OK (skipped=22)`. The default interpreter's initial full-suite run could not import `psycopg`; the hash-locked temporary validation environment resolved that without repository dependency changes. Bandit found no issues. `python3 scripts/milestone_ledger.py --summary` and AI DevKit feature lint passed. `git diff --check` passed.

The tests validate only the local process-level contract. They do not prove persistence, a deployed API, multiple workers, a live curator, or actual AI model calls.

## Limits

These tests prove behavior within one Python process and one explicitly shared registry object only. They do not prove protection across process restart, separate workers, a deployed API, or a trusted persistent registry.
