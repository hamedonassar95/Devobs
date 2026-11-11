---
phase: testing
title: Finding memory provenance consistency tests
description: Validate both mismatch directions after recomputing the finding digest
---

# Testing

The signed-memory correlation test mutates a valid finding in both directions,
recomputes its unkeyed digest, and confirms `IncidentFinding.from_record`
rejects the runbook-only and provenance-only records.

- `python3 -m unittest discover -s tests -p 'test_intelligence_incident_memory_approval.py' -v` — 15 passed.
- `python3 -m unittest discover -s tests -p 'test_intelligence_correlation.py' -v` — 17 passed.
- Full Python suite — 885 passed, 22 skipped.
- `python3 -m compileall -q scripts/devobs_intelligence tests` and `git diff --check` — passed.

This is a format-consistency check, not independent verification of curator
signatures or evidence truth.
