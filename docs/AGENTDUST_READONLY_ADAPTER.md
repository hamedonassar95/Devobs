# AgentDust Read-Only Adapter

## Purpose and trust boundary

`scripts/agentdust_readonly_adapter.py` accepts one explicitly supplied local path to an AgentDust `doctor --json` report. The report is untrusted input. The adapter validates its bounded JSON shape and emits aggregate counts only. It does not establish that the report came from AgentDust, that the binary was authentic, or that the report describes the current host. The module uses Python 3.10 or newer.

The caller is responsible for choosing the report file and protecting its directory. The adapter rejects symlinks in every path component, opens only a regular file, and caps bytes read at 2 MiB plus one detection byte. It uses standard-library file operations and JSON parsing only.

Before `json.loads` builds Python objects, a bounded lexical preflight rejects documents deeper than 64 nested arrays/objects or containing more than 100,000 JSON nodes. A node includes each object/array start, string token (including object keys), or primitive token. This limits nesting and object-count amplification before tree allocation; the 2 MiB byte cap still applies.

## Threat model

The adapter is designed to limit damage from malformed or hostile local report files, including oversized input, duplicate JSON keys, invalid encoding, unexpected schema, symlink substitution, special files such as FIFOs, and sensitive strings embedded in findings. It does not inspect finding contents. Error output consists only of fixed adapter error codes.

The adapter does not run AgentDust, a shell, subprocesses, or network requests. It does not modify the report. It parses the JSON document but does not inspect, transform, or emit finding entries. The underlying OS, Python runtime, filesystem, and caller-selected path remain trusted. Hard links cannot be distinguished from ordinary regular files by this interface; callers should place reports in a directory they control.

## Accepted input schema

The input must be UTF-8 JSON with a top-level object containing:

* `version`: integer `1` (booleans are not accepted as integers).
* `counts`: an object with exactly `managed`, `owned-live`, `owned-ended`, `likely-owned`, `suspect`, and `unknown`; each value must be a nonnegative integer no greater than 10,000,000.
* `findings`: an array with at most 10,000 elements. Elements are deliberately not read into the output.

The six count values therefore have a maximum aggregate of 60,000,000, which is checked before output. The 10,000,000 per-count ceiling is a generous single-host safety limit, not a claim derived from AgentDust's producer implementation; confirm compatibility with a trusted producer schema before integration. Every JSON integer token is limited to 20 decimal digits before conversion to a Python integer, including integers inside findings.

The entire file must be no larger than 2 MiB. Duplicate object keys and non-standard JSON numeric constants are rejected. The depth and node preflight scans the decoded, size-bounded text before `json.loads`; the standard-library parser is still used only after these limits pass.

## Output

For a valid input, the CLI writes one JSON object to stdout containing only `status_code`, `processes_detected` (the sum of the six counts), and `findings_count`. `status_code` is the fixed value `REPORT_VALID`. It does not include individual counts, PIDs, command lines, paths, or finding contents.

For rejected input in the regular one-path CLI mode, stdout remains empty, the process exits with status 2, and stderr contains only `adapter_error=<fixed-code>`. The provided path and exception text are never printed. Workflow-summary mode instead emits its fixed failure fields and exits nonzero.

Example invocation:

```sh
python3 scripts/agentdust_readonly_adapter.py /controlled/path/doctor.json
```

The sandbox Workflow uses the same validator through `--workflow-summary <report-path> <doctor-exit-code>`. That mode emits only fixed CI fields (`doctor_exit_code`, aggregate counts, success, and a fixed failure code); it returns nonzero for an invalid report or nonzero Doctor exit status. Both modes call `summarize_report`, so schema and resource rules are not duplicated in the Workflow.

## Security limits

The reader requires POSIX `dir_fd` support plus `O_NOFOLLOW`, `O_DIRECTORY`, `O_CLOEXEC`, and `O_NONBLOCK`; it fails closed when unavailable. It walks each path component using directory descriptors without following symlinks, checks the final file with `lstat`-style metadata, opens with no-follow flags, and verifies the opened inode before reading. The bounded reader detects growth beyond 2 MiB without loading the remainder.

The adapter summarizes the validity of this bounded report shape only. It does not prove that the report is authentic or came from AgentDust, verify package integrity or Sigstore provenance, establish that the report describes the current host, or authorize action on the data. Structural validation is separate from authenticity verification. It performs no remediation and must not be treated as approval to stop or modify processes.

These caps reduce parser resource exposure but are not a process memory or CPU sandbox. A valid input can still consume resources up to the configured byte, node, and depth limits, and the caller must keep the file and its directory under appropriate control.

## Tests and limitations

`tests/test_agentdust_readonly_adapter.py` uses synthetic JSON and temporary files only. It covers valid input, malformed JSON, version and count errors, exact and exceeded byte limits, depth and node limits (including rejection before `json.loads`), bounded integers, findings limits, symlinks, a FIFO, output redaction, and guards against subprocess and network APIs. The tests do not run AgentDust, access a real process inventory, make network requests, or validate Sigstore provenance. The count ceiling still needs compatibility confirmation against a trusted AgentDust report schema.

## Conditions for future Devobs integration

Before integration, keep this adapter behind an explicit read-only API boundary; preserve tenant authorization and data minimization; never log or persist raw reports or findings; verify the report's producer and artifact provenance separately; cap request and response sizes; and add integration tests for concurrent file replacement and multi-tenant isolation. Any state-changing action must remain a separate, explicitly authorized workflow with its own review and safeguards.
