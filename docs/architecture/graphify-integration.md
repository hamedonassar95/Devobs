# Offline Graphify integration — design, privacy and evidence

**Status:** local, opt-in, read-only integration. No hosted service, no paid
inference, no source upload, no repository permission change, no merge or deploy.
This document describes code and local runs, not a live CI or production service.

## 1. Scope

One pinned Graphify CLI installation is reused for every authorized repository.
Each repository has its **own external index directory**; no index is written
inside a source tree and no Graphify global state (`~/.graphify`) is used.
The allowlist lives in
[`assets/graphify/multi_repo_manifest.json`](../../assets/graphify/multi_repo_manifest.json)
and contains only logical identifiers — local roots are passed at run time.

In scope: fast local code navigation, dependency graphs, impact analysis,
per-repository isolation, privacy checks and measured search latency.

Out of scope: hosted OAuth/MCP, `gh`-authenticated features such as `graphify prs`,
cloud deployment, billing, repository rule changes, and automatic merge.

**Canonical status (2026-11-20):** `tools/graphify` with CLI
`scripts/graphify/multi_repo.py` is the supported implementation for new work.
`scripts/integrations/graphify_portfolio.py` is now a thin backward-compatible
adapter with no orchestration or subprocess implementation; it preserves the
legacy 0.9.112 contract and emits a deprecation notice. The moved logic lives in
`tools/graphify/portfolio.py` and `tools/graphify/portfolio_execution.py`. See
[the F01b consolidation plan](GRAPHIFY_CONSOLIDATION_PLAN.md) for the exact
compatibility contract and evidence.

## 2. Verified tool identity and supply chain

| Property | Value | Evidence |
| --- | --- | --- |
| Package | `graphifyy` 0.9.113 | PyPI artifact and `graphify --version` → `graphify 0.9.113` |
| Wheel SHA-256 | `62f8483e536c9200f93665f9c61df6489436ab087432e0a0a738bd88096e0491` | local `Get-FileHash` of the pinned PyPI wheel; now enforced by `tools/graphify/supply_chain.py` for local wheel verification |
| License | Apache-2.0 | package metadata |
| Advisory | `GHSA-pcc4-rvhr-2pr8` fixed in 0.9.70; pinned 0.9.113 is above the fix | published advisory |
| Backend | deterministic local graph; no vector store or hosted service required | official docs below |

Official references:
- https://docs.graphify.com/open-source/overview.md
- https://docs.graphify.com/concepts/outputs.md
- https://docs.graphify.com/open-source/features/multi-repo.md
- https://docs.graphify.com/open-source/features/pr-impact.md
- https://docs.graphify.com/open-source/features/incremental-updates.md

## 3. Architecture

```
one pinned graphify executable (outside the repository)
        |
        +-- manifest: authorized repos, tags, extra excludes, search terms
        |
        +-- runner: version pin + offline env + code-only extract + validation
        |
        +-- one index directory per tag: <index-root>/<tag>/graphify-out/graph.json
        |
        +-- per-repo result: success | blocked | skipped (failures isolated)
```

Key implementation files:
- `tools/graphify/runner.py` — subprocess wrapper, version pin, offline
  environment, graph validation, source snapshot before/after.
- `tools/graphify/common.py` — exclusions, schema validation, sanitizers.
- `tools/graphify/adapters.py` — Devobs-owned adapters; explicitly **not**
  native Graphify features.
- `tools/graphify/multi_repo.py` — manifest validation, per-repo isolation,
  path-safe report aggregation.
- `tools/graphify/portfolio.py` — canonical legacy-compatibility policy,
  discovery and plan contracts.
- `tools/graphify/portfolio_execution.py` — canonical extraction/CLI layer used
  by the legacy adapter; no implementation remains in `scripts/integrations`.
- `tools/graphify/supply_chain.py` — fail-closed local wheel SHA-256 verifier.
- `scripts/graphify/multi_repo.py` — CLI entry point.

Native Graphify commands used: `extract`, `query`, `affected`, `god-nodes`,
`diagnose`, `merge-graphs`. Devobs adapters used for repository structure,
workflow jobs, branches, docs links and dependency-to-source mapping.

## 4. Privacy and safety controls

1. **Offline by construction.** Child processes receive blank provider keys,
   `GRAPHIFY_BACKEND=none`, query logging disabled and a dead-loop proxy.
   The proxy is defense in depth, not proof of network isolation.
2. **No global state.** `HOME`, `USERPROFILE`, `XDG_CONFIG_HOME` and
   `XDG_DATA_HOME` are redirected under the explicit external output root.
   `--global` is never used.
3. **Separate indexes.** `--out <index-root>/<tag>` is required; the runner
   refuses any source/output overlap and verifies the graph file resolves
   inside the output root.
4. **Fail-closed validation.** Version mismatch, missing graph, empty graph,
   malformed nodes/edges, dangling edges, unknown confidence, source mutation
   during extract and malformed config all stop that repository.
   Non-zero Graphify statuses 3/4 are reported as `ambiguous`/`no_match`,
   not silently treated as success.
5. **Exclusions.** `.env*`, secrets/credentials directories, service accounts,
   key/certificate formats, tfstate/tfplan, SSH/AWS dot-directories, token
   files and build/cache directories are excluded. Manifest entries add
   repository-specific patterns (for example Firebase applet configs and
   local Keycloak config).
6. **No path or secret leakage in reports.** All report payloads pass through a
   recursive JSON sanitizer that replaces absolute paths and bounds strings.
   CLI errors are emitted as codes or hashes, never raw stderr.
7. **Isolation.** Each repository is processed in its own try/catch. One
   blocked repository does not prevent the others from being indexed.

## 5. How to run

```powershell
python scripts/graphify/multi_repo.py validate `
  --manifest assets/graphify/multi_repo_manifest.json

python scripts/graphify/multi_repo.py run `
  --manifest assets/graphify/multi_repo_manifest.json `
  --index-root <external-index-root> `
  --source-root primary=<local-project-root> `
  --source-root portfolio=<local-portfolio-root> `
  --graphify-bin <pinned-graphify-exe> `
  --json-out <external-report.json>
```

Exit codes: `0` = no blocked repositories, `2` = configuration/policy failure,
`3` = at least one repository blocked. `skipped` does not fail the run.

To verify a locally provisioned wheel without installing or downloading it:

```powershell
python scripts/graphify/repository_intelligence.py verify-wheel --wheel <local-wheel>
```

A missing wheel, truncated digest or hash mismatch exits `2` with `FAIL
<reason>`; this command never modifies the environment.

Per-repository single-repo commands and adapters are documented in
[repository-intelligence.md](repository-intelligence.md).

## 6. VERIFIED local evidence (2026-11-20)

Exact commands and final output were captured on the reviewed working tree.

| Check | Command | Result |
| --- | --- | --- |
| Unit tests | `python -m unittest discover -s tests/graphify -v` | `Ran 41 tests`, `OK` |
| Static | `python -m compileall -q tools/graphify scripts/graphify`; `git diff --check` | exit `0` |
| Manifest | `python scripts/graphify/multi_repo.py validate --manifest assets/graphify/multi_repo_manifest.json` | exit `0`, 8 repositories |
| Real multi-repo run | `python scripts/graphify/multi_repo.py run ...` | `MULTI_EXIT=0`, `{"blocked":0,"skipped":3,"success":5,"total":8}` |
| Report safety | local JSON scan for `C:\DevProjects` / `C:\Users` | `ABSOLUTE_PATH_LEAK False` |
| Tool pin | report `product.reported_version` | `0.9.113` |

Per-repository outcomes from that run (source unchanged for every indexed repo,
`sensitive_source_file_count=0` for every indexed repo):

| Repository | Status | Nodes | Edges | Graph bytes | Extract ms | Search / impact |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `hamedonassar95/Devobs` | success | 8959 | 17192 | 7,339,239 | 44,534 | 2 ok / ok |
| `hamedonassar95/CineForge-AI` | success | 3831 | 10691 | 4,796,181 | 17,721 | 3 ok / ok |
| `hamedonassar95/devobs-saas` | success | 758 | 1840 | 655,362 | 9,982 | ambiguous, no_match / ok |
| `hamedonassar95/LiveOps-Integration` | success | 297 | 516 | 172,016 | 5,994 | 2 ok / ok |
| `hamedonassar95/ops` | success | 502 | 997 | 355,790 | 10,049 | ambiguous, no_match / ok |
| `hamedonassar95/al-dala-mobile` | skipped | — | — | — | — | `no_indexable_source` |
| `hamedonassar95/phone-repair-assistant-v2` | skipped | — | — | — | — | `public_api_404_and_no_local_checkout` |
| `hamedonassar95/DevObs-ai-Intelligence-` | skipped | — | — | — | — | `public_api_404_and_no_local_checkout` |

Earlier single-repo Devobs baseline (same pinned CLI): `BENCH_EXIT=0`,
extract `51,341 ms` then `29,839 ms`, 8,986/8,985 nodes, 17,109/17,108 edges,
`query ok 2829ms` and `query ok 3334ms`. The multi-repo run is not a like-for-like
performance comparison because exclusion patterns and machine load differ.

### F01b local evidence (post-consolidation)

| Check | Command | Final output |
| --- | --- | --- |
| Canonical suite | `python -B -m unittest discover -s tests/graphify -v` | `Ran 51 tests`, `OK` |
| Legacy contract suite | `python -B -m unittest tests.test_graphify_portfolio -v` | `Ran 28 tests`, `OK` |
| Wheel verifier suite | `python -B -m unittest tests.graphify.test_supply_chain -v` | `Ran 6 tests`, `OK` |
| Targeted guard suite | `python -B -m unittest tests.test_python_source_coverage tests.test_node_pipeline_selection tests.test_python_dependency_automation -v` | `Ran 11 tests`, `OK` |
| Syntax | `python -B -m compileall -q tools/graphify scripts/graphify scripts/integrations/graphify_portfolio.py` | exit `0` |
| Action pins | `python -B scripts/check_action_pins.py` | `Action pin check passed for 48 workflow and template files.` |

The exact base and post-change full-suite comparison is recorded in the
[unification audit](../audits/DEVOBS_GRAPHIFY_UNIFICATION_AUDIT.md). No Graphify
binary was installed or run for these checks.

## 7. Blocked and unverified items

- **BLOCKED — authenticated GitHub access.** `gh` is not installed in this
  environment and no authenticated browser session is available. Repository
  discovery used the unauthenticated public REST API. Pushing feature branches,
  opening PRs and any private-repository discovery require owner-provided
  authentication. A 404 on the public API is reported as `skipped`, never as
  proof that a repository does not exist.
- **UNVERIFIED — hosted CI.** No GitHub Actions run was executed on the
  feature-branch head; the table above is local evidence only.
- **UNVERIFIED — `CineForge-AI` remote.** The public API returned 404 for that
  name while a local checkout with that remote exists; push/PR availability is
  unknown.
- **Unchanged gates.** P01 = BLOCKED/NO-GO, AI-9 = BLOCKED, Codex runtime
  acceptance = OPEN. This integration does not alter them.

## 8. Rollback

For the F01b consolidation, revert the reviewed implementation commits as
described in [`docs/runbooks/GRAPHIFY_ROLLBACK.md`](../runbooks/GRAPHIFY_ROLLBACK.md).
Do not delete `tools/graphify/`, `scripts/graphify/`, `tests/graphify/`,
`assets/graphify/`, existing indexes or historical documentation merely because
logic moved. No repository source was extracted or uploaded by this change.
