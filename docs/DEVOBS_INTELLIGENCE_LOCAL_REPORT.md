# Local intelligence audit report

Run `python3 scripts/intelligence_report.py --database <existing-sqlite-path>`
to check an existing Devobs audit database and print a small JSON status report.
The command opens the database using `AuditStore.open_readonly`, verifies the
local hash chain, and reports only the chain status, record count, and final
record hash. It does not create or migrate a database, print event or project
identifiers, or make network calls. Errors use fixed codes and exit status 2.

This check proves only that the chain in the file was internally consistent
when read through this process. It does not protect against a privileged actor
rewriting the database and its chain, prove protected external retention, verify
a signed checkpoint unless separately requested, or establish a hosted service,
AI inference, or production readiness.

Chain verification reads the ledger records to validate their order and hashes;
memory use therefore grows with the size of the local audit database.
