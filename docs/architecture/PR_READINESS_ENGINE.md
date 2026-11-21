# PR Readiness Engine

## Purpose
A deterministic, fail-closed, read-only engine that evaluates pull request evidence for human review readiness. It does **not** approve, merge, deploy, modify GitHub settings, or bypass branch protection.

## Architecture
- `devobs/pr_readiness/evidence.py` - input validation, bounds, redaction, normalization. Treats PR content as untrusted; rejects malformed/unsafe structures.
- `devobs/pr_readiness/ownership.py` - multi-agent ownership/conflict detection. Reuses `scripts/check_two_agent_tasks.py` when a task manifest is provided.
- `devobs/pr_readiness/policy.py` - deterministic policy evaluation. Authoritative decision source.
- `devobs/pr_readiness/advisory.py` - optional non-authoritative advisory summary from deterministic findings.
- `devobs/pr_readiness/report.py` - stable JSON and Markdown rendering with redaction.
- `devobs/pr_readiness/models.py` - typed data models and decision constants.

## Decisions
- `READY_FOR_HUMAN_REVIEW` - all required evidence verified; human approval still required before merge.
- `BLOCKED` - required checks failed/pending or mergeability blocked.
- `INSUFFICIENT_EVIDENCE` - required evidence missing, unavailable, unknown, stale-required-check, or malformed.
- `POLICY_VIOLATION` - security/dependency/ownership/branch/stale-head violations.

## Evidence inputs
The engine evaluates pre-collected evidence (no network calls in unit tests). Expected fields include PR identity, base/head, head/reviewed SHA, mergeability, required checks, CI check results, security findings, dependency results, reviews/approvals, changed files, timestamps, and optional ownership/task manifest.

## Security boundaries
- No secrets in reports: tokens/credentials/bearer/AWS-style values redacted.
- Missing or inconsistent evidence fails closed.
- PR text/content is untrusted; no commands from PR content are executed.
- Deterministic rules override any advisory output.
- No GitHub settings/branch protection modifications.

## Limitations
- Readiness is not merge authorization.
- Live GitHub collection requires authenticated read-only tooling and is outside unit tests.
- Ownership conflict detection is strongest when file owners or task manifest evidence is supplied.


## Risk scoring
Deterministic, transparent `LOW|MEDIUM|HIGH|CRITICAL` classification based on sensitive file paths, workflow permissions, infrastructure/auth/dependency changes, security scan failures, missing approvals, ownership conflicts, and CI evidence. No AI-generated confidence score substitutes for required evidence.

## Optional AI advisory
Disabled by default, offline/mock only, no paid API calls, no external transmission by default. Advisory cannot override deterministic decisions and never approves/merges.
