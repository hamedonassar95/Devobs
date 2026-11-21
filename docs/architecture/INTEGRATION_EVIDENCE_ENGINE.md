# Integration Evidence Engine

## Overview
Extends `devobs/integration_control` with deterministic, offline-first evidence verification and readiness reporting for multi-agent contributions. It is read-only and fail-closed.

## Evidence states
- `VERIFIED`: evidence present, valid, and consistent.
- `UNVERIFIED`: missing or unknown evidence.
- `STALE`: evidence does not match current head SHA / stale workspace.
- `CONFLICTED`: contradictory or ownership/branch conflicts.
- `BLOCKED`: invalid or failed evidence/policy.
- `UNKNOWN`: cannot determine safely.

## Readiness states
- `READY_FOR_HUMAN_REVIEW`
- `BLOCKED`
- `UNKNOWN`

No auto-merge decision is produced.

## Components
- `evidence.py`: SHA/CI/approval/evidence-record verification primitives.
- `conflicts.py`: ownership, duplicate task IDs, branch ownership, stale evidence, dependencies, blocked task ownership, evidence consistency.
- `readiness.py`: deterministic readiness evaluation combining evidence + conflicts + existing engine.
- `reporting.py`: JSON/Markdown report with required fields.
- `scripts/check_integration_readiness.py`: offline CLI.

## Security boundaries
- Untrusted evidence/content never executed.
- Secret redaction in reports.
- Strict validation and path traversal protection.
- Bounded input sizes; fail closed.
- Read-only analysis; no merge/deploy/GitHub mutation.
