# Cross-platform test reliability runbook

**Scope:** local Windows and Linux validation of the Devobs Python/Node test harness. This runbook describes test infrastructure only; it does not authorize a merge, deployment, provider change, secret access, paid service or release-gate change.

## 1. Prerequisites

Use a clean checkout of the reviewed branch and a disposable virtual environment. On Windows, install both hash-locked manifests so the same dependencies used by CI are present:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check --require-hashes -r requirements-api.lock -r requirements-dev.lock
```

Record the Python version and the exact checked-out SHA before running checks. Do not use the system `python3` on Windows: Git Bash may resolve it to the WindowsApps stub, which exits `49`.

## 2. Baseline and full verification

Run these from the repository root. Capture stdout and stderr, plus `$LASTEXITCODE`, and keep logs outside the working tree.

```powershell
$py = '.\.venv\Scripts\python.exe'

& $py -B -m unittest discover -s tests -v
"FULL_SUITE_EXIT=$LASTEXITCODE"

& $py -B -m unittest discover -s tests/graphify -v
"GRAPHIFY_EXIT=$LASTEXITCODE"

& $py -m compileall -q scripts tests tools
"COMPILEALL_EXIT=$LASTEXITCODE"

& $py -m bandit -r scripts tools -x scripts/check_site.py
"BANDIT_EXIT=$LASTEXITCODE"

& $py -B scripts/check_action_pins.py
"ACTION_PINS_EXIT=$LASTEXITCODE"

git diff --check
"DIFF_CHECK_EXIT=$LASTEXITCODE"
```

Expected final local result for this branch: full suite `Ran 1487 tests`, `OK (skipped=91)`, exit `0`; Graphify `Ran 51 tests`, `OK`, exit `0`; Bandit `No issues identified`, exit `0`; action pins and `git diff --check` exit `0`.

### GitHub Actions YAML parse (local substitute, not actionlint)

```powershell
$check = @'
from pathlib import Path
import yaml
paths = sorted(Path('.github/workflows').glob('*.yml'))
if not paths:
    raise SystemExit('no workflow YAML files found')
for path in paths:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'{path}: top level is not a mapping')
print(f'YAML_PARSE_OK files={len(paths)}')
'@
$check | & $py -B -
"WORKFLOW_YAML_EXIT=$LASTEXITCODE"
```

A YAML parse does not replace the pinned `actionlint`/`ShellCheck` job in GitHub Actions. Report that job as UNVERIFIED until CI runs.

### Node smoke checks

Run the exact `node --check` target list from `ci.yml`, failing closed if any target is missing or any command fails:

```powershell
$paths = @(Select-String -Path '.github/workflows/ci.yml' -Pattern '^\s+node --check (.+)$' | ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() })
if ($paths.Count -eq 0) { throw 'no node --check commands found' }
foreach ($p in $paths) {
  if (-not (Test-Path -LiteralPath $p)) { throw "missing node smoke target: $p" }
  node --check $p
  if ($LASTEXITCODE -ne 0) { throw "node --check failed: $p" }
}
"NODE_SMOKE_OK files=$($paths.Count)"
```

### Node test batches

Run every `node --test` command from `ci.yml`, failing closed if any batch fails:

```powershell
$batches = @(Select-String -Path '.github/workflows/ci.yml' -Pattern '^\s+node --test (.+)$' | ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() -split '\s+' })
if ($batches.Count -eq 0) { throw 'no node --test batches found' }
$failed = 0
foreach ($batch in $batches) {
  node --test @batch
  if ($LASTEXITCODE -ne 0) { $failed += 1 }
}
"NODE_TEST_BATCHES=$($batches.Count)"
"NODE_TEST_FAILED_BATCHES=$failed"
if ($failed -ne 0) { exit 1 }
```

Expected final local result for this branch: `NODE_SMOKE_OK files=88`; `NODE_TEST_BATCHES=23`, `NODE_TEST_FAILED_BATCHES=0`, with aggregate TAP output `284 tests`, `239 pass`, `45 skipped`, `0 fail`. Skips are limited to POSIX-only secure-storage, journal and symlink paths; the Windows fail-closed codes are asserted explicitly.

## 3. Capability decision table

| Symptom | Probe / helper | Correct action |
|---|---|---|
| Bash missing on `PATH` | `find_bash()` | Skip only shell-contract tests that require Bash; on Windows the helper also checks Program Files for Git Bash. |
| Native path passed into Git Bash | `to_bash_path()` | Convert `C:\...` to `/c/...`; do not rewrite production scripts. |
| `python3` exits `49` or `jq` unavailable | `write_python3_shim()`, test-only `fake_jq` | Bind the workflow command to the shim and keep executing the real production script. Unknown jq filters must fail closed. |
| `secure_open_unavailable` | `has_secure_open_capability()` | Skip only POSIX-content assertions; keep the explicit fail-closed adapter assertions active. |
| Symlink creation returns `WinError 1314` | `require_symlink_creation()` | Skip only the symlink fixture. Split mixed tests so all other assertions remain active. |
| Node `O_NOFOLLOW` or secure journal unavailable | `hasNoFollowCapability()`, `hasJournalCapability()`, `requireNoFollowCapability()`, `requireJournalCapability()` | Skip only POSIX-content and journal-write paths. Keep explicit assertions that production returns `platform_no_follow_unsupported` or `unsupported_journal_platform`. |
| Node symlink creation returns `EPERM` | `canCreateSymlink()`, `requireSymlinkCreation()` | Skip only symlink fixture setup; keep adjacent conversion and validation assertions active. |
| `os.mkfifo` absent | `require_fifo_creation()` | Skip only FIFO fixture setup. |
| `chmod(0o755)` does not expose POSIX mode bits | `require_posix_mode_bits()` | Skip only executable-mode-bit assertions. |
| SQLite/temp cleanup returns `WinError 32` | direct inspection | Close connections with `contextlib.closing`; never ignore cleanup errors. |

When adding a capability guard, the skip reason must name the missing capability. Never guard an entire test class merely because one fixture cannot be constructed.

## 4. Byte-pinned fixtures and dataset hashes

Four fixtures are pinned to LF bytes through `.gitattributes`:

- `tests/fixtures/ai-evals/decisions-triage.jsonl`
- `tests/fixtures/intelligence_eval_cases.json`
- `tests/fixtures/intelligence_eval_cases_v2.json`
- `deploy/keycloak-hosted/render.yaml`

If a digest check fails:

1. Re-checkout or normalize the fixture according to `.gitattributes`; do not edit the expected hash first.
2. Compare the raw checkout bytes with the committed Git blob. The pinned hashes in this branch were matched to the LF blobs.
3. Run the fixture guard suite before changing any test logic:

```powershell
& $py -B -m unittest tests.test_cross_platform_fixtures tests.test_ai_eval_fixture_guard tests.test_intelligence_evaluation tests.test_p01_keycloak_external_plan -v
& $py -B scripts/validate_ai_eval_fixtures.py
```

A mismatch with unchanged bytes is a failure. Expected hashes may be changed only after independent verification that the data content itself changed in an approved commit.

## 5. Security review checklist

Before requesting review, confirm:

- No production `fail closed` branch, security check, CI job, action pin or permission was disabled.
- Capability skips are narrow and report the missing capability.
- `secure_open_unavailable`, `platform_no_follow_unsupported` and `unsupported_journal_platform` have active negative tests on hosts without POSIX flags.
- Fake tools accept only the exact contracts used by production scripts and fail closed on unknown input.
- No secret, token, credential, cloud setting, provider resource or paid service was touched.
- The full suite, Graphify suite, compileall, Bandit, action pins, YAML parse, Node smoke checks, all Node test batches and `git diff --check` were run with fresh exit codes.
- Hosted CI results are reported separately from local results.

## 6. Rollback

The ten code commits are ordered in [the Windows failure analysis](../audits/WINDOWS_TEST_FAILURE_ANALYSIS.md#commit-sequence). If the branch has not been pushed, a local-only reset to the verified base is sufficient:

```powershell
git switch feature/windows-test-reliability
git reset --hard 799efe673a72aeadf3016667eaed853d2553aaa8
```

After the branch has been published, do **not** reset or force-push. Revert on a new review branch, newest first, including every documentation commit on the branch:

```powershell
git switch -c revert/windows-test-reliability
git revert --no-edit 69440f3900523fd26b70cfb0054072213b0603b8 e48d852c5d8119f6667616f4a466a634fd844551 2a4de5132fa3c6f8d7cca4fc4c2c947052e677a4 c2e5c8ccac523c04c30cad5cd19cc3c4add10cff a1b3990574da1ba0ddfd3e45511308306db3e374 bca89b0649316214e623d1bb8287cc10bb22ef1e 58bafa5cd5c201713228470c84e7e62d5c9b4f98 6e3d2fd4d9e1a418c6639add3a6927b916cd78d2 9157281c0c7a5dd58110640bca1eabae57185eec c3201f5c6a5fbf081f1ea49774b0bf6b2a5ee2e4 407ab18709b8a9300734684fd35d556a3c1f01ca dea68ebf4096d295360513d335cbc1bc785f8542
```

Then rerun section 2 and open a separate review for the revert. A revert is never an approval to merge, deploy or change a release gate.
