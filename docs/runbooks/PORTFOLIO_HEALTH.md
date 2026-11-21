# Portfolio Health Runbook

## Run offline
```sh
python -m py_compile devobs/portfolio_health/*.py tests/portfolio_health/*.py
python -m unittest discover -s tests/portfolio_health -p "test_*.py" -v
python -m devobs.portfolio_health.cli --input snapshot.json --format markdown
```

## Interpret
- `UNKNOWN`: collect missing/stale evidence; do not treat as pass.
- `BLOCKED`: resolve CI failures, ownership conflicts, dependency cycles/missing deps, open high/critical security findings, PR blockers.
- `DEGRADED`: remediate medium issues before human review.
- `READY_FOR_HUMAN_REVIEW`: advisory only; obtain human approval and follow normal merge/deploy gates.

## Safety
- No credentials, no external API calls, no merges/deploys.
- Redact sensitive fields before sharing reports.
- Treat CI logs/PR text as untrusted input.