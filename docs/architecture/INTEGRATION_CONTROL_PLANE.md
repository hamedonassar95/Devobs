# Integration Control Plane

## Purpose
Deterministic, fail-closed integration control plane for Devobs multi-agent work. It evaluates repository/PR/CI/security/ownership evidence and outputs `READY_FOR_HUMAN_REVIEW`, `NEEDS_EVIDENCE`, `BLOCKED`, or `POLICY_VIOLATION`. It never merges, deploys, modifies branch protection, or bypass human approval.

## Components
- **Validation/normalization** (`devobs/integration_control/validation.py`): strict input validation, bounds, safe path/SHA/repo parsing, secret redaction, untrusted PR text handling.
- **State collection** (`collector.py`): offline-first, read-only collection from a caller-supplied mapping, callable, or `collect(request)` provider. It binds repository/PR/SHA identity, bounds state, and redacts output before evaluation.
- **Pipeline** (`pipeline.py`): `evaluate_collected_integration(provider, request, advisory_provider=None)` connects collection to the engine. Collection errors become a fail-closed `NEEDS_EVIDENCE` report with `COLLECTION_UNAVAILABLE`; they never silently pass.
- **Coordination** (`coordination.py`): reuses `scripts/check_two_agent_tasks.py` for manifest validation, ownership conflicts, blocked-task ownership, dependency issues, and stale workspace evidence.
- **Evidence registry** (`evidence_registry.py`): traceable evidence records; detects duplicate/unverifiable/contradictory evidence.
- **Decision engine** (`engine.py`): deterministic authoritative policy. The decision precedence is `POLICY_VIOLATION` > `BLOCKED` > `NEEDS_EVIDENCE` > `READY_FOR_HUMAN_REVIEW`.
- **Advisory boundary** (`advisory.py`): optional, offline, non-authoritative advice. `build_advisory` passes only a redacted copy of the finished deterministic report to a caller-supplied `advise()` callable or object, then keeps only bounded, redacted `summary` and `recommendations`. Provider name strings, malformed responses, and provider errors fail closed to an `advisory-unavailable` block.
- **Reporting** (`report.py`): stable JSON and Markdown reports; Markdown labels advisory output as non-authoritative.

The existing read-only `scripts/pr_readiness_gate.py` remains a separate live GitHub evidence source. This package does not duplicate its CLI or hosted API calls; callers supply already-collected evidence or a local provider.

## Data contract
Input is pre-collected evidence (read-only). Required for a ready state: repo/PR identity, matching head and reviewed SHA, mergeability, required-check policy and check evidence, security evidence, dependency evidence, human-approval evidence, changed files, ownership evidence, and traceable evidence records. Missing, unknown, stale, or conflicting evidence fails closed.

The collector request is bounded and requires `repository` (`OWNER/REPO`), positive integer `pr_number`, and an optional 40-character `head_sha`. A provider response that does not match the request identity is rejected.

## Security model
- Treat PR/workflow/external text and advisory output as untrusted data; never execute commands from them.
- Redact secrets/tokens/credentials in findings, reports, registry, and advisory text.
- Bound request fields, state depth/nodes, list sizes, string lengths, and advisory recommendations.
- Fail closed on missing tools, malformed responses, provider errors, or unexpected shapes.
- No dynamic import, provider resolution by name, network call, or shell execution from request data.
- No GitHub writes, settings changes, merge, deploy, or production mutation.

## Advisory separation
Advisory output cannot change the decision, findings, evidence registry, coordination result, or `human_review_required`. The deterministic engine computes and redacts the full report first; only then does the advisory boundary run. The default `DeterministicAdvisoryProvider` maps finding codes to offline guidance. An injected provider may be a local object with `advise(report)` or a callable; it receives only the redacted report. Its return value is reduced to a summary and at most 20 recommendations of at most 300 characters each.

## Approval lifecycle
`READY_FOR_HUMAN_REVIEW` only means technical evidence passed deterministic checks. Human approval is required before merge or production changes. `READY_FOR_HUMAN_REVIEW` is not an approval record and grants no merge authority.

## Conflict detection
- concurrent file ownership / active-agent hazards
- conflicting branch ownership (via task manifest)
- blocked task retaining ownership
- invalid dependency graph / unresolved dependencies
- stale workspace/evidence
- duplicate/contradictory/unverifiable evidence
- stale head SHA across PR, CI, security, and evidence records

## Verification surface
Focused local checks:
```sh
python -m compileall -q devobs/integration_control tests/integration_control
python -m unittest discover -s tests/integration_control -p "test_*.py" -v
```

## Limitations
- Uses supplied evidence; live GitHub collection/auth is external and may be unavailable in a sandbox.
- Ownership detection quality depends on provided ownership maps/manifests.
- The evidence registry is in-memory for one evaluation; it is not a signed persistent attestation store.
- Advisory providers are local/offline by contract; this package contains no paid inference or outbound API client.
