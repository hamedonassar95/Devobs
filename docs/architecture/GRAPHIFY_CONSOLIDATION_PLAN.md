# Graphify consolidation plan — F01b completion — 2026-11-20

**Status:** F01b code consolidation COMPLETE on the reviewed branch; no merge,
deployment, gate promotion or legacy deletion.
**Base revision:** `41353d1451524492d6ca6e3ae8bb1b7d12c87b45` (`origin/main`, PR
#725 merge commit, VERIFIED).
**Implementation commits:** `b95ac86`, `01b980d`, `1bbccc9`, `2df481b`,
`c19e4a0`, `ed55a06`.

This document supersedes the F01a designation record. F01a made `tools/graphify`
canonical without moving code. F01b performs the bounded code consolidation while
preserving the legacy entrypoint as a compatibility adapter.

## 1. Architecture after consolidation

| Role | Path | Pin / policy | Status |
| --- | --- | --- | --- |
| **Canonical implementation** | `tools/graphify/` | `graphifyy` 0.9.113; `devobs-repository-intelligence-v1`; approved wheel SHA-256 `62f8483e536c9200f93665f9c61df6489436ab087432e0a0a738bd88096e0491` | Sole implementation for new work. |
| Public canonical CLIs | `scripts/graphify/multi_repo.py`, `scripts/graphify/repository_intelligence.py` | Thin shims importing `tools.graphify.*` | Supported. |
| Legacy compatibility adapter | `scripts/integrations/graphify_portfolio.py` | Preserves `devobs-graphify-portfolio-v1` and the 0.9.112 behavioral check | Backward-compatible; contains no orchestration or subprocess implementation. |
| Canonical compatibility modules | `tools/graphify/portfolio.py`, `tools/graphify/portfolio_execution.py` | Explicit legacy/canonical contracts | New home of all moved discovery, planning, execution and CLI behavior. |
| Supply-chain verifier | `tools/graphify/supply_chain.py` | Fails closed unless the digest is a full 64-hex SHA-256 | Local verification only; no download or install. |

`scripts/graphify/` is not a third implementation: both files add the repository
root to `sys.path` and import `tools.graphify.*`.

## 2. Compatibility contract

The legacy adapter preserves the exact observable contract asserted by
`tests/test_graphify_portfolio.py`:

- same flags: `--root`, `--repo`, `--out-root`, `--only`, `--graphify`,
  `--timeout`, `--execute`, `--json`;
- dry-run default and `--execute --only` authorization;
- output-root/source-overlap refusal and no-overwrite behavior;
- read-only fixed Git argv allowlist;
- exact `graphify extract <path> --code-only --out <dir>` argv;
- 0.9.112 version gate and mismatch message;
- exit codes `0` dry-run/success, `2` preflight refusal, `3` failed run;
- deprecation notice on stderr, in `--help` and in JSON report metadata;
- report and `run.json` field names, absolute-path evidence, and
  `network_egress_verification: "not_verified"`.

The legacy 0.9.112 pin is retained **only** as this compatibility contract. It is
not a second implementation and is not recommended for new work. The canonical
pointer in every legacy report identifies `tools/graphify`, CLI
`scripts/graphify/multi_repo.py` and pin 0.9.113.

## 3. What changed

1. Added `tools/graphify/portfolio.py`: policy contracts, repository discovery,
   remote parsing, eligibility and plan construction.
2. Added `tools/graphify/portfolio_execution.py`: offline environment, version
   gate, fixed-argv extraction, run evidence and CLI.
3. Replaced `scripts/integrations/graphify_portfolio.py` with a thin re-export
   adapter. No legacy file was deleted.
4. Added `tests/graphify/test_portfolio.py` for canonical contract parity and
   one adapter-delegation test in `tests/test_graphify_portfolio.py`.
5. Added `tools/graphify/supply_chain.py` and the `verify-wheel` subcommand to
   fail closed on truncated, mismatched or missing local wheel artifacts.

No CLI flag was removed, no indexed data was deleted, no source tree was
extracted, and no Graphify binary was installed, downloaded or executed during
this change.

## 4. Supply-chain boundary

`PINNED_WHEEL_SHA256` was metadata before this change. It is now checked by
`verify_wheel_sha256()` against a local file using a complete 64-character
lowercase hexadecimal digest and constant-time comparison. A truncated pin,
missing wheel or mismatch returns exit code `2` with `FAIL <reason>` and no
report payload.

```powershell
python scripts/graphify/repository_intelligence.py verify-wheel --wheel <local-wheel>
python -B -m unittest tests.graphify.test_supply_chain -v
```

This does **not** install or download anything. The external operator install
step remains outside repository automation; its provenance is therefore
UNVERIFIED in this audit. The normal `build`/`run` commands still enforce the
0.9.113 version string; they do not accept an arbitrary local wheel path.

## 5. Verification

```powershell
python -B -m unittest discover -s tests/graphify -v
python -B -m unittest tests.test_graphify_portfolio -v
python -B -m unittest tests.test_python_source_coverage tests.test_node_pipeline_selection tests.test_python_dependency_automation -v
python -B -m compileall -q tools/graphify scripts/graphify scripts/integrations/graphify_portfolio.py
python scripts/check_action_pins.py
git diff --check
```

See [`docs/audits/DEVOBS_GRAPHIFY_UNIFICATION_AUDIT.md`](../audits/DEVOBS_GRAPHIFY_UNIFICATION_AUDIT.md)
for exact output, Windows classification, unresolved findings and owner gates.

## 6. Non-goals

- No legacy deletion, policy merge, pin promotion or schema unification.
- No change to `assets/graphify/multi_repo_manifest.json` or existing indexes.
- No change to P01, AI-9 or Codex runtime acceptance gates.
- No hosted CI assertion, merge, deployment, cloud write, secret or permission
  change, paid inference or external upload.

## 7. Rollback

See [`docs/runbooks/GRAPHIFY_ROLLBACK.md`](../runbooks/GRAPHIFY_ROLLBACK.md).
Reverting the five implementation commits restores the previous F01a state; no
hosted state or indexed data must be restored.
