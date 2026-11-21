# Integration Verification Hub

## Purpose
Deterministic, offline-first hub that inventories Devobs integration components, validates cross-component contracts/dependencies/ownership/evidence, and emits fail-closed release-readiness reports. Advisory only; never merges/deploys/approves.

## Component discovery
`inventory.py` scans known component paths under a repo root and classifies each as `IMPLEMENTED_AND_TESTED`, `IMPLEMENTED_UNVERIFIED`, `PARTIALLY_IMPLEMENTED`, `DOCUMENTATION_ONLY`, `ABSENT`, or `BLOCKED`. Discovery is evidence, not proof of CI success.

## Contract validation
`contracts.py` validates schema version, component shape, dependency declarations, evidence fields (`source`, `evidence_id`, commit SHA when present, verification method, timestamp, result), and detects contradictory PASS/FAIL evidence.

## Dependency/ownership validation
`evaluator.py` builds a deterministic dependency graph (iterative DFS for cycle detection), flags missing/cyclic/blocked dependencies. `ownership.py` reuses `scripts/check_two_agent_tasks.py` and active worktree ownership maps; blocked tasks retain ownership until explicitly released.

## Decision states
`READY_FOR_HUMAN_REVIEW | BLOCKED | INSUFFICIENT_EVIDENCE | POLICY_VIOLATION`. Missing/unknown/stale/contradictory evidence fails closed. Human approval remains mandatory.

## CLI
```sh
python -m devobs.integration_verification.cli --input evidence.json --format json --repo-root .
```

## Security boundaries
No secrets in reports (redaction). Bounded parsing, strict validation, no arbitrary command execution, no paid/external API calls, no repo mutation. AI/advisory inputs are non-authoritative.
