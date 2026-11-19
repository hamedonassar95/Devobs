# Graphify portfolio integration (offline, dry-run first)

**Status: integration implemented, execution evidence hardened; rollout
BLOCKED.** The orchestrator and its tests exist, but no authorized repository
currently meets the rollout preconditions (clean `main`/`master` checkout), and
the per-repository rollout Draft PRs were not opened. Run evidence no longer
retains raw process output, and network-upload state is recorded as
`UNVERIFIED` instead of being asserted.

This document records what was verified on 2026-11-19 and 2026-11-20. It is
local, read-only evidence and not a claim that any project is connected to a
Graphify service.

## 1. Scope

| Item | Value |
| --- | --- |
| Repository | `hamedonassar95/Devobs` |
| Branch | `feature/graphify-safe-evidence` |
| Base | `23b18502434b0d22f40a14037ac94c0901936e92` (head of PR #720) |
| Parent PR | #720 (`feature/graphify-portfolio-integration`, open Draft, base `main`) |
| Orchestrator | `scripts/integrations/graphify_portfolio.py` |
| Tests | `tests/test_graphify_portfolio.py` |
| Pinned Graphify release | `graphifyy==0.9.112` |

Files changed by this task: the orchestrator, its tests and this document. No
application source, CI workflow, hook, service inventory, README or Android
configuration was modified, and no additional repository was scanned.

## 2. Provenance of `graphifyy==0.9.112`

VERIFIED from the public package index and the upstream repository:

| Evidence | Value |
| --- | --- |
| PyPI JSON API | `https://pypi.org/pypi/graphifyy/0.9.112/json` (HTTP 200) |
| Wheel | `graphifyy-0.9.112-py3-none-any.whl`, 1,997,065 bytes |
| Wheel SHA-256 | `ad6a9152fb6d9c5d85a77ffcaf29e18c5634a7d5ca474edb218cbc68b062241d` |
| Downloaded wheel SHA-256 | identical (recomputed with `Get-FileHash -Algorithm SHA256`) |
| sdist | `graphifyy-0.9.112.tar.gz`, 3,526,647 bytes, published 2026-11-17 |
| Publisher (PEP 740 attestation) | GitHub, `Graphify-Labs/graphify`, workflow `publish.yml` |
| Upstream repository | `https://github.com/Graphify-Labs/graphify`, Apache-2.0, not archived |
| Upstream release | `v0.9.112` published 2026-11-17T15:42:01Z |

The PEP 740 attestation bundle at
`https://pypi.org/integrity/graphifyy/0.9.112/graphifyy-0.9.112-py3-none-any.whl/provenance`
returned HTTP 200 with a GitHub-sourced publisher identity, so the wheel is
cryptographically linked to the public upstream repository and its publish
workflow. The installation used Python 3.12.10 in an isolated virtual
environment (`%USERPROFILE%\DevTools\graphify-venv`); the console entry point
reports `graphify 0.9.112`.

Limits: the repository-level stars/popularity were not used as a trust signal.
No GPG verification of the sdist was performed, and the package was installed
with pip's normal index-integrity check rather than a repository-wide hash
lockfile.

## 3. Security advisories

OSV (`https://api.osv.dev/v1/query`, ecosystem `PyPI`, package `graphifyy`)
returns exactly one advisory for the package:

**GHSA-pcc4-rvhr-2pr8** - "Graphify Fortran extractor: incomplete cpp
`#include` hardening allows arbitrary host-file read/exfiltration when indexing
an untrusted repo".

| Field | Value |
| --- | --- |
| Published | 2026-10-19 |
| GitHub severity | Moderate (CVSS v4 vector `AV:L/AC:L/AT:N/PR:N/UI:P/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N`) |
| Affected range | `>= 0.7.2, < 0.9.70` |
| Fixed version | `0.9.70` |
| Pinned version assessment | **Not affected** (0.9.112 is above the fixed version) |

The vulnerable code path is the Fortran C-preprocessor step, which reads
`#include` targets outside the corpus. The pinned release is outside the
affected range, and this integration only scans locally trusted owner
repositories, never arbitrary untrusted corpora. This is recorded as a residual
risk to re-check on every version change, not as a cleared finding.

The orchestrator pins the exact version: any other reported version is refused
before extraction (`not the pinned 0.9.112`).

## 4. Offline invocation and the `--backend none` deviation

The requested literal command was:

```sh
graphify extract PATH --code-only --backend none
```

**VERIFIED: that flag is rejected by the pinned release.** Running it against a
synthetic corpus returned:

```text
error: unknown backend 'none'. Available: azure, bedrock, claude, claude-cli,
deepseek, gemini, kimi, ollama, openai
exit code 1
```

The supported offline switch in 0.9.112 is the documented environment variable
`GRAPHIFY_BACKEND=none`; it keeps the local AST pass and skips every LLM step
(`graphify/cli.py`, "GRAPHIFY_BACKEND=none: skipping LLM work"). The same probe
with `GRAPHIFY_BACKEND=none` and `GRAPHIFY_QUERY_LOG_DISABLE=1` completed with
exit 0 and wrote `graph.json`.

The orchestrator therefore runs:

```sh
GRAPHIFY_BACKEND=none GRAPHIFY_QUERY_LOG_DISABLE=1 \
  graphify extract PATH --code-only --out EXTERNAL_DIR
```

and never passes the unsupported `--backend` flag. Provider credential
variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `KIMI_API_KEY`, `MOONSHOT_API_KEY`,
`AZURE_OPENAI_API_KEY`) are blanked in the child environment as defence in
depth, and only their names are written to the local run record.

Because `--out DIR` writes `DIR/graphify-out/`, the output directory is chosen
outside every source repository and is checked twice: at the portfolio level and
again per repository immediately before the run.

## 5. Safety model

1. **Dry-run by default.** Discovery and planning create no directory and write
   no file. Tests assert the repository tree is byte-for-byte unchanged.
2. **Explicit execution.** `--execute` is refused unless at least one
   `--only <repository>` is supplied; there is no "scan everything" mode.
3. **Authorization.** Only `origin` remotes on `github.com` owned by
   `hamedonassar95` are eligible. `git@`, `ssh://` and `https://` forms are
   accepted; other hosts, other owners and local paths are blocked.
4. **Branch and cleanliness.** Only `main` or `master` is eligible; a dirty
   working tree is blocked. This keeps a graph tied to a reviewed commit.
5. **Output containment.** An output root inside a source repository, or a
   source repository inside the output root, is refused. An existing output
   directory is never overwritten.
6. **Post-run proof.** The working tree and `HEAD` are snapshotted before and
   after extraction. Any change, any `graphify-out` inside the source
   repository, a non-zero exit, a missing `graph.json`, invalid JSON or a
   structurally invalid graph is reported as `failed`, and the CLI exits 3.
7. **No side channels.** The orchestrator never runs `graphify install`, never
   installs git hooks, never uses `--global`, `--postgres`, `--google-workspace`
   or any export/push subcommand, never uploads, publishes, deploys or
   schedules, and never calls an LLM backend. `network_uploads` is recorded as
   `UNVERIFIED`: absence of an HTTP client in this module is not an attestation
   about the pinned binary.
8. **Evidence hygiene.** Raw process output is never retained; credential
   shapes are redacted before any write, and a residual match withholds the
   whole record. See section 8.

## 6. Local discovery result

Command (dry run, no writes):

```sh
python scripts/integrations/graphify_portfolio.py --root C:\DevProjects --json
```

| Checkout | Branch | HEAD | Result |
| --- | --- | --- | --- |
| `CineForge-AI` | `feature/android-local-toolchain-provision` | `9af4f9f` | BLOCKED: branch is not `main`/`master` |
| `Devobs` | `feature/pages-manifest-transient-retry` | `cbaf86b` | BLOCKED: branch is not `main`/`master`; 4 uncommitted files |
| `Devobs-graphify` | worktree | n/a | SKIPPED: linked worktree of `Devobs` |

Both checkouts are authorized (owner `hamedonassar95`, correct `origin`), but
neither is eligible for a rollout graph today. No other local GitHub checkouts
were found. Remote-only repositories were not cloned for this task.

This table is a 2026-11-19 snapshot. Later branch changes (for example a Gradle
verification branch in `CineForge-AI`) are not reflected; re-run the dry run
before rollout.

## 7. Isolated pilot (executed)

The pilot ran against a **disposable local clone** of `Devobs` `main` at
`cbaf86b97339fb778038e51c7b2ca6724a61e3d6`. Its `origin` was rewritten to the
canonical `https://github.com/hamedonassar95/Devobs.git` so the same
authorization check applied. The real `Devobs` checkout (dirty) and the linked
worktree were not touched.

```sh
GRAPHIFY_BACKEND=none GRAPHIFY_QUERY_LOG_DISABLE=1 \
  graphify extract <pilot-clone> --code-only --out <external-dir>
```

with `HTTP_PROXY`/`HTTPS_PROXY` pointed at a dead local port (`127.0.0.1:9`) and
`NO_PROXY` cleared, so any outbound HTTP attempt would have failed.

| Result | Value |
| --- | --- |
| CLI exit | 0 (`status: extracted`, `failure: null`) |
| Duration | 107.7 s |
| Files scanned | 599 code files; 406 docs skipped by `--code-only`; 34 unclassified skipped |
| Graph | 8,797 nodes, 16,290 edges, 490 communities |
| `graph.json` | 8,107,170 bytes |
| `graph.json` SHA-256 | `ba66e853378bbbc9ca2b22ec57990ed37a1b4d80fee9b2d40565b85732d5c403` |
| Repository after run | unchanged (`git status` empty, `HEAD` unchanged) |
| Stray `graphify-out` in source | none |
| Network uploads | `UNVERIFIED` - see section 8 |
| Hooks installed | `NOT_PERFORMED` (no install subcommand is ever invoked) |
| `~/.graphify` global state | not created |
| Output footprint | 402 files, 20.4 MB, all under the external output root |

That pilot was produced by the previous evidence schema, which still stored a
short stdout/stderr tail. The tail is no longer written; the graph and
repository proof above are unaffected.

The orchestrator wrote the graph outside the source tree
(`...\graphify-pilot\graphs\Devobs-pilot\<sha>\graphify-out\graph.json`) plus a
local `run.json` containing the argv, offline environment, exit code and output
byte counts, graph hash and file-derived counts, and the before/after
repository state.

Pilot limitations:

- Terraform/SQL/HCL files contributed nothing: `tree_sitter_sql` and
  `tree_sitter_hcl` are optional extras (`graphifyy[sql]`,
  `graphifyy[terraform]`) that were deliberately not installed. 3 `.sql`,
  3 `.tf` and 2 `.hcl` sources are therefore incomplete in this graph.
- 16 code files yielded no symbols, and 34 files had no supported extension.
- The graph is AST-only and structural. Clustering ran locally; no LLM named
  communities, so these results cannot be used for semantic claims.
- A dead-proxy run shows extraction required no HTTP. It does not prove that no
  connection was attempted and immediately failed.
- The pilot does not make the real checkouts eligible; it only proves the
  orchestrator and the offline invocation work end to end.

## 8. Evidence model and redaction

`run.json` is deliberately free of process output. It records:

| Field | Content |
| --- | --- |
| `policy`, `graphify_version` | fixed identifiers |
| `repository` | name, path, redacted remote, branch, HEAD, dirty flag |
| `command` | exact argv (paths only) |
| `environment` | the two offline variables plus the *names* of blanked provider variables |
| timing | `started_at`, `finished_at`, `duration_seconds` |
| `exit_code`, `stdout_bytes`, `stderr_bytes` | status and output size, never output |
| `graph` | path, SHA-256, byte size, node/edge counts from the validated file |
| `repository_unchanged`, `stray_graphify_out_in_repository` | before/after proof |
| `evidence` | `network_uploads: UNVERIFIED`, `hooks_installed: NOT_PERFORMED`, `process_output: NOT_RETAINED` |
| `status`, `failure` | outcome; failure text is index-based and redacted |

Removed by this change: `stdout_tail`, `stderr_tail` and any diagnostic dump.
The old schema could copy file names, test names and source identifiers from
Graphify warnings into evidence that sits beside the repository.

Redaction runs before every write and before the JSON report is printed:

- URL userinfo (`scheme://user:token@host`) becomes
  `scheme://[REDACTED]@host`; the host is kept.
- `KEY=value` / `TOKEN: value`, `Bearer ...` and provider token shapes
  (`ghp_`, `github_pat_`, `glpat-`, `xox?-`, `AKIA...`, `AIza...`, `sk-...`),
  JWTs and PEM private-key blocks become `[REDACTED]`.
- Git object ids and SHA-256 digests are lowercase hex and are preserved:
  there is no generic long-hex or base64 rule.
- After sanitization a second scan of the serialized record must find no known
  secret shape. If it does, the record is withheld and replaced with a fixed
  failure stub (`sensitive_evidence_withheld: true`).

This is defence in depth, not a guarantee. It cannot recognise an unknown
credential format, and it keeps the local filesystem path and repository name
because the operator needs them to locate the run.

### Graph validation

`status: extracted` requires `graph.json` to pass structural checks first: a
JSON object root, `nodes` and `links` lists, at least one node, unique
non-empty **string** node ids, both link endpoints resolving to a known id, and
boolean `directed`/`multigraph` plus object `graph` metadata when present.
Counts come from the validated file, never from stdout. Error messages cite
node/link indexes only, so a private node id is not echoed into evidence. The
real pilot graph satisfies these rules (8,797 unique string ids, 16,290 links,
0 dangling endpoints), which is why the checks are strict rather than
heuristic.

## 9. Draft Pull Request plan

This branch is stacked: it targets `feature/graphify-portfolio-integration`
(PR #720), not `main`, so PR #720 can be reviewed first.

No Draft PR could be opened from this host: `gh` is not installed, and
extracting the credential-manager token to call the REST API is prohibited.
Once `gh` is available, open a **Draft** PR with:

```text
base:   feature/graphify-portfolio-integration
head:   feature/graphify-safe-evidence
title:  fix(graphify): harden execution evidence and privacy
```

Compare URL:

```text
https://github.com/hamedonassar95/Devobs/compare/feature/graphify-portfolio-integration...feature/graphify-safe-evidence
```

The PR body must reference PR #720, the hardening commits, the test result and
the residual risks below. Future per-repository rollout PRs (not opened)
contain only a summary under `docs/integrations/graphify/<sha>.md` plus a
one-line README link; graph artifacts stay outside Git.

## 10. Residual risks

- Removing raw output means a failed run is diagnosed by re-running it, not by
  reading a log from `run.json`.
- Redaction cannot catch an unknown credential format, and local paths and
  user names remain in evidence.
- A sibling branch `feature-graphify-security-privacy` (`a344fd6`) touches the
  same functions (sanitized diagnostics, Bandit suppressions). This branch was
  created from `23b1850` as instructed, so the two will conflict and must be
  reconciled before either merges. The Bandit findings (`B404`, `B603`,
  `B607`) fixed on that sibling branch are **not** fixed here.
- `network_uploads: UNVERIFIED` is a declaration. The dead-proxy pilot shows
  extraction needed no HTTP; it is not proof that no connection was attempted.
- No repository is rollout-eligible today, so the hardened path has not been
  exercised against a real eligible checkout. It is covered by synthetic tests
  and the earlier pilot's graph, not by a new end-to-end real run.

## 11. What this does not do

- No `graphify install`, no platform skill installation, no git hooks.
- No system images, emulators or Android toolchain changes.
- No cloud Firebase, paid inference, Graphify cloud service or upload.
- No change to CI workflows, `service-inventory.json` or existing integrations.
- No merge, release, deployment or scheduler.
- No claim about compile, lint or unit-test gates of any scanned project.

## 12. Next action

1. Resolve the paused `pages-manifest-transient-retry` work so `Devobs` has a
   clean `main` checkout, or point the orchestrator at a clean clone.
2. Reconcile with `feature-graphify-security-privacy` before merging either
   hardening branch.
3. Re-run the dry run, then execute one repository with explicit `--only`, and
   review the new `run.json` schema and graph hash.
