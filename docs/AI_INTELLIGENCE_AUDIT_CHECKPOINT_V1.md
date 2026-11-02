# AI Intelligence — audit checkpoint v1

**Scope:** offline checkpoint metadata for the existing local SQLite audit hash chain. It allows a separately retained checkpoint to detect later changes to the chain prefix.

## Record contract

`AuditStore.create_checkpoint()` verifies the current chain, then returns this strict record shape:

```json
{
  "schema_version": 1,
  "record_count": 3,
  "head_hash": "<64 lowercase hexadecimal characters>"
}
```

For an empty chain, `record_count` is zero and `head_hash` is 64 zeroes. The parser rejects unsupported versions, booleans in integer fields, negative counts, malformed hashes, inconsistent empty-chain values, and extra fields.

## Verification behavior

`AuditStore.verify_checkpoint(record)` validates the checkpoint, verifies the whole current local chain, then compares the stored hash at the checkpoint's record count. Later valid appends are allowed. A shorter chain or a different hash at that prefix raises the fixed `checkpoint_mismatch` error; a malformed record raises `invalid_checkpoint`. The method returns the current verified chain length after a successful comparison.

The offline demo exposes its checkpoint in JSON output after all demo audit writes. The caller must retain the record in a separately protected location to make later comparison useful.

## Limits

The checkpoint is not signed, timestamped by a trusted clock, or automatically archived. It does not identify the operator or authenticate the audit writer. It detects a rewritten chain only when the independently retained checkpoint remains trustworthy; an actor able to replace both the database and checkpoint can forge a matching pair. No network service, new dependency, customer data, or production action is involved.

Focused checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_audit_store.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_demo.py' -v
```
