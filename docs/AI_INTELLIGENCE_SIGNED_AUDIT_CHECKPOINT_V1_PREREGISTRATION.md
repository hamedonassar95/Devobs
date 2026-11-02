# Signed audit checkpoint v1 — preregistration

**Status:** Registered before implementation or feature tests.  
**Base:** `7cb400b5d90c2935c98e76aad7c5335a77aa48b5` (main after PR #388).  
**Scope:** Add an opt-in Ed25519 signature envelope around the existing local audit-chain checkpoint. No change to the audit hash-chain format or existing unsigned checkpoint API.

## Design frozen for this change

The signed envelope has exactly these fields:

```json
{
  "schema_version": 1,
  "algorithm": "ed25519",
  "key_id": "<lowercase SHA-256 hex of the raw 32-byte public key>",
  "checkpoint": {
    "schema_version": 1,
    "record_count": 0,
    "head_hash": "<64 lowercase hex characters>"
  },
  "signature": "<unpadded URL-safe base64 of the 64-byte Ed25519 signature>"
}
```

The signature covers a domain separator (`devobs-audit-checkpoint-v1\n`) followed by ASCII canonical JSON (sorted keys, compact separators, `ensure_ascii=true`) of the envelope fields except `signature`. The verifier receives the trusted public key separately; an envelope-provided key is never trusted. Its raw-key SHA-256 must match `key_id`. Signing and verification accept cryptography key objects or, for verification only, exactly 32 raw public-key bytes. The API does not load, serialize, generate, store, print, or transmit private keys.

The store exposes `create_signed_checkpoint(private_key)` and `verify_signed_checkpoint(record, trusted_public_key)`. Verification checks the strict envelope and signature first, then delegates the embedded checkpoint to existing `verify_checkpoint`, preserving detection of a rewritten/truncated chain prefix and allowing valid later appends.

## Acceptance criteria

1. The existing unsigned checkpoint v1 record and methods remain byte/schema compatible.
2. A signed checkpoint can be verified with its separately supplied trusted key; a valid later append remains accepted.
3. Wrong public key, mismatched key ID, modified checkpoint, modified signature, malformed envelope, unsupported algorithm/version, and noncanonical signature encoding fail closed with fixed error codes.
4. A validly recomputed local hash chain that rewrites a signed checkpoint's anchored prefix is rejected by the store after signature verification.
5. The same checkpoint and Ed25519 key produce the same signature; the envelope contains no private-key bytes.
6. Tests use only ephemeral in-memory keys and disposable synthetic SQLite fixtures. No key files, services, network access, production detector changes, or AI-9 scoring are introduced.

## Boundaries and known limits

The signer remains responsible for protecting the private key and independently distributing/trusting the public key. This feature does not add key rotation/revocation, trusted timestamps, external checkpoint retention, operator identity, HSM/KMS integration, access control, multi-writer coordination, or hosted audit storage. A valid signature proves that the corresponding key signed the stated bytes; it does not establish that the key is authorized, that its holder is a human, or that the checkpoint was retained independently. The existing audit ledger remains a local logical audit store, not a tamper-proof service.

No detector thresholds, evaluation policy, readiness gate, provider, deployment, or billing configuration may change in this work.
