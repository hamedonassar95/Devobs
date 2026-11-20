# Windows test failure analysis — 2026-11-20

**Branch:** `feature/windows-test-reliability`  
**Verified base:** `799efe673a72aeadf3016667eaed853d2553aaa8` (`refactor(graphify): unify canonical execution and preserve legacy compatibility (#726)`)  
**Verified PR #726:** merged before this branch was created. The branch never modified `main`.  
**Scope:** local Windows test harness, fixtures and two production helpers whose platform assumptions caused false failures. No hosted service, identity, secret, deployment, CI job, security gate, dataset expectation or release decision was changed.

## Evidence summary

- **VERIFIED — baseline:** a fresh Windows run of `python -B -m unittest discover -s tests -v` produced `Ran 1212 tests in 343.964s`, `FAILED (failures=47, errors=123, skipped=44)`, exit `1`. Log headers were reduced to `HEADERS 170 UNIQUE 135 MODULES 22`; the 170 failure/error headers were reconciled into the categories below.
- **VERIFIED — intermediate:** after the first repair set, the same suite produced `Ran 1482 tests in 279.617s`, `FAILED (errors=17, skipped=78)`, exit `1`. The remaining 17 were 12 unprivileged symlink fixtures, four Windows-locked SQLite temp files and one POSIX mode-bit fixture.
- **VERIFIED — final local suite:** after all repairs, the hash-locked virtual-environment run produced `Ran 1487 tests`, `OK (skipped=91)`, exit `0`. The exact command and output are recorded in the final verification report.
- **UNVERIFIED — hosted Ubuntu CI:** not run locally. GitHub Actions must validate the exact pushed head before review or merge.
- **LIMITS:** counts describe the observed Windows host, not every Windows configuration. Skips are narrow capability skips; they do not relax production assertions.

## Root-cause classification

| Category | Baseline count | Observed symptom | Root cause | Disposition |
|---|---:|---|---|---|
| Bash discovery and executable resolution | 78 | `FileNotFoundError`, POSIX shell scripts not executed, `python3` exit `49` | Tests assumed a Bash binary on `PATH` and used native Windows paths inside Git Bash. Git Bash's `python3` resolves to the WindowsApps stub, which exits `49`; `jq` is absent. | Shared `find_bash()` discovers Git Bash under Program Files; `to_bash_path()` converts drive paths; test-only `python3`/CLI shims call the active interpreter. No production shell is used as a fake tool. |
| POSIX `secure_open` path | 31 | `secure_open_unavailable` where report-content behavior was expected | Windows lacks the required `O_NOFOLLOW`/`O_DIRECTORY`/`O_CLOEXEC`/`O_NONBLOCK` combination and directory-FD support. The production adapter correctly failed closed before reading content. | Narrow capability guards skip only POSIX-content assertions. New, ungated capability tests assert that `summarize_report()` raises `secure_open_unavailable` and the CLI emits `adapter_error=secure_open_unavailable` or the workflow fallback on this host. Production code was not changed. |
| Hard-coded `/usr/bin/git` | 17 | Gitleaks coverage tests could not execute Git on Windows | `scripts/verify_gitleaks_coverage.py` used an absolute Linux path. | Resolve Git at import with `shutil.which('git')`, retaining the legacy path as a Windows fallback, and fail closed with a clear error when no Git is available. Paths still come from discovery, never from the untrusted CI event. |
| Symlink fixture setup | 13 | `OSError: [WinError 1314] A required privilege is not held by the client` | Unprivileged Windows cannot create the symlink fixture used to test rejection. | Shared `require_symlink_creation()` skips only symlink setup. Mixed tests were split so duplicate-key, missing-file, input-limit and other non-symlink assertions still run. |
| Missing local Python dependencies | 22 | `ModuleNotFoundError` for `cryptography`, `jwt`, `psycopg` or OpenTelemetry modules | The system interpreter lacked declared dependencies. The hash-locked Windows install lacked Windows-only transitive packages. | Added hash-pinned `tzdata` and `colorama` only under Windows markers. Verified a hash-checked install in a disposable virtual environment. No package version was upgraded and no expected hash was changed. |
| Windows path canonicalization | 4 | Valid staged-site children rejected as outside `GITHUB_WORKSPACE` | `Path.resolve()` expands 8.3 short names on Windows while `os.path.abspath()` does not; the two forms were mixed. | `scripts/stage_site.py` now keeps a lexical workspace form for the containment check and continues to reject symlinks at every component. |
| CRLF/LF fixture bytes | 3 (including two dataset-digest cases) | `dataset_digest_mismatch` and other raw-byte hash failures | Windows checkout converted LF fixtures to CRLF; pinned hashes were computed over LF bytes. | `.gitattributes` pins the four byte-sensitive fixtures to `eol=lf`. Pinned hashes were independently matched to the LF Git blobs and **were not changed**. |
| Windows-exclusive file handle | 1 | `PermissionError: [WinError 32]` during temp-directory cleanup | SQLite fixtures kept connections open while `TemporaryDirectory.cleanup()` ran. | Tests now close SQLite connections with `contextlib.closing`; assertions and read-only semantics are unchanged. |
| Missing FIFO support | 1 | `os.mkfifo` absent | Windows has no POSIX FIFO API. | Narrow `require_fifo_creation()` guard; no FIFO-specific production behavior was weakened. |

## Dataset integrity

**VERIFIED:** the two `dataset_digest_mismatch` failures were checkout artifacts, not dataset drift. The pinned SHA-256 values match the LF Git blobs; no expected hash was edited. The runbook makes raw-byte verification mandatory before any hash change and treats a mismatch with unchanged bytes as a failure, never as a reason to refresh a pin.

## Security invariants

- Fail-closed assertions remain active. Where a capability is absent, an explicit alternate assertion proves the production code still fails closed (`secure_open_unavailable`) instead of silently skipping the security behavior.
- Skips identify a missing host capability in the skip reason; they never disable a security check, CI job, action pin, Gitleaks rule, tenant-isolation check or release gate.
- The fake Git fixture is invoked through an explicit `FAKE_GIT` variable because Git Bash prepends its own tools to `PATH`; directory precedence is not trusted.
- The offline `fake_jq` fixture accepts only the exact filters used by `scripts/check_vercel_site.sh`; unknown filters return an error. Health-check tests still execute the real production shell script.
- Vercel, Trivy, Pages and Gitleaks tests use fail-closed offline fixtures/shims; production scripts and CI policy were not weakened.
- No secret, token, credential, IAM rule, provider setting, paid service, deployment or merge was created or changed.

## Residual work and open gates

- Hosted Ubuntu CI and exact-head PR checks remain **UNVERIFIED** until the branch is pushed and CI completes.
- Symlink, FIFO and POSIX mode-bit behaviors remain **UNVERIFIED on this Windows host** and are exercised on Linux CI. Their absence is reported as a skip, not a pass of the POSIX behavior.
- Actionlint, Docker/Trivy runtime scans, Terraform and kubectl were unavailable locally; repository-owned offline policy tests and action-pin checks were used instead and are reported separately.
- P01 remains **BLOCKED / NO-GO**, AI-9 remains **BLOCKED**, and Codex runtime acceptance remains **OPEN**. This test-reliability work does not change any of those gates.

## Commit sequence

The code changes are nine small commits, in order:

1. `dea68ebf4096d295360513d335cbc1bc785f8542` — Windows-only transitive dependency pins
2. `407ab18709b8a9300734684fd35d556a3c1f01ca` — byte-pinned fixture line endings
3. `c3201f5c6a5fbf081f1ea49774b0bf6b2a5ee2e4` — Git discovery and synthetic scanner portability
4. `9157281c0c7a5dd58110640bca1eabae57185eec` — staged-site path normalization
5. `6e3d2fd4d9e1a418c6639add3a6927b916cd78d2` — Windows-exclusive summary file handle
6. `58bafa5cd5c201713228470c84e7e62d5c9b4f98` — shared host capability discovery
7. `bca89b0649316214e623d1bb8287cc10bb22ef1e` — Bash-backed contract portability
8. `a1b3990574da1ba0ddfd3e45511308306db3e374` — remaining offline fail-closed contracts
9. `c2e5c8ccac523c04c30cad5cd19cc3c4add10cff` — SQLite fixture close and narrow POSIX-only guards

See [the cross-platform testing runbook](../runbooks/CROSS_PLATFORM_TESTING.md) for reproduction, interpretation and rollback steps.
