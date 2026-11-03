---
phase: testing
title: Evidence-sufficiency abstention trade-off tests
description: Verify sufficient-label rates, denominators, intervals, empty slices, and ledger evidence
---

# Testing

## Coverage

- Only cases labeled `sufficient` contribute to the new sufficient-evidence abstention rate.
- Sufficient and insufficient rates use separate explicit denominators.
- An empty label slice produces a null rate and interval with a zero denominator.
- Synthetic label validation, output schema versioning, fixture provenance, and report privacy remain in force.
- PR #410 merge evidence is bound to the exact head and merge SHAs, CI/CodeQL run IDs, and unchanged gate limits.

## Test-first evidence

The new sufficient-evidence metric tests initially failed because the report lacked `sufficient_evidence_abstention_rate`. After the implementation and schema update, both focused and full suites passed.

## Verification results

- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_intelligence_evaluation.py' -v` — 23 tests passed.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_milestone_ledger.py' -v` — 41 tests passed.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -v` — 814 tests passed, 22 skipped.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m compileall -q scripts tests` — passed.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m bandit -r scripts/devobs_intelligence/evaluation.py` — no issues identified.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python -m unittest discover -s tests -p 'test_intelligence_bom.py' -v` — 2 tests passed.
- `PYTHONPATH=scripts /tmp/devobs-p04-refusal-validation-20261103/bin/python -c 'from devobs_intelligence.evaluation import evaluate_fixture; r=evaluate_fixture(); print({k:r[k] for k in ("schema_version", "case_count", "live_model_calls", "sufficient_evidence_abstention_rate", "insufficient_evidence_abstention_rate")})'` — schema 3, five cases, zero live model calls; sufficient rate 0/4 and insufficient rate 1/1.
- `/tmp/devobs-p04-refusal-validation-20261103/bin/python scripts/milestone_ledger.py --summary` — latest PR 410, 86 merged milestones, three open gates; AI-9 and P01 remain blocked and Codex runtime remains open.
- `git diff --check` — passed. The v2 fixture SHA-256 remains `6ae90bdb0d5091d580d61b4f9b0356a4e6bb6c8bcdf408ca0e92deeb059afe23`.

No model API, paid provider, external runtime, deployment, or live dataset was used.
