---
phase: testing
title: Approved encrypted memory archive restore tests
description: Verify fail-closed provenance restoration and replay behavior with synthetic records
---

# Testing

The focused encryption suite exercises authenticated plain decryption stripping
approval provenance, exact approved restore with generated Ed25519 keys,
complete record-set mismatch without partial approval consumption, and replay
rejection by the process-local registry. Tests use synthetic records and
ephemeral test keys only.

- `python3 -m unittest discover -s tests -p 'test_intelligence_incident_memory_encryption.py' -v` — 9 passed.
- `PYTHONPATH=/tmp/devobs-p03-approved-restore-deps-20261103 python3 -m unittest discover -s tests -v` — 884 passed, 22 skipped.
- `python3 -m compileall -q scripts/devobs_intelligence tests` and `git diff --check` — passed.

The full suite used the locked `psycopg[binary]==3.3.6` in a temporary target
outside the repository; that target was removed after verification.

The tests do not establish key enrollment/custody, durable replay prevention,
cross-worker coordination, persistence, physical deletion, production tenant
isolation, or real incident-data quality.
