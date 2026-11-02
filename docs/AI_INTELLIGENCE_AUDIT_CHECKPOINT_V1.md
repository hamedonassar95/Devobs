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

## Optional signed envelope v1

`AuditStore.create_signed_checkpoint(private_key)` wraps the unchanged checkpoint record in a strict Ed25519 envelope. The signature covers a domain-separated canonical JSON encoding of the schema version, algorithm, SHA-256 public-key fingerprint, and checkpoint. Signatures use unpadded URL-safe base64. `AuditStore.verify_signed_checkpoint(record, trusted_public_key)` requires the verifier to supply the trusted public key separately, verifies the key fingerprint and signature, and then checks the local ledger prefix using `verify_checkpoint`.

The envelope contains no public key or private key. The signer passes an Ed25519 private-key object to the creation method; this component does not load, create, serialize, store, display, or send keys. The verifier may supply an Ed25519 public-key object or exactly 32 raw public-key bytes. Malformed envelopes, keys that do not match `key_id`, and invalid signatures fail closed with fixed error codes. Existing unsigned checkpoint v1 records remain valid and unchanged.

## Limits

Signing is optional. A signed checkpoint is not timestamped by a trusted clock or automatically archived, and it does not identify a human operator or authenticate the audit writer. The caller must retain the envelope separately and obtain the public key from a trusted source; a signature proves possession of that key, not that the key is authorized. Key enrollment, rotation/revocation, HSM/KMS, protected external retention, and hosted audit storage remain out of scope. A party able to replace the database and the independently held checkpoint, or control the signing key and trust configuration, can still defeat the intended evidence boundary. No service or production action is involved.

Focused checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_audit_store.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_demo.py' -v
```

Cryptographic implementation references: [Python cryptography Ed25519 API](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) and [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032).
