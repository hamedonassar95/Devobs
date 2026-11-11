# AuditStore read-only verification — preregistration

**Status:** REGISTERED BEFORE IMPLEMENTATION TESTS  
**Base revision:** `27349fcdb9f3753a7bc686dd2177795ef005014d` (main after PR #389)  
**Scope:** local SQLite audit checkpoint verification only. No service, network, hosted storage, key loading, or production operation.

## Objective

Provide a fail-closed way to verify an existing audit ledger without invoking the normal `AuditStore` constructor, which creates or migrates its schema. The verifier must not create a missing file, change the schema, or permit writes through the returned store connection.

## Frozen API and behavior

Add `AuditStore.open_readonly(path: str) -> AuditStore` with these outcomes:

1. Reject non-string, empty, SQLite `file:` URI, NUL-containing, and final-component symbolic-link paths with `AuditError('invalid_path')`.
2. Require an existing regular file. Missing files, directories, corrupt databases, and SQLite open/read failures return the fixed `AuditError('storage_unavailable')`; a missing file remains absent.
3. Open the resolved file using SQLite URI `mode=ro`, with URI interpretation enabled, and set connection-level `PRAGMA query_only=ON`.
4. Require the existing `audit` table and all columns consumed by the verifier (`seq`, `event_id`, `source_sha`, `policy_version`, `decision`, `action`, `previous_hash`, `record_hash`, `subject_digest`). Missing or incompatible schema returns `AuditError('unsupported_schema')`; this path performs no DDL or migration.
5. On success, support existing verification and checkpoint-reading methods. All append/record operations fail with the fixed `AuditError('read_only_store')`, and direct SQL write attempts are rejected by SQLite.
6. Close the connection on every failure after opening it.

## Acceptance checks to run after registration

- A signed checkpoint and its chain verify after opening through `open_readonly`.
- `append` and direct `INSERT`, `UPDATE`, and `DELETE` are denied.
- The database file bytes and schema are unchanged by open/verify/close.
- Missing files are not created; legacy/missing-column schemas are rejected without migration.
- URI, invalid-type, NUL, and symlink paths fail with the specified fixed error.
- Existing writable `AuditStore(path)` behavior remains unchanged.
- Focused audit-store tests, the full Python suite, Node suite, milestone-ledger validator, compile checks, and `git diff --check` pass before publishing a PR.

## Non-goals and limitations

This mode protects against writes made through this SQLite connection; it is not an operating-system sandbox and cannot prevent another process or privileged host operator from changing the file. It does not provide immutable media, independent retention, trusted timestamps, key enrollment/revocation, live service verification, or tamper-proof storage. It must not change the AI-9, P01, or Codex runtime readiness gates.

## References

- Python `sqlite3` URI handling: <https://docs.python.org/3/library/sqlite3.html#how-to-work-with-sqlite-uris>
- SQLite read-only URI parameter: <https://www.sqlite.org/uri.html#uri_readonly>
