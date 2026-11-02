# Local intelligence audit report

Run `python3 scripts/intelligence_report.py --database <existing-sqlite-path>`
to check an existing Devobs audit database and print a small JSON status report.
The command opens the database using `AuditStore.open_readonly`, verifies the
local hash chain, and reports only the chain status, record count, and final
record hash. It does not create or migrate a database, print event or project
identifiers, or make network calls. Errors use fixed codes and exit status 2.

To also verify a separately retained signed checkpoint, pass both files:

```bash
python3 scripts/intelligence_report.py \
  --database <existing-sqlite-path> \
  --signed-checkpoint <checkpoint-json-path> \
  --trusted-public-key <raw-ed25519-public-key-path>
```

The public key must be exactly 32 raw Ed25519 bytes and must come from a source
the operator already trusts; the checkpoint's `key_id` is only a fingerprint,
not a trust anchor. The checkpoint JSON is capped at 16 KiB and duplicate JSON
keys are rejected. Supplying only one optional argument, unreadable files,
malformed signatures, a mismatched key, or a checkpoint that does not match the
database prefix fails closed with a fixed error code. No private key is read.
When verification succeeds, the JSON report adds `signed_checkpoint` with the
signature result and signed prefix record count. Later valid appends are allowed
by the existing `AuditStore.verify_signed_checkpoint` contract.

This check proves only that the chain in the file was internally consistent
when read through this process. If a checkpoint is supplied, it also proves
that the signed prefix matches the chain under the supplied trusted public key.
It does not protect against a privileged actor rewriting both the database and
the independently retained checkpoint if they can also control the signing key
or trusted-key source. It does not prove checkpoint freshness: an older valid
signed prefix can be replayed if the operator cannot establish that it is the
current checkpoint. It also does not prove protected external retention,
authenticate that the signing key belongs to an authorized operator, or
establish a hosted service, AI inference, or production readiness.

Chain verification reads the ledger records to validate their order and hashes;
memory use therefore grows with the size of the local audit database.
