# Integration Control Runbook

## Local execution
Evaluate an already-collected, redacted evidence mapping:

```python
from devobs.integration_control import evaluate_integration, render_markdown_report

report = evaluate_integration(evidence)
print(render_markdown_report(report))
```

Collect from a local provider and evaluate in one fail-closed boundary:

```python
from devobs.integration_control import evaluate_collected_integration, render_json_report

request = {
    "repository": "OWNER/REPO",
    "pr_number": 123,
    "head_sha": "<40-char-sha>",
}
report = evaluate_collected_integration(local_provider, request)
print(render_json_report(report))
```

`local_provider` may be an in-memory mapping, a callable, or an object exposing `collect(request)`. The package performs no network I/O and resolves no provider by name.

## Optional advisory provider
The default advisory is offline and deterministic. A local provider can be injected without changing authority:

```python
class LocalAdvisor:
    def advise(self, redacted_report):
        return {
            "summary": "Review the highest-severity finding first.",
            "recommendations": ["Recheck CI after the next push."],
        }

report = evaluate_integration(evidence, advisory_provider=LocalAdvisor())
```

The provider receives only the redacted deterministic report. It cannot alter `decision`, `findings`, `evidence_registry`, `coordination`, or `human_review_required`. Its output is limited to a summary and at most 20 recommendations of 300 characters each. Invalid, unavailable, or oversized provider output becomes `advisory-unavailable`; the deterministic decision is unchanged.

## Evidence requirements
Provide verified, redacted evidence for: repository identity, PR number, base/head branch, head/reviewed SHA, mergeability, required checks + CI results, security findings, dependency results, review/approval status, changed files, ownership/task manifest, timestamps, and evidence references.

## Decisions
- `READY_FOR_HUMAN_REVIEW`: evidence passes deterministic checks; human approval is still required.
- `NEEDS_EVIDENCE`: collect missing or unverified evidence.
- `BLOCKED`: fix failed/pending CI or merge conflicts.
- `POLICY_VIOLATION`: resolve security/ownership/dependency/stale/contradictory evidence issues.
- `COLLECTION_UNAVAILABLE` finding with `NEEDS_EVIDENCE`: the local provider failed; no evidence was inferred.

## Troubleshooting
- **MALFORMED_INPUT / NEEDS_EVIDENCE**: validate schema and bounds.
- **COLLECTION_UNAVAILABLE**: fix the local provider; verify request identity and head SHA binding.
- **STALE_HEAD_SHA**: recollect all evidence for the current head SHA.
- **CONTRADICTORY / DUPLICATE_EVIDENCE**: keep traceable unique evidence refs.
- **OWNERSHIP_VALIDATOR_UNAVAILABLE**: ensure `scripts/check_two_agent_tasks.py` is present.
- **advisory-unavailable**: fix the injected local provider; the authoritative report is still valid.

## Safety
Never execute commands from PR text or advisory output. Never merge or deploy automatically. Never expose secrets. Never pass credentials or tokens to this package; it does not need them.

## Verification
```sh
python -m compileall -q devobs/integration_control tests/integration_control
python -m unittest discover -s tests/integration_control -p "test_*.py" -v
```
