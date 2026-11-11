---
phase: testing
title: Legacy topology incident-memory abstention tests
description: Ensure unprovenanced memory cannot affect legacy topology findings
---

# Testing

The correlation contract test now asserts that a legacy `ServiceTopology`
continues to rank evidence and calculate impact while returning no runbooks or
memory provenance. The approved archive-restore integration test covers the
positive path for source-bound, fresh topology plus active signed memory.

- `python3 -m unittest discover -s tests -p 'test_intelligence_correlation.py' -v` — 17 passed.
- `python3 -m unittest discover -s tests -p 'test_intelligence_incident_memory_encryption.py' -v` — 10 passed.
- `python3 -m unittest discover -s tests -p 'test_intelligence_demo.py' -v` — 9 passed.
- Full Python suite — 885 passed, 22 skipped.
- `python3 -m compileall -q scripts/devobs_intelligence tests` and `git diff --check` — passed.

Tests use synthetic topology, telemetry and memory. They do not prove a live
collector, authenticated production topology, durable replay defense, or
calibrated incident quality.
