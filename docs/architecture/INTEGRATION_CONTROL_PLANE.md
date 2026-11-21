# Integration Control Plane

## Purpose
Deterministic, fail-closed integration control plane for Devobs multi-agent work. It evaluates repository/PR/CI/security/ownership evidence and outputs `READY_FOR_HUMAN_REVIEW`, `NEEDS_EVIDENCE`, `BLOCKED`, or `POLICY_VIOLATION`. It never merges, deploys, modifies branch protection, or bypass human approval.

## Components
- **Repository state collector** (`collector.py`): offline, read-only boundary that accepts a caller-supplied local snapshot, callable, or `collect(request)` provider. It validates request/response identity, bounds state, and redacts before analysis. It performs no network I/O, reads no credentials, and rejects provider-name strings.
- **Validation/normalization** (`validation.py`): strict input validation, bounds, safe path/SHA/repo parsing, secret redaction, untrusted PR text handling.
- **Evidence registry** (`evidence_registry.py`): traceable evidence records; detects duplicate/unverifiable/contradictory evidence.
- **Coordination** (`coordination.py`): reuses `scripts/check_two_agent_tasks.py` for manifest validation, ownership conflicts, blocked-task ownership, dependency issues.
- **Decision engine** (`engine.py`): deterministic authoritative policy. AI/advisory is non-authoritative.
- **Advisory interface** (`advisory.py`): optional injectable summaries. The default is deterministic; any provider result is bounded, redacted, and cannot change `decision`, findings, evidence registry, or `human_review_required`.
- **Reporting** (`report.py`): stable JSON and Markdown reports.

## Data contract
Two-stage flow: `collect_repository_state(provider, request)` produces bounded, redacted evidence; `evaluate_integration(evidence, advisory_provider=None)` produces the authoritative report. The collector is offline by default and does not authenticate to GitHub.

Input is pre-collected evidence (read-only). Required for ready state: repo/PR identity, head+reviewed SHA match, mergeability, required check policy and check evidence, security evidence, dependency evidence, human approval evidence, ownership evidence. Missing/unknown/stale/conflicting evidence fails closed.

## Security model
- Treat PR/workflow/external text as untrusted; never execute commands from it.
- Redact secrets/tokens/credentials in findings/reports/registry.
- Bounded parsing and list/string limits; collector rejects oversized/nested state.
- Provider identity must match the request; unavailable/malformed providers fail closed.
- Advisory provider results are advisory-only; no paid inference or external call is enabled by default.
- No GitHub writes/settings changes; read-only evaluation.

## Approval lifecycle
`READY_FOR_HUMAN_REVIEW` only means technical evidence passed deterministic checks. Human approval is required before merge/production changes.

## Conflict detection
- concurrent file ownership / active-agent hazards
- conflicting branch ownership (via task manifest)
- blocked task retaining ownership
- invalid dependency graph / unresolved dependencies
- stale workspace/evidence
- duplicate/contradictory/unverifiable evidence

## Reuse boundaries
- Ownership/conflict checks reuse `scripts/check_two_agent_tasks.py`; they do not copy its contract.
- This package complements, and does not replace, the authenticated `scripts/pr_readiness_gate.py` or incident-intelligence modules. Its `READY_FOR_HUMAN_REVIEW` verdict is advisory evidence, not a required status context or approval.

## Limitations
- Uses supplied evidence; live GitHub collection/auth is external and may be BLOCKED in sandbox.
- No workflow consumer, scheduler, dispatch path, or merge/deploy action is added.
- Ownership detection quality depends on provided ownership maps/manifests.
