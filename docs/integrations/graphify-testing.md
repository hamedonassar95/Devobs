# Graphify Integration Regression Testing

**Status:** Local/offline regression coverage for Graphify graph validation and integration contracts. No external APIs, no paid inference, no Graphify uploads.

## Scope

This suite protects the existing Graphify integration behavior introduced by PR #720 and the canonical `tools/graphify` package. It focuses on deterministic, fail-closed validation of graph data and actionable diagnostics.

Covered:
- Valid node-link graphs (`edges` and `links`)
- Missing node references / dangling edges (fail closed)
- Duplicate edges (deterministic counting/diagnostics; no behavior change)
- Dependency cycles (detected and reported with bounded samples)
- Malformed inputs (invalid JSON, wrong types, missing files, size out of range)
- Integration contract checks via existing Graphify suites (runner, adapters, CLI, portfolio, multi-repo)

Out of scope:
- Calling real Graphify services or installing packages from network
- Modifying security gates, scheduler, or incident intelligence modules
- Any production deployment, merge, or secret handling

## Entry points (VERIFIED)

| Entry point | Role | Notes |
|---|---|---|
| `tools/graphify/common.py` | Graph schema validation / diagnostics | `validate_graph`, `read_graph`, `GraphSchemaError`, cycle/dangling detection |
| `tools/graphify/runner.py` | Pinned offline Graphify CLI wrapper | fixed argv, env sanitization, source-mutation guard, fail-closed |
| `tools/graphify/repository_intelligence.py` | Local report/CLI surface | build report, adapters, search/impact/benchmark |
| `tools/graphify/portfolio.py` + `portfolio_execution.py` | Legacy-compatible portfolio orchestration contract | dry-run default, `--execute --only`, no upload/hooks/install |
| `scripts/integrations/graphify_portfolio.py` | Legacy adapter path preserved by PR #720 | delegates to canonical portfolio implementation |
| `scripts/graphify/multi_repo.py` + `tools/graphify/multi_repo.py` | Canonical multi-repo offline orchestration | per-repo isolation, path-safe reports |

## Regression fixtures

Fixtures live under `tests/graphify/fixtures/`:

- `valid_graph.json` - minimal valid graph
- `missing_node.json` - edge references missing node; expects dangling-edge diagnostic
- `duplicate_edges.json` - duplicate edge records; expects deterministic stats
- `dependency_cycle.json` - cycle; expects `cycle_back_edges >= 1` and sample
- `malformed_input.json` - malformed structure; expects actionable schema error

## Running tests

Targeted regression suite:

```sh
python -m unittest tests.graphify.test_graphify_regressions -v
```

Existing Graphify integration suites:

```sh
python -m unittest tests.test_graphify_portfolio -v
python -m unittest discover -s tests/graphify -p "test_*.py" -v
```

Syntax check (touched/new files):

```sh
python -m py_compile tests/graphify/test_graphify_regressions.py
git diff --check
```

## Diagnostics contract

Failures must be actionable and fail closed:
- Invalid root/nodes/edges/confidence: `GraphSchemaError` with specific code (e.g. `graph_edges_or_links_must_be_array`, `graph_edge_confidence_not_supported`).
- Dangling edges: `graph_has_{n}_dangling_edges`.
- Missing/empty/oversized/invalid JSON graph files: `RepositoryIntelligenceError` / `GraphSchemaError` with specific reason.
- Cycle detection: `cycle_back_edges` and bounded `cycle_samples` included in stats.

## Safety

- No network calls or paid APIs.
- No secrets/tokens read or written.
- No modifications to security gates, scheduler, or incident intelligence modules.
- Existing production behavior preserved; tests add coverage only.
