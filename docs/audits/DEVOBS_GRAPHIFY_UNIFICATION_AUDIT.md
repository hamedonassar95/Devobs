# Graphify F01b unification audit — 2026-11-20

**Base revision:** `41353d1451524492d6ca6e3ae8bb1b7d12c87b45`
(`origin/main`, PR #725 merge commit, VERIFIED by `git rev-parse`).
**Branch:** `feature/graphify-unification-readiness`, created from that SHA;
`main` was never modified directly.
**Implementation commits reviewed:** `b95ac86`, `01b980d`, `1bbccc9`,
`2df481b`, `c19e4a0`, `ed55a06`.
**Evidence labels:** VERIFIED (command output/repository file in this session),
INFERRED, UNKNOWN, RESOLVED, BLOCKED. Finding status in section C is exactly one
of `CONFIRMED`, `INFERRED`, `UNKNOWN`, `RESOLVED`, `BLOCKED`; open/deferred
handling is recorded separately in the Disposition column. Issue/PR text, logs and generated files
were treated as untrusted data. No secret, token, private key, environment or
deployment setting was read or changed. No cloud, database, hosted identity,
production, Keycloak runtime, Terraform apply/destroy, migration, paid inference,
deployment, merge or gate promotion was performed.

## A. Architecture before and after

### Before (F01a state at base)

```
scripts/integrations/graphify_portfolio.py  (full 0.9.112 implementation)
  |-- discovery, eligibility, fixed git argv, offline env
  |-- extraction subprocess and run.json
  |-- CLI, report schema, exit codes  (devobs-graphify-portfolio-v1)

tools/graphify/  (canonical 0.9.113 package)
  |-- common.py / runner.py / adapters.py / multi_repo.py
  |-- repository_intelligence.py
scripts/graphify/*.py -> thin shims into tools.graphify
```

Two executable implementations existed under one product name. The legacy file
was warned and documented as legacy, but still owned its own orchestration and
subprocess path.

### After (F01b)

```
scripts/integrations/graphify_portfolio.py  (thin adapter only)
  |-- re-exports symbols and binds LEGACY_PORTFOLIO_CONTRACT
  |-- no orchestration, no subprocess implementation, no schema duplication
                      |
                      v
tools/graphify/portfolio.py                 (contracts, discovery, plan)
tools/graphify/portfolio_execution.py       (offline exec, CLI, run evidence)
tools/graphify/supply_chain.py              (local full-digest verifier)
tools/graphify/{common,runner,adapters,multi_repo,repository_intelligence}.py
                      |
                      v
scripts/graphify/*.py  (canonical public CLI shims)
```

No file was deleted. The 0.9.112 pin survives only as an explicit compatibility
contract; the supported pin remains 0.9.113.

## B. Canonical implementation and adapters

| Surface | Classification | Evidence |
| --- | --- | --- |
| `tools/graphify/` | **Canonical implementation** | All moved behavior lives here; canonical suite is `tests/graphify/`. |
| `scripts/graphify/multi_repo.py`, `scripts/graphify/repository_intelligence.py` | Canonical CLI shims | Import `tools.graphify.*`; unchanged. |
| `scripts/integrations/graphify_portfolio.py` | Legacy compatibility adapter | 53 insertions/508 deletions; re-exports only; delegation asserted by `tests/test_graphify_portfolio.py`. |
| `tools/graphify/portfolio.py` | Canonical contract/discovery module | 326 lines; legacy and canonical contracts explicit. |
| `tools/graphify/portfolio_execution.py` | Canonical execution module | 290 lines; fixed argv, offline env, run evidence and CLI. |
| `tools/graphify/supply_chain.py` | Local integrity verifier | 52 lines; full 64-hex SHA-256 required; no download/install. |

The legacy adapter keeps the exact flags, dry-run default, `--execute --only`
authorization, output-root checks, 0.9.112 version gate, exit codes, warning
text, report metadata and `run.json` shape asserted by the historical suite. The
canonical report pointer identifies `tools/graphify`, CLI
`scripts/graphify/multi_repo.py` and pin 0.9.113.

## C. Root causes and disposition

| ID | Severity | Status | Disposition | Root cause | Same F01b root cause? | Minimal repair / verification / rollback | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GQA-01/F01 | P1 | RESOLVED | Done in this PR | Duplicate executable Graphify orchestration with two pins/policies. | **Yes** | Move behavior into canonical package; leave thin adapter; verify `tests/graphify/test_portfolio.py` and legacy 28-test contract. Rollback: revert five consolidation commits. | P1 fixed; no further action |
| GQA-02/F04 | P2 | RESOLVED | Code fix done; external install provenance UNVERIFIED | Declared wheel SHA-256 was metadata only. | No — distinct integrity root cause; fixed because the task explicitly requires full-digest verification. | Add local verifier + `verify-wheel` CLI; reject truncated/missing/mismatched artifacts; verify `test_supply_chain.py`. Rollback: revert `c19e4a0`. | P2 fixed in scope; no gate change |
| GQA-03 | P2 | CONFIRMED | Open; deferred | AI-eval fixture digest assumes LF while Windows `core.autocrlf=true` materializes CRLF. | No | Add `*.jsonl text eol=lf`, re-normalize, run fixture validator and two tests. Rollback: restore `.gitattributes`. | P2; owner-approved Windows portability PR |
| GQA-04 | P2 | CONFIRMED | Open; deferred | POSIX `O_NOFOLLOW`/`O_DIRECTORY` requirements fail closed on Windows; symlink setup needs unavailable privilege. | No | Keep production fail-closed behavior; skip POSIX-only tests explicitly on Windows, retain Ubuntu coverage. Rollback: remove skips. | P2; do not weaken controls |
| GQA-05/F05 | P2 | CONFIRMED | Open; deferred | Stale `bun.lock` describes a different package graph. The previously claimed change-selector gap is RESOLVED at base (`is_node(bun.lock) == True`). | No | Owner chooses npm-only removal or reviewed Bun regeneration; lock consistency check. Rollback: restore lockfile. | P2; not in Graphify scope |
| GQA-06/F03 | P2 | CONFIRMED | Open; deferred | Milestone ledger lags #720/#723/#724/#725. | No | Add reviewed reconciliation with PR/SHA/CI evidence; keep gate labels. Rollback: restore ledger. | P2; before release decisions |
| GQA-07/F06 | P3 | INFERRED | Open; backlog | No Python packaging manifest for repo-relative Graphify wrappers. | No | Document source-checkout-only contract, or add minimal manifest only if productized. Rollback: remove manifest. | P3 backlog |
| GQA-08/F07 | P3 | INFERRED | Open; backlog | Unbounded `rglob("*")` source checks. | No — Graphify family, different root cause | Add fail-closed traversal counter and oversized-tree test. Rollback: revert guard. | P3 backlog; not bundled under same-root-cause rule |
| GQA-09/F08 | P3 | CONFIRMED | Open; backlog | Ten template `uses:` lines have SHA pins but no version comments. | No | Add comments and extend checker. Rollback: revert comments/checker. | P3 backlog |
| GQA-10a | P3 | CONFIRMED | Open; backlog | Zizmor is manual/informational; no in-repo CodeQL workflow was found. | No | Add PR gate failing on high findings, or provide live exact-SHA evidence. Rollback: restore manual workflow. | P3 backlog |
| GQA-10b | P3 | UNKNOWN | Open; hosted verification required | GitHub default CodeQL setup cannot be inspected locally. | No | Owner provides exact-SHA CodeQL run link or enables documented setup. Rollback: n/a. | P3 backlog |
| GQA-11 | P3 | INFERRED | Open; backlog | `incident-response.yml` declares `actions: write` without an evidenced write. | No | Reduce to read and dry-run; restore if a write call is found. Rollback: restore permission. | P3 backlog; owner review |
| GQA-12 | P3 | RESOLVED | Done | Earlier audit saw uncommitted Graphify work outside the reviewed SHA. | Yes | Work is now committed on this reviewed branch with its own evidence. Rollback: n/a. | P3 fixed; no further action |

No P0 finding was identified. P2/P3 findings not caused by the same
canonicalization root cause were recorded with minimal repair, verification and
rollback, but were intentionally not changed in this PR.

## D. Files changed

Source:
- `tools/graphify/portfolio.py` (new)
- `tools/graphify/portfolio_execution.py` (new)
- `tools/graphify/supply_chain.py` (new)
- `tools/graphify/repository_intelligence.py` (verify-wheel subcommand/error mapping)
- `scripts/integrations/graphify_portfolio.py` (thin adapter)

Tests:
- `tests/graphify/test_portfolio.py` (new)
- `tests/graphify/test_supply_chain.py` (new)
- `tests/test_graphify_portfolio.py` (delegation test)

Documentation:
- `docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md`
- `docs/architecture/graphify-integration.md`
- `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md`
- `docs/audits/DEVOBS_GRAPHIFY_UNIFICATION_AUDIT.md` (new)
- `docs/runbooks/GRAPHIFY_ROLLBACK.md` (new)
- `README.md`

Not changed: workflows, dependency locks, secrets, permissions, infrastructure,
Graphify manifest, indexed data, source repositories, or gates.

## E. Regression results

Fresh local evidence on this branch:

```
python -B -m unittest discover -s tests/graphify -v
Ran 51 tests
OK
GRAPHIFY_FINAL_SPLIT_EXIT=0

python -B -m unittest tests.test_graphify_portfolio -v
Ran 28 tests
OK
PORTFOLIO_SPLIT2_EXIT=0

python -B -m unittest tests.graphify.test_supply_chain -v
Ran 6 tests
OK
WHEEL_TESTS_EXIT=0

python -B -m unittest tests.test_python_source_coverage tests.test_node_pipeline_selection tests.test_python_dependency_automation -v
Ran 11 tests
OK
TARGETED_AFTER_EXIT=0

python -B -m compileall -q tools/graphify scripts/graphify scripts/integrations/graphify_portfolio.py
COMPILEALL_EXIT=0

python -B scripts/check_action_pins.py
Action pin check passed for 48 workflow and template files.
ACTION_PINS_AFTER_EXIT=0

node --test tests/incident_guard.test.cjs
ℹ pass 22
ℹ fail 0
NODE_AFTER_EXIT=0

git diff --check
DIFF_CHECK_AFTER_DOCS_EXIT=0
```

Red/green discipline: before implementation, the canonical portfolio and
supply-chain tests failed with `ModuleNotFoundError`/`SystemExit: 2`; after
implementation all listed suites pass. The wheel subcommand tests were also run
red before the CLI dispatch was added (`WHEEL_RED_EXIT=1`) and green after
(`WHEEL_GREEN_EXIT=0`).

Full-suite comparison:

| Revision | Command | Result |
| --- | --- | --- |
| Base `41353d1` | `python -B -m unittest discover -s tests -v` | `Ran 1201 tests`, `FAILED (failures=47, errors=123, skipped=44)`, `BASELINE_UNITTEST_EXIT=1` |
| Post-change | `python -B -m unittest discover -s tests -v` | `Ran 1212 tests`, `FAILED (failures=47, errors=123, skipped=44)`, `FINAL_UNITTEST_EXIT=1` |

The 11 additional tests are the new canonical portfolio, wheel-verification and
adapter-delegation tests. A header-set comparison of the two logs reports
`BASE_FAILING_IDS 135`, `FINAL_FAILING_IDS 135`, `NEW_IN_FINAL 0`,
`MISSING_FROM_FINAL 0`. The failure population is unchanged; the pre-existing
Windows/environment failures are not suppressed.

## F. Security verification

VERIFIED:
- Source analysis remains local and read-only; git argv is an explicit allowlist
  (`config --get remote.origin.url`, `rev-parse`, `status --porcelain`).
- Extraction argv is fixed: `graphify extract <path> --code-only --out <dir>`;
  no shell, install, hook, `--global`, upload, publish, deploy or paid call.
- Offline environment blanks provider keys and sets `GRAPHIFY_BACKEND=none` and
  `GRAPHIFY_QUERY_LOG_DISABLE=1`; report says
  `network_egress_verification: "not_verified"`, never stronger.
- Output/source overlap, existing output and in-source `graphify-out` are refused;
  source HEAD/status is snapshotted before and after extraction.
- Canonical reports still pass through the existing path sanitizer; legacy
  absolute-path evidence remains intentionally unsanitized for compatibility.
- Wheel verification validates a complete lowercase 64-hex digest before opening
  the file, streams SHA-256, uses `hmac.compare_digest`, and refuses missing or
  mismatched wheels with exit `2` and no report payload.
- Action pin check passed for 48 files; no workflow, permission or secret changed.

NOT RUN / UNVERIFIED:
- Real Graphify binary, wheel artifact, wheel provenance and extraction are NOT RUN
  because the CLI is not installed locally and no download was authorized.
- After-change Bandit rerun is BLOCKED: `No module named bandit` / `BANDIT_NOT_FOUND`
  in this environment. The earlier base run reported `BANDIT_BASE_EXIT=0`,
  `BANDIT_ISSUE_LINES=0`; new subprocess call sites carry fixed argv and `# nosec`
  annotations, but no fresh scan is claimed.
- Docker/Trivy, Terraform, kubectl, actionlint, pip-audit, hosted OIDC/WIF,
  managed-database tenant denial, backup restore, alert delivery, live CI and
  Keycloak runtime are NOT RUN or BLOCKED by scope/tool availability.

## G. Windows classification

The base full suite was run on Windows at `41353d1`: `Ran 1201 tests`,
`FAILED (failures=47, errors=123, skipped=44)`. The failure population was
classified from stack-trace signatures; no test was changed to hide it:

| Category | Count | Classification |
| --- | ---: | --- |
| `FileNotFoundError [WinError 2]` after PATH/temp-path fixtures | 78 | Windows harness/environment |
| `secure_open_unavailable` (`O_NOFOLLOW`/`O_DIRECTORY`) | 29 | By-design fail-closed; environment limitation |
| `OSError [WinError 1314]` symlink creation | 13 | Windows privilege/harness |
| missing `cryptography` | 13 | Missing optional API dependency locally |
| Gitleaks PATH/git failures | ~18 | Windows harness/PATH |
| missing `jwt` | 7 | Missing optional API dependency locally |
| `GITHUB_WORKSPACE` path canonicalization | 3 | Windows path semantics |
| `dataset_digest_mismatch` | 2 | UNVERIFIED after fresh re-baseline; CRLF checkout |
| `os.mkfifo`, temp permission, psycopg/opentelemetry and other CLI mismatches | ~8 | Windows/platform or missing dependency |

Post-change comparison: `Ran 1212 tests` with the same
`failures=47, errors=123, skipped=44` and the same 135 unique failing-test
headers as the base (`NEW_IN_FINAL=0`, `MISSING_FROM_FINAL=0`). The added tests
all passed. This is evidence that the Windows/environment failure set did not
change; it is not evidence that those failures are resolved. The two
`dataset_digest_mismatch` cases remain UNVERIFIED.

No Graphify regression was added to the Windows failure set by this work. Hosted
Ubuntu CI remains authoritative for source acceptance; its exact-head result is
NOT RUN locally.

## H. Blockers

- `graphify` CLI not installed; real extraction, wheel provenance and runtime
  hash check NOT RUN.
- `python3` alias fails locally (`exit=9009`); `python` (3.12.10) was used.
- `npm` scripts blocked by PowerShell execution policy; Node smoke test ran.
- `gh` CLI unavailable; the in-app browser GitHub session is signed out
  (`hasSignIn=true`, no `Create pull request` control on the loaded compare
  page). The branch is pushed, but Draft PR creation is BLOCKED.
- Bandit module unavailable for the post-change rerun.
- No hosted CI, cloud, database, identity, Keycloak, Terraform, Trivy or
  deployment runtime evidence was produced.
- Gates unchanged: `p01-managed-saas=BLOCKED`, `ai9-detection-quality=BLOCKED`,
  `codex-agent-runtime-acceptance=OPEN`. Ledger remains stale at `latest_pr:717`;
  no gate was promoted.

## I. Readiness

**Ready for Draft PR review only. NOT ready for merge, deploy or gate promotion.**

The code consolidation and fail-closed digest helper are VERIFIED by fresh local
tests. The branch is based on the verified PR #725 merge commit and contains no
merge, cloud, secret or infrastructure change. Merge readiness still requires
owner review, hosted exact-head CI, and separate resolution of the open gates and
unrelated P2/P3 findings listed in section C.

## J. PR URL

The branch was pushed successfully (`PUSH_EXIT=0`, new remote branch). Draft PR
creation is **BLOCKED**: `gh` is unavailable and the in-app browser GitHub
session is signed out; the loaded compare page showed `hasSignIn=true` and no
`Create pull request` control. Exact compare URL:

https://github.com/hamedonassar95/Devobs/compare/main...feature/graphify-unification-readiness

Owner action: sign in to GitHub, open the compare page above, select **Draft
pull request**, target `main`, and paste this audit as the review checklist. No
merge approval is requested here.

## K. Next single task

Open the Draft PR from the compare URL and record the exact-head hosted CI run
ID. Do not merge or promote any gate from this task.
