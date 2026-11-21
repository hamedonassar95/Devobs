# PR Readiness Policy

## Deterministic decisions
- `READY_FOR_HUMAN_REVIEW`: required evidence verified by deterministic checks. **Not merge approval.**
- `BLOCKED`: failing/pending required checks or mergeability blockers.
- `INSUFFICIENT_EVIDENCE`: missing, stale, malformed, unknown, or contradictory evidence.
- `POLICY_VIOLATION`: security, dependency, ownership, workflow-permission, branch, or SHA integrity violations.

## Fail-closed rules
- Missing evidence never counts as success.
- Unknown/unavailable CI/security/dependency/mergeability evidence blocks readiness.
- Self-reported success is not verified CI; checks must include verifiable status/conclusion and head SHA.
- Contradictory or stale evidence is rejected.
- Untrusted PR content is never executed.

## Risk classification (deterministic)
`LOW|MEDIUM|HIGH|CRITICAL` computed by transparent rules: sensitive/infrastructure/auth file changes, workflow permission changes, dependency changes, security scan failures, missing approvals, ownership conflicts, missing/failed CI. No AI confidence score replaces required evidence.

## Human approval
Human approval is mandatory before merge. `READY_FOR_HUMAN_REVIEW` does not authorize merge, deploy, or production changes.
