# PR Readiness Operations

## Inputs
Offline JSON evidence: PR identity, base/head/reviewed SHAs, mergeability, required checks, CI checks, security findings, dependency results, reviews/approvals, changed files, ownership/task manifest, timestamps.

## Outputs
JSON and Markdown reports with decision, risk, passed/failed/missing/blocking findings, remediation, human approval requirement, evaluation timestamp, provenance fields.

## Local execution
```sh
python -m compileall -q devobs
python -m pytest -q tests/pr_readiness
python -m ruff check devobs/pr_readiness tests/pr_readiness
python scripts/check_integration_readiness.py --input evidence.json --format markdown  # related tool
```

## Failure handling
- Invalid/malformed/oversized input: `INSUFFICIENT_EVIDENCE`/blocked finding, no crash-leak of secrets.
- Unavailable GitHub/API evidence: fail closed as `INSUFFICIENT_EVIDENCE`/`BLOCKED`.
- Conflicts/violations: `POLICY_VIOLATION`.

## Human approval process
Operator reviews report, verifies evidence provenance, obtains required human approval. No automatic merge.

## Rollback
Revert branch commit; tool is read-only and has no persistent production side effects.
