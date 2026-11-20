# Repository intelligence — reusable architecture

This is the reusable layer beneath the multi-repo orchestrator described in
[graphify-integration.md](graphify-integration.md). It is local, read-only and
deliberately split into three concerns.

## Modules

| Module | Responsibility |
| --- | --- |
| `tools/graphify/common.py` | Policy constants, pinned version/hash, exclusion patterns, graph schema validation, source snapshotting, string/JSON sanitizers |
| `tools/graphify/runner.py` | `GraphifyRunner` — pinned, offline subprocess calls, extraction, native queries, native merge |
| `tools/graphify/adapters.py` | Devobs-owned adapters: tree, workflow jobs, branches, docs links, dependency mapping, bounded cross-repo view |
| `tools/graphify/repository_intelligence.py` | Stable public surface and single-repository CLI |
| `tools/graphify/multi_repo.py` | Authorized manifest, per-repository isolation, aggregated path-safe report |
| `scripts/graphify/repository_intelligence.py` | Single-repository CLI entry point |
| `scripts/graphify/multi_repo.py` | Multi-repository CLI entry point |

## Native features versus Devobs adapters

The report marks every result with `native_graphify_feature`.

- **Native:** `extract`, `query`, `path`, `explain`, `affected`, `god-nodes`,
  `diagnose`, `merge-graphs`. These are Graphify CLI capabilities.
- **Devobs-owned:** tree categories, workflow `needs` edges, branch/worktree
  view, documentation link graph, dependency-to-source mapping, bounded
  cross-repo view and changed-file impact mapping via repeated `affected`
  queries. These are local thin views over git/files and the graph; they are
  **not** Graphify features and must not be described as such.

## Graph contract

`validate_graph()` accepts only a node/edge document where:

- nodes are objects with a unique non-empty string `id`;
- `label`, `source_file` and `source_location` are strings or `null`
  (Graphify 0.9.113 emits `source_location: null` for file nodes);
- edges are objects with string endpoints, a non-empty `relation` and one of
  `EXTRACTED`, `INFERRED`, `AMBIGUOUS`;
- no edge points to a missing node;
- the file is non-empty and below 512 MiB;
- extraction additionally requires at least one node and one source file.

Both `edges` and native merged `links` keys are supported. Cycle back-edges,
orphans, confidence counts and relation counts are reported for impact analysis.

## Single-repository CLI

```powershell
python scripts/graphify/repository_intelligence.py build `
  --source <source-dir> --output-root <external-index-dir> `
  --graphify-bin <pinned-graphify-exe> --json-out <external-report.json>

python scripts/graphify/repository_intelligence.py search `
  --graph <index-dir>\graphify-out\graph.json --kind affected --term <term>

python scripts/graphify/repository_intelligence.py impact `
  --graph <index-dir>\graphify-out\graph.json --changed-file <relative-path>

python scripts/graphify/repository_intelligence.py cross-repo `
  --config <external-config.json> --json-out <external-report.json>

python scripts/graphify/repository_intelligence.py benchmark `
  --source <source-dir> --output-root <external-index-dir> `
  --iterations 2 --search-term <term> --json-out <external-benchmark.json>
```

`build`, `inspect`, `cross-repo` and `benchmark` refuse a report path inside any
source. `graphify tree --root` requires repository-relative roots; the adapters
therefore use relative paths only.

## Isolation and reporting

- Each repository in a multi-repo run is wrapped independently. Domain errors
  become `blocked` with a sanitized reason; unexpected exception types are
  recorded as `unexpected_<TypeName>` and never abort the remaining repos.
- Disabled or unavailable repositories are `skipped` with an explicit reason.
- Reports contain logical tags and GitHub names, graph hashes and sizes, timing
  and status — no absolute local paths, raw stdout/stderr, tokens or secrets.
- Exit codes make automation fail closed: `0` no blocked, `2` configuration or
  policy failure, `3` at least one blocked repository.

## Tests

`tests/graphify/` uses synthetic fixtures and subprocess doubles; no test needs
network, credentials or a real source checkout. It covers schema validation,
offline invocation, version pinning, source-mutation detection, path overlap,
sensitive-file detection, per-repository failure isolation, disabled and empty
repositories, search/impact recording and absence of absolute paths in reports.

Verified locally: `python -m unittest discover -s tests/graphify -v` →
`Ran 41 tests`, `OK`.
