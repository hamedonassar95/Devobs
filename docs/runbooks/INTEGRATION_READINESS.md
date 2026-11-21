# Integration Readiness Runbook

## CLI
```sh
python scripts/check_integration_readiness.py --input evidence.json --format json
python scripts/check_integration_readiness.py --input evidence.json --format markdown --output report.md
```

## Failure handling
- `UNKNOWN`: missing/unverified/unavailable evidence. Collect evidence and rerun.
- `BLOCKED`: conflicting/stale/invalid/failed evidence or policy violation. Remediate and rerun.
- `READY_FOR_HUMAN_REVIEW`: deterministic checks passed; human approval still required.

## Human approval
All merges require human approval. The tool never approves or merges.

## Rollback
Revert the feature branch commit or stop using the CLI/package; no production state is changed by this read-only tool.

## Troubleshooting
- Invalid JSON/SHA/path: fix input schema.
- Stale SHA: recollect evidence for current PR head.
- Ownership conflicts: resolve task manifest/file owners before rerun.
