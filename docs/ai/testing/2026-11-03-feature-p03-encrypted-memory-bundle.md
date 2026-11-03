---
phase: testing
title: Encrypted incident-memory bundle tests
description: Check scoped round-trip, confidentiality shape, authentication, expiry and strict parsing
---

# Testing

- Focused encryption suite: 6 passed.
- Full command: `PYTHONPATH=/tmp/devobs-p03-memory-crypto-deps-20261103 python3 -m unittest discover -s tests -v` — 881 passed, 22 skipped.
- `python3 -m compileall -q scripts/devobs_intelligence tests` and `git diff --check` passed.
- The temp target supplied locked `psycopg==3.3.6` and `psycopg-binary==3.3.6`; no hosted database was configured.

Coverage includes scoped confidentiality round-trip, expiry, wrong-scope/key,
tamper and schema rejection, salt separation, and absent curator approval.
No real incident data, external key manager, service, model call, cloud resource,
production deletion or retention was exercised.
