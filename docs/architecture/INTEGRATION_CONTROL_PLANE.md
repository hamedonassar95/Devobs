# Integration Control Plane

## Purpose
Deterministic, fail-closed integration control plane for Devobs multi-agent work. It evaluates repository/PR/CI/security/ownership evidence and outputs `READY_FOR_HUMAN_REVIEW`, `NEEDS_EVIDENCE`, `BLOCKED`, or `POLICY_VIOLATION`. It never merges, deploys, modifies branch protection, or bypass human approval.

## Components
- **Validation/normalization** (`devobs/integration_control/validation.py`): strict input validation, bounds, safe path/SHA/repo parsing, secret redaction, untrusted PR text handling.
- **Evidence registry** (`evidence_registry.py`): traceable evidence records; detects duplicate/unverifiable/contradictory evidence.
- **Coordination** (`coordination.py`): reuses `scripts/check_two_agent_tasks.py` for manifest validation, ownership conflicts, blocked-task ownership, dependency issues.
- **Decision engine** (`engine.py`): deterministic authoritative policy. AI/advisory is non-authoritative.
- **Reporting** (`report.py`): stable JSON and Markdown reports.

## Data contract
Input is pre-collected evidence (read-only). Required for ready state: repo/PR identity, head+reviewed SHA match, mergeability, required check policy and check evidence, security evidence, dependency evidence, human approval evidence, ownership evidence. Missing/unknown/stale/conflicting evidence fails closed.

## Security model
- Treat PR/workflow/external text as untrusted; never execute commands from it.
- Redact secrets/tokens/credentials in findings/reports/registry.
- Bounded parsing and list/string limits.
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

## Limitations
- Uses supplied evidence; live GitHub collection/auth is external and may be BLOCKED in sandbox.
- Ownership detection quality depends on provided ownership maps/manifests.
