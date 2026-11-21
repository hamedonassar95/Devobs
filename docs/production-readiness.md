# Production Readiness Intelligence Engine

## Purpose
Deterministic, offline, advisory-only production readiness evaluator for Devobs. It reports CI/CD, dependency/supply-chain, secret exposure, ownership conflict, PR risk, deployment configuration, observability, task duplication, and approval-gate risks from verified snapshot evidence.

## Safety boundaries
- Read-only evaluation; no merge, deploy, rollback, or destructive action.
- No paid services. No external API calls.
- AI analysis is optional, read-only, disabled by default, and non-authoritative; unauthorized AI requests are reported and blocked from influence.
- Missing/unknown/invalid evidence fails closed (`UNKNOWN` or `BLOCKED`).

## Snapshot inputs (JSON)
- `cicd.required_checks[]`, `cicd.observed_checks{check: PASS|FAIL|PENDING|MISSING|UNKNOWN}`
- `dependencies.components[] {name, depends_on[]}`, `dependencies.vulnerabilities[]`
- `security.secret_findings[]`
- `ownership.active_agents[] {agent,id,owned_paths[]}`
- `pull_requests[] {number, changed_files[], missing_tests, unverified}`
- `deployment.approval_gate`, `deployment.configs[] {name, allow_unauthenticated, debug, mutable_image_tag, missing_healthcheck}`
- `observability {logs,metrics,traces,alerts}`
- `tasks[] {id,fingerprint,owner}`
- `ai_analysis {enabled, provider, authorized, summary}` (optional, default off)

## Usage
```sh
python -m unittest discover -s tests/readiness -p "test_*.py" -v
python -c "import json; from tools.readiness.readiness_engine import evaluate_production_readiness; print(json.dumps(evaluate_production_readiness(json.load(open('snapshot.json'))), indent=2))"
```

## Report
Structured JSON includes status, severity/risk matrix, findings with remediation, and checks summary. Markdown report is human-readable. Human approval remains required before merge/deploy.