# Integration Verification Policy

## Fail-closed rules
- Missing/invalid/contradictory evidence => not ready.
- Self-reported agent success is not independently verified CI evidence.
- Blocked tasks retain ownership until explicit verified release.
- Conflicting ownership, invalid schema, or unsafe input => `POLICY_VIOLATION`.
- Missing dependency/cycle/blocked dependency => `BLOCKED` or `INSUFFICIENT_EVIDENCE` per deterministic rules.

## Approval
Human review is required before merge/deploy. `READY_FOR_HUMAN_REVIEW` does not authorize merge.

## Evidence minimum
Each positive claim: source, evidence_id, relevant commit SHA when applicable, verification method, verification timestamp, result.
