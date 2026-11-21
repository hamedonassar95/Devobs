# Integration Verification Runbook

## Run
```sh
python -m py_compile devobs/integration_verification/*.py tests/integration_verification/*.py
python -m unittest discover -s tests/integration_verification -p "test_*.py" -v
python -m devobs.integration_verification.cli --input input.json --format markdown --repo-root .
```

## Inputs
JSON object with optional `repository`, `head_sha`, `components`, `ownership`, `evidence`, `approval`. Missing fields fail closed.

## Failure handling
- `INSUFFICIENT_EVIDENCE`: collect required evidence.
- `BLOCKED`: resolve dependencies/conflicts/blocked tasks.
- `POLICY_VIOLATION`: remediate contract/ownership/contradiction/unsafe input.
- `READY_FOR_HUMAN_REVIEW`: only after independent evidence and human approval.

## Limitations
Inventory is local/static; CI evidence must be supplied as verified evidence. No GitHub mutation.
