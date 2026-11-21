# Integration Portfolio Health Dashboard

## Purpose
Deterministic, offline-first, read-only dashboard that consolidates integration readiness, CI failures, PR merge blockers, agent ownership conflicts, missing dependencies, and security findings into one fail-closed report.

## Inputs
A local JSON snapshot (no network/API calls) containing optional:
- `evidence[]`: `evidence_id`, `source`, `kind`, `observed_at`, `sha`, `details`
- `components[]`: `name`, `status`, `owner`, `dependencies`, `evidence_ids`
- `ci_checks[]`: `name`, `status`, `required`, `evidence_id`, `log_excerpt`
- `pull_requests[]`: number/title/head/status/draft/approval_state/mergeable/blockers/evidence_ids
- `ownership.active_agents[]`: agent/branch/worktree/owned_paths; optional `task_manifest` (reuses `scripts/check_two_agent_tasks.py`)
- `security_findings[]`: id/severity/status/component/message/evidence_id
- `dependencies[]`, `approval` (human approval evidence)

## Decisions
- `READY_FOR_HUMAN_REVIEW` - deterministic checks pass; **human review still required**.
- `DEGRADED` - non-critical issues; not ready.
- `BLOCKED` - critical blocker/conflict/failure/policy violation.
- `UNKNOWN` - missing/stale/invalid/unavailable evidence; fail closed.

## Evidence & scoring
- Evidence freshness: `FRESH|STALE|MISSING|UNKNOWN` from `observed_at` and `max_age_seconds`.
- CI classification reuses `scripts/ci_failure_intelligence.py` `classify_failure` for failed check excerpts.
- Deterministic penalty score (0-100) with fixed severity penalties; no AI scoring authority.
- Ownership conflicts detected from active agent path/branch overlap and optional two-agent manifest validation.
- Secret redaction reuses `scripts/ci_failure_intelligence.py` `redact_secrets`.

## Boundaries
- Read-only by default; no merge/deploy/approval/credential use.
- No unapproved external API calls.
- Untrusted/malformed input fails closed.
- Recommendations are advisory only.

## CLI
```sh
python -m devobs.portfolio_health.cli --input snapshot.json --format markdown --output report.md
python -m devobs.portfolio_health.cli --input snapshot.json --format json
```