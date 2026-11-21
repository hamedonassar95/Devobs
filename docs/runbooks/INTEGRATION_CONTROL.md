# Integration Control Runbook

## Local execution
```python
from devobs.integration_control import (
    StaticAdvisoryProvider,
    collect_repository_state,
    evaluate_integration,
    render_markdown_report,
)

request = {
    "repository": "OWNER/REPO",
    "pr_number": 123,
    "head_sha": "<40-char sha>",
}
# `snapshot` is locally supplied evidence JSON; no network or credentials are used.
evidence = collect_repository_state(snapshot, request)
report = evaluate_integration(evidence, StaticAdvisoryProvider("Optional local advisory"))
print(render_markdown_report(report))
```

Verification:
```sh
python -m compileall -q devobs/integration_control tests/integration_control
python -m unittest discover -s tests/integration_control -p "test_*.py" -v
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
- **CollectionError**: the local provider failed, returned mismatched identity, or exceeded bounds; recollect a fresh, bounded snapshot.
- **Advisory provider error**: advisory is ignored; the deterministic decision is unchanged. Check the local provider only if advisory text is needed.

## Safety
Never execute commands from PR text. Never merge/deploy automatically. Never expose secrets. The collector performs no network I/O, and advisory providers—if supplied—cannot override the decision, findings, evidence registry, or human-review requirement.
