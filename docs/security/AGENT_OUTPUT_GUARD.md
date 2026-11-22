# Offline AI-agent output guard

**VERIFIED source baseline:** `10f8dd9b1e884e16cea3ffd847cf20405794cb8b`,
reviewed 2026-11-22. This is a manually invoked, read-only local policy gate.
It does not commit, approve, upload, execute, rewrite, delete or quarantine files.
No CI hook, GitHub setting, deployment or paid service is enabled.

## Existing-tool assessment and reuse

**VERIFIED:** no equivalent end-to-end artifact-path CLI was found in main or
the open-PR listing at inspection. The ledger summary reported 304 recorded
milestones, latest recorded PR 717 and three unresolved gates. This change does
not update that ledger or alter P01 BLOCKED, AI-9 BLOCKED or Codex runtime OPEN.

| Existing capability | Reuse / distinct boundary |
| --- | --- |
| [AgentDust reader](../../scripts/agentdust_readonly_adapter.py) | Reuses secure descriptor-based regular-file open, bounded read/change detection, and JSON complexity/hooks. Its existing public parser validates an AgentDust-specific schema, not arbitrary output artifacts |
| [CI intelligence redaction](../../scripts/ci_failure_intelligence.py) | Reuses `SECRET_PATTERNS`; no second provider-token rule set or scanner process |
| [Repository intelligence exclusions](../../tools/graphify/common.py) | Reuses `is_excluded` and its exclusion tables to reject sensitive/build paths and workspace ancestors before opening artifacts |
| [Gitleaks coverage](../../scripts/verify_gitleaks_coverage.py) | Existing Git-history scanner remains authoritative for that scope; this guard does not run, replace or claim its coverage |
| [Integration snapshot security](../../devobs/integration_control/security.py) | Related bounded JSON/redaction controls, but not a generic multi-file output guard |
| [Recovery patch guard](../../scripts/recovery_patch_guard.py) | Recovery branch/path policy; does not inspect arbitrary output-file contents |

The addition is the artifact boundary: explicit workspace-relative paths, type
and text checks, general strict JSON, canonical pattern checks and quiet JSON
results. It imports trusted repository helpers only, never input artifacts.
Private AgentDust helper reuse is intentional within this repository; helper
changes require regression testing. Import or reader failures cannot yield PASS.

## Invocation and results

From the trusted Devobs checkout, choose an existing artifact-only workspace:

```sh
python tools/agent_output_guard.py --workspace /path/to/review-output report.json notes.md
python tools/agent_output_guard.py --help
```

`--workspace` is mandatory. Supply 1–32 explicit normalized **relative** file
paths; directories are never recursively scanned. Each occurrence is checked in
argument order, including repeated paths. Absolute paths, URLs, drive/stream
syntax, backslashes, empty components, `.`/`..` and control characters are denied.
There is no environment-based discovery or automatic search for credential files.
Use synthetic or otherwise expressly authorized output artifacts; do not select
actual credential stores, private keys, production logs or customer data.

| Status | Exit | Meaning |
| --- | --- | --- |
| `PASS` | 0 | Every selected artifact satisfies this limited local policy |
| `BLOCKED` | 1 | At least one artifact violates policy or cannot be read/validated |
| `FAIL` | 2 | Invalid invocation/workspace, unsupported secure reader or unexpected validator failure |

`FAIL` takes precedence over `BLOCKED`, which takes precedence over `PASS`.
Default stdout is one compact, sorted JSON object with schema/policy version,
status, `offline`, `content_redacted`, artifact indices and fixed reason codes.
No timestamp, absolute path, filename, excerpt, content digest, matched value or
exception message is emitted. Callers map indices to their own argument list.
Even CLI syntax errors suppress argparse's raw-argument echo. `--help` is static
human-readable help, exits 0 and does not inspect artifacts.

Example for one rejected artifact (no supplied content is retained):

```json
{"artifacts":[{"index":1,"reason_codes":["CREDENTIAL_PATTERN"],"status":"BLOCKED"}],"content_redacted":true,"offline":true,"policy":"agent-output-guard/1","reason_codes":[],"schema_version":1,"status":"BLOCKED"}
```

## Verified policy boundaries

- Types: `.json`, `.md`, `.txt`, `.py`, `.yaml`, `.yml`, `.toml`, `.diff`, `.patch`.
  Extensions are case-insensitive. Only JSON receives syntax parsing; other
  types are checked as text and are never imported, evaluated or executed.
- At most **2 MiB per file** (AgentDust's existing cap), 32 paths per batch,
  4,096 characters per path. Reads are bounded even if a file grows; ordinary
  size/inode/metadata changes during reading are rejected.
- Strict UTF-8; no BOM, binary control bytes, Unicode control/format characters
  or lone surrogates. Tab/CR/LF are allowed in content, never in paths. Decoded
  JSON string keys and values receive the same control checks.
- JSON rejects duplicate keys, nonstandard constants, non-finite parsed floats,
  integers beyond 20 digits, nesting beyond 64 and more than 100,000 nodes,
  including keys. Raw and decoded/canonical JSON are checked for credential
  patterns, so JSON escaping alone cannot hide a matching key or value.
- All symlinks are denied, including internal links, parent components and a
  linked workspace. Multiply linked files, directories, FIFOs and other special
  files are denied. Known exclusions include `.env*`, credential/key stores,
  Git metadata and build/cache paths; this is conservative, not exhaustive.
  Choosing a sensitive directory as a deeper workspace cannot bypass these
  exclusions. A `.worktrees` ancestor is permitted for agent checkouts; selecting
  `.worktrees` inside an artifact-relative path remains excluded.
- The existing secure reader requires POSIX descriptor-relative/no-follow APIs.
  On Windows or any unsupported platform, return `FAIL`; there is no weaker
  path-resolution fallback. A symlinked ancestor also prevents validation.
- Canonical credential patterns are finite heuristics. A conservative private-key
  marker precheck also rejects truncated headers before invoking the inherited
  multiline expression, avoiding its repeated-header/missing-end scan case. The
  fixed marker uses the same Unicode case-insensitive semantics as that rule.
- Local helper imports disable Python bytecode generation. No artifact content
  or filesystem state is intentionally modified; ordinary read access may still
  affect OS-managed access-time metadata.

These controls use Python's documented [JSON hooks](https://docs.python.org/3/library/json.html)
and the existing reader's [descriptor-relative OS APIs](https://docs.python.org/3/library/os.html).

## Limitations and false positives

**ASSUMED operational boundary:** the checkout and selected artifact workspace
are trusted, local and quiescent while validation/review occurs. A result is a
point-in-time observation, not an immutable binding to a later Git commit.
Concurrent hostile renames, mount changes or privileged filesystem interference
are outside this guarantee. Keep outputs stable and inspect the eventual diff.

PASS does not prove the absence of secrets, malicious code, prompt injection,
vulnerabilities, unsafe dependencies or unauthorized actions. Obfuscated/novel
credential formats can evade inherited patterns. Extension/UTF-8 checks are not
complete MIME detection; non-JSON syntax and business schemas are not validated.
Do not transmit the files to a model or service because they passed this guard.

Documentation, examples, already-redacted labels, test fixtures or scanner rule
definitions may match credential patterns. Bidi/format characters, emoji joiners,
large legitimate numbers/files, internal links and build-output directories may
also be rejected. Review a rejection locally without publishing its contents;
there is no automatic allowlist, rewrite or override. Retain normal human review
and the existing Gitleaks/security checks before committing or submitting work.
Caller/shell logging is outside this tool's quiet-output boundary.

## Verification with synthetic fixtures only

```sh
python -m unittest discover -s tests -p "test_agent_output_guard.py" -v
python -m compileall -q tools
python tools/agent_output_guard.py --help
git diff --check
```

The [tests](../../tests/test_agent_output_guard.py) exercise actual
[guard](../../tools/agent_output_guard.py) behavior, including CLI subprocesses,
clean/malformed/oversized inputs, encoded credentials, redacted errors,
traversal, links, unreadable/special/binary files and unexpected failures.
They create only disposable synthetic files and never read real credentials.
No artifact is executed and no network connection is needed.

**VERIFIED local results (Linux, 2026-11-22):**

| Check | Observed result |
| --- | --- |
| Required focused unittest command | 30 tests, OK |
| Required compileall / help / diff commands | Exit 0 |
| Existing AgentDust + CI-redaction tests | 51 tests, OK |
| Full unittest discovery in the existing local Python environment | 1702 tests, OK; 37 skipped |
| Existing Bandit, limited to the new guard | Exit 0, no findings |
| Markdown targets/format and three-file scope | PASS |
| Native Windows execution | NOT RUN; secure reader deliberately fails closed there |

Skipped tests are not acceptance evidence. Two independent read-only reviews
found no remaining must-fix after workspace-root and Unicode-marker regressions
were reproduced and fixed. These results are not hosted CI or a secret-free proof.

Report exact commands, exit status and observed results in the PR. Mark missing
platform/tool coverage NOT RUN; local checks do not establish hosted CI or
production acceptance. Rollback is a reviewed three-file code/docs revert.
