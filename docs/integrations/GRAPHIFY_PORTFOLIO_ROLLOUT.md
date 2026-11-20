# Graphify portfolio integration (offline, dry-run first)

**Status: LEGACY historical evidence — integration implemented and tested;
rollout BLOCKED.** The orchestrator and its tests exist, but no authorized
repository currently meets the rollout preconditions (clean `main`/`master`
checkout), no Draft PR was opened, and no graph was uploaded anywhere.

**Canonical pointer (2026-11-20, F01b):** new work uses `tools/graphify` 0.9.113
via `scripts/graphify/multi_repo.py`. This document records the historical
legacy 0.9.112 rollout evidence. The path `scripts/integrations/graphify_portfolio.py`
is now a thin backward-compatible adapter over
`tools/graphify/portfolio_execution.py`; it preserves the flags, dry-run default,
`--execute --only` authorization, report schema, exit codes and deprecation
notice described below, but it no longer contains a second implementation. See
[the F01b consolidation plan](../architecture/GRAPHIFY_CONSOLIDATION_PLAN.md) and
[the rollback runbook](../runbooks/GRAPHIFY_ROLLBACK.md).

This document records what was verified on 2026-11-19. It is local, read-only
evidence and not a claim that any project is connected to a Graphify service.

## 1. Scope

| Item | Value |
| --- | --- |
| Repository | `hamedonassar95/Devobs` |
| Branch | `feature/graphify-portfolio-integration` |
| Base | `main` at `cbaf86b97339fb778038e51c7b2ca6724a61e3d6` |
| Orchestrator | `scripts/integrations/graphify_portfolio.py` |
| Tests | `tests/test_graphify_portfolio.py` |
| Pinned Graphify release | `graphifyy==0.9.112` |

Files changed by this task: the two files above, this document and a README
link. No application source, CI workflow, hook, service inventory or Android
configuration was modified.

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
   repository, a non-zero exit, missing `graph.json` or invalid JSON is reported
   as `failed`, and the CLI exits 3.
7. **No side channels.** The orchestrator never runs `graphify install`, never
   installs git hooks, never uses `--global`, `--postgres`, `--google-workspace`
   or any export/push subcommand, never uploads, publishes, deploys or
   schedules, and never calls an LLM backend.

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
| Uploads / hooks | none (`network_uploads: false`, `hooks_installed: false`) |
| `~/.graphify` global state | not created |
| Output footprint | 402 files, 20.4 MB, all under the external output root |

The orchestrator wrote the graph outside the source tree
(`...\graphify-pilot\graphs\Devobs-pilot\<sha>\graphify-out\graph.json`) plus a
local `run.json` containing the argv, offline environment, exit code, graph
hash, node/edge counts and the before/after repository state.

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

## 8. Draft Pull Request plan (blocked)

No Draft PR was opened:

- `gh` is not installed on this host.
- Extracting the credential-manager token to call the REST API is prohibited.
- No repository is eligible for a rollout graph, so a per-repository PR would
  document a blocked state rather than a result.

When a repository becomes eligible, the intended per-repository change is one
Draft PR containing only:

```text
docs/integrations/graphify/<sha>.md   # graph summary, node/edge counts, hash
```

and a one-line README link. The graph artifacts themselves stay outside the
repository; only the summary belongs in Git. The PR body must state the exact
commit, the pinned Graphify version, the offline environment variables, the
graph SHA-256, and that no upload, LLM call, hook or deployment occurred.

## 9. What this does not do

- No `graphify install`, no platform skill installation, no git hooks.
- No system images, emulators or Android toolchain changes.
- No cloud Firebase, paid inference, Graphify cloud service or upload.
- No change to CI workflows, `service-inventory.json` or existing integrations.
- No merge, release, deployment or scheduler.
- No claim about compile, lint or unit-test gates of any scanned project.

## 10. Next action

1. Merge or park the paused `pages-manifest-transient-retry` work so `Devobs`
   has a clean `main` checkout, or point the orchestrator at a clean clone.
2. Re-run the dry run, then execute one repository with explicit `--only`.
3. Review the local `run.json` and `graph.json` hash, then decide whether a
   documentation-only Draft PR is worth opening.

## Security hardening review (PR #720 follow-up)

The local `run.json` record deliberately omits child-process stdout/stderr and raw execution exceptions. It records `network_egress_verification: not_verified`; disabling known provider variables does **not** prove network isolation. Git inspection accepts only a fixed read-only command allowlist and resolves the Git executable before invocation. Malformed graph structures fail closed. This change does not authorize multi-repository activation, external indexing, deployment, or merging without a passing exact-head CI review.
