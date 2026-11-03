---
phase: testing
title: Finding memory approval verification tests
description: Check signed provenance binding, scope isolation and fail-closed cases
---

# Testing

- Attested finding suite: 9 passed, including encrypted archive restore, correlation, signed-topology validation and curator approval verification end to end.
- Finding-memory provenance suite: 6 passed, including cross-tenant, missing, extra and invalid signatures, plus stale/future records and required/bounded age policy.
- Incident-memory approval suite: 15 passed.
- Full Python suite — 892 passed, 22 skipped.
- `python3 -m compileall -q scripts/devobs_intelligence tests` and `git diff --check` — passed.

The full suite used locked `psycopg[binary]==3.3.6` in a temporary target
outside the repository; that target was removed after verification.

All keys and records are generated synthetic fixtures. Tests do not establish
key enrollment, identity of a real curator, durable replay protection or live
data-source authenticity.
