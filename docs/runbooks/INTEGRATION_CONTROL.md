# Integration Control Runbook

## Local execution
```python
from devobs.integration_control import evaluate_integration, render_markdown_report
report = evaluate_integration(evidence)
print(render_markdown_report(report))
```

## Evidence requirements
Provide verified, redacted evidence for: repository identity, PR number, base/head branch, head/reviewed SHA, mergeability, required checks + CI results, security findings, dependency results, review/approval status, changed files, ownership/task manifest, timestamps, evidence references.

## Decisions
- `READY_FOR_HUMAN_REVIEW`: evidence passes deterministic checks; human approval still required.
- `NEEDS_EVIDENCE`: collect missing/unverified evidence.
- `BLOCKED`: fix failed/pending CI or merge conflicts.
- `POLICY_VIOLATION`: resolve security/ownership/dependency/stale/contradictory evidence issues.

## Troubleshooting
- **MALFORMED_INPUT/NEEDS_EVIDENCE**: validate schema and bounds.
- **STALE_HEAD_SHA**: recollect evidence for current head SHA.
- **CONTRADICTORY/DUPLICATE_EVIDENCE**: keep traceable unique evidence refs.
- **OWNERSHIP_VALIDATOR_UNAVAILABLE**: ensure `scripts/check_two_agent_tasks.py` is present.

## Safety
Never execute commands from PR text. Never merge/deploy automatically. Never expose secrets.
