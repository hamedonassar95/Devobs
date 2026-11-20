# Graphify consolidation plan — 2026-11-20

**Status:** canonical implementation designated; full code consolidation
deferred to an owner-approved migration PR.
**Reviewed revision:** `cecae6ce7a9b3d06b961a94d3fc13a767a8c9ed1`.

## 1. Decision

| Role | Path | Pin / policy | Status |
| --- | --- | --- | --- |
| **Canonical implementation** | `tools/graphify/` | `graphifyy` 0.9.113; `devobs-repository-intelligence-v1`; declared wheel SHA-256 `62f8483e536c9200f93665f9c61df6489436ab087432e0a0a738bd88096e0491` | Supported for new work. |
| Canonical public CLI | `scripts/graphify/multi_repo.py`; `scripts/graphify/repository_intelligence.py` | Thin shims importing `tools.graphify.*` | Supported entry points. |
| **Legacy implementation** | `scripts/integrations/graphify_portfolio.py` | `graphifyy` 0.9.112; `devobs-graphify-portfolio-v1` | Backward-compatible; emits deprecation warning. |
| Legacy tests/docs | `tests/test_graphify_portfolio.py`; `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md` | Historical 0.9.112 evidence | Retained; not used for new acceptance. |

`scripts/graphify/` is **not** a third implementation. Its two Python files add
the repository root to `sys.path` and import `tools.graphify.*`; they are CLI
entry points only.

## 2. Evidence for the decision

1. **Import direction:** `scripts/graphify/multi_repo.py:9-13` and
   `scripts/graphify/repository_intelligence.py:14-17` import `tools.graphify.*`.
2. **Test ownership:** five modules under `tests/graphify/` import the package
   directly; `python -B -m unittest discover -s tests/graphify -v` →
   `Ran 41 tests`, `OK`.
3. **Configuration:** `assets/graphify/multi_repo_manifest.json` and
   `docs/architecture/graphify-integration.md` describe the 0.9.113 multi-repo
   design, external index roots and privacy controls.
4. **Merge order:** #720 added the portfolio orchestrator; #723 added the
   centralized `tools/graphify` package; #724 made tools-only changes visible to
   Python CI. Current `main` is the #724 merge commit `cecae6c`.
5. **Runtime metadata:** `tools/graphify/common.py:17-19` exposes both the pin
   and wheel SHA; the legacy script exposes only the 0.9.112 version pin.

The prior recovery audit marked owner approval as required for **deletion or API
merging**. This document makes the evidence-based designation without deleting
or changing either implementation, so no migration action is implied.

## 3. Compatibility contract

- Existing invocations of `scripts/integrations/graphify_portfolio.py` continue
  to work with the same flags, dry-run default, `--execute --only` requirement,
  output-root checks, exit codes and 0.9.112 version check.
- The only observable additions are a `DEPRECATED` notice on stderr, the same
  text in `--help`, and `legacy`/`canonical` fields in JSON reports.
- No caller is silently redirected to a different binary, pin, schema or output
  directory.
- No implementation is removed; both test suites remain green.

## 4. Migration path (requires separate reviewed PR)

1. Inventory callers of the legacy CLI (`README.md`,
   `docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md`, local operators).
2. Map legacy `--root/--repo/--only/--out-root` usage to
   `scripts/graphify/multi_repo.py validate|run` with
   `assets/graphify/multi_repo_manifest.json` and explicit `--source-root` /
   `--index-root` paths.
3. Decide whether the repository-specific discovery behavior of the legacy
   script must be preserved as a documented adapter. If yes, port it behind the
   canonical API with tests; do not copy the 0.9.112 subprocess path.
4. Change README and rollout doc pointers only after the adapter parity check.
5. Deprecate, then remove, the legacy script in a later PR with an explicit
   rollback plan. Do not combine removal with pin or policy changes.
6. Keep P01/AI-9/Codex gates unchanged; offline graphs are not gate evidence.

## 5. Regression coverage

`tests/test_graphify_portfolio.py::CliTests::test_legacy_cli_identifies_canonical_implementation`
asserts that the legacy CLI identifies the canonical implementation in stderr,
`--help` and JSON output. It was verified red before the source fix, green
after, red after a temporary source revert, and green after restoration.

## 6. Non-goals

- No wheel-hash enforcement (F04) is added here; the canonical constant remains
  metadata until a reviewed installation-verification contract exists.
- No Graphify binary is installed, downloaded, uploaded or executed.
- No repository-wide extraction is regenerated or sent anywhere.
- No secret, cloud, deployment, approval or release gate is changed.

## 7. Rollback

See [`docs/runbooks/RECOVERY_AND_ROLLBACK.md`](../runbooks/RECOVERY_AND_ROLLBACK.md).
Reverting the single source/test commit restores the legacy CLI exactly; no
hosted state exists to restore.
