# PR Readiness and Security Evidence Engine

**Status:** Deterministic, fail-closed, read-only governance engine. It evaluates pre-collected evidence and produces JSON/Markdown readiness reports. It never approves, merges, deploys, or modifies GitHub state.

## Purpose

Integrate existing PR validation signals, CI/test evidence, security scan evidence, and human approval requirements into a single explainable readiness decision:

- `READY_FOR_HUMAN_REVIEW`
- `PENDING`
- `BLOCKED`
- `UNVERIFIED`

**Fail-closed rule:** missing, stale, malformed, conflicting, or unverified evidence never produces `READY_FOR_HUMAN_REVIEW`.

## Architecture

The implementation is split by responsibility:

1. **Evidence validation/normalization** - `devobs/governance/evidence_validator.py`
   - Validates schema/types/SHAs/timestamps/branch names.
   - Normalizes check, security, and approval evidence.
   - Detects stale SHA mismatches, duplicate checks, malformed inputs.
   - Redacts sensitive values (tokens, secrets, bearer credentials, AWS-style keys) from report-safe outputs.
   - Treats self-reported/unverified approvals as non-authoritative.

2. **Policy evaluation** - `devobs/governance/pr_readiness.py`
   - Deterministic policy decision over normalized evidence.
   - Separates evidence issues from policy outcomes.
   - Produces stable JSON report and human-readable Markdown.
   - Explainable reasons with `code`, `message`, `source`, `severity`.

3. **Tests/fixtures** - `tests/governance/`
   - Offline unit tests, no network access.
   - Covers required regression scenarios.

## Input contract (evidence)

The engine accepts a Python mapping or JSON string/bytes. Minimal shape:

```json
{
  "pr": {
    "branch": "feature/example",
    "base": "main",
    "head_sha": "<40-hex-sha>",
    "title": "optional"
  },
  "required_checks": ["validate", "security"],
  "checks": [
    {"name": "validate", "status": "completed", "conclusion": "success", "head_sha": "<40-hex-sha>"}
  ],
  "security_evidence": [
    {"name": "bandit", "status": "pass", "head_sha": "<40-hex-sha>"}
  ],
  "approvals": [
    {"actor": "alice", "state": "approved", "head_sha": "<40-hex-sha>", "source_type": "github_review", "verified": true}
  ],
  "required_approvals": 1,
  "protected_branch": true
}
```

## Decision rules

| Condition | State |
|---|---|
| Failed/stale/conflicting/invalid policy evidence | `BLOCKED` |
| Missing/unverified/unknown/malformed evidence | `UNVERIFIED` |
| Pending checks/evidence, no blocking/unverified findings | `PENDING` |
| All required checks pass, security evidence verified/pass, authoritative approvals meet requirement, head SHA/branch valid | `READY_FOR_HUMAN_REVIEW` |

## Security and safety

- No network access in unit tests; evaluation is local and deterministic.
- No secrets in reports: sensitive keys/values redacted.
- Self-reported approval is never authoritative.
- Missing security evidence cannot produce ready state.
- No automatic PR approval/merge/deploy behavior.

## Usage

```python
from devobs.governance import evaluate_pr_readiness, render_markdown_report

report = evaluate_pr_readiness(evidence)
markdown = render_markdown_report(report)
```

## Verification

```sh
python -m py_compile devobs/governance/__init__.py devobs/governance/evidence_validator.py devobs/governance/pr_readiness.py
python -m unittest tests.governance.test_evidence_validator tests.governance.test_pr_readiness -v
git diff --check
```

## Limitations

- This engine evaluates supplied evidence; it does not itself call GitHub APIs. External evidence collection must be authenticated, read-only, and preserved as artifacts for audit.
- Existing `scripts/pr_readiness_gate.py` remains the GitHub-CLI-backed read-only gate; this engine provides a reusable deterministic governance model for offline/fixture and evidence-object evaluation.
