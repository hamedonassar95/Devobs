# AgentDust Read-Only Adapter

## Purpose and trust boundary

`scripts/agentdust_readonly_adapter.py` accepts one explicitly supplied local path to an AgentDust `doctor --json` report. The report is untrusted input. The adapter validates its bounded JSON shape and emits aggregate counts only. It does not establish that the report came from AgentDust, that the binary was authentic, or that the report describes the current host. The module uses Python 3.10 or newer.

The caller is responsible for choosing the report file and protecting its directory. The adapter rejects symlinks in every path component, opens only a regular file, and caps bytes read at 2 MiB plus one detection byte. It uses standard-library file operations and JSON parsing only.

## Threat model

The adapter is designed to limit damage from malformed or hostile local report files, including oversized input, duplicate JSON keys, invalid encoding, unexpected schema, symlink substitution, special files such as FIFOs, and sensitive strings embedded in findings. It does not inspect finding contents. Error output consists only of fixed adapter error codes.

The adapter does not run AgentDust, a shell, subprocesses, or network requests. It does not modify the report. It parses the JSON document but does not inspect, transform, or emit finding entries. The underlying OS, Python runtime, filesystem, and caller-selected path remain trusted. Hard links cannot be distinguished from ordinary regular files by this interface; callers should place reports in a directory they control.

## Accepted input schema

The input must be UTF-8 JSON with a top-level object containing:

* `version`: integer `1` (booleans are not accepted as integers).
* `counts`: an object with exactly `managed`, `owned-live`, `owned-ended`, `likely-owned`, `suspect`, and `unknown`; each value must be a nonnegative integer.
* `findings`: an array with at most 10,000 elements. Elements are deliberately not read into the output.

The entire file must be no larger than 2 MiB. Duplicate object keys and non-standard JSON numeric constants are rejected.

## Output

For a valid input, the CLI writes one JSON object to stdout containing only `status_code`, `processes_detected` (the sum of the six counts), and `findings_count`. `status_code` is the fixed value `REPORT_VALID`. It does not include individual counts, PIDs, command lines, paths, or finding contents.

For rejected input, stdout remains empty, the process exits with status 2, and stderr contains only `adapter_error=<fixed-code>`. The provided path and exception text are never printed.

Example invocation:

```sh
python3 scripts/agentdust_readonly_adapter.py /controlled/path/doctor.json
```

## Security limits

The reader requires POSIX `dir_fd` support plus `O_NOFOLLOW`, `O_DIRECTORY`, `O_CLOEXEC`, and `O_NONBLOCK`; it fails closed when unavailable. It walks each path component using directory descriptors without following symlinks, checks the final file with `lstat`-style metadata, opens with no-follow flags, and verifies the opened inode before reading. The bounded reader detects growth beyond 2 MiB without loading the remainder.

The adapter summarizes schema validity only. It does not verify package integrity, Sigstore provenance, the report's origin, or authorization to act on the data. It performs no remediation and must not be treated as an approval to stop or modify processes.

## Tests and limitations

`tests/test_agentdust_readonly_adapter.py` uses synthetic JSON and temporary files only. It covers valid input, malformed JSON, version and count errors, size and findings limits, symlinks, a FIFO, output redaction, and guards against subprocess and network APIs. The tests do not run AgentDust, access a real process inventory, make network requests, or validate Sigstore provenance.

## Conditions for future Devobs integration

Before integration, keep this adapter behind an explicit read-only API boundary; preserve tenant authorization and data minimization; never log or persist raw reports or findings; verify the report's producer and artifact provenance separately; cap request and response sizes; and add integration tests for concurrent file replacement and multi-tenant isolation. Any state-changing action must remain a separate, explicitly authorized workflow with its own review and safeguards.
