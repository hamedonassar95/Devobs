# Runbook — Open-Source Integration Readiness Check

Scope: **offline, read-only, advisory**. This runbook operates on a local versioned JSON catalog. It does not install packages, call hosted APIs, start Docker/Keycloak, restart services, merge, deploy, access secrets, or approve production changes. It cannot prove P01, AI-9, Codex runtime acceptance, hosted configuration, tenant isolation, or production telemetry.

A separate branch owns `docs/runbooks/INTEGRATION_READINESS.md`; that path was intentionally left untouched.

## 1. Inputs

- Engine: `devobs/integration_readiness/`
- Default fixture: `fixtures/integration_readiness/catalog.v1.json`
- Catalog schema: `devobs.integration_readiness.v1`, version `1`
- Architecture: [OPEN_SOURCE_INTEGRATIONS.md](../architecture/OPEN_SOURCE_INTEGRATIONS.md)
- OSS evidence: [OPEN_SOURCE_INTEGRATIONS_RESEARCH.md](../architecture/OPEN_SOURCE_INTEGRATIONS_RESEARCH.md)

The fixture is a declared inventory, not live discovery. Its `approval` records are synthetic fixture metadata for testing validation logic; they are not real owner approvals and grant no authority.

This check is distinct from the merged [Integration Control Plane](../architecture/INTEGRATION_CONTROL_PLANE.md) in `devobs/integration_control/`. That engine evaluates PR readiness and agent-task coordination snapshots; this one evaluates a static catalog of third-party integration versions, licenses, config key names, dependencies, tools, and security evidence. Neither grants merge or production authority.

## 2. Run the check

From the repository root:

```sh
python -m devobs.integration_readiness.cli --input fixtures/integration_readiness/catalog.v1.json --format json > readiness.json
python -m devobs.integration_readiness.cli --input fixtures/integration_readiness/catalog.v1.json --format markdown > readiness.md
```

On Windows PowerShell:

```powershell
python -m devobs.integration_readiness.cli --input fixtures/integration_readiness/catalog.v1.json --format json | Set-Content -Encoding utf8 readiness.json
python -m devobs.integration_readiness.cli --input fixtures/integration_readiness/catalog.v1.json --format markdown | Set-Content -Encoding utf8 readiness.md
```

The CLI writes a report to stdout and stable diagnostics to stderr. It never writes to the catalog or any service. `--allow-findings` forces exit code `0` for reporting-only use; it does not alter findings or decisions and must not be used as a release gate.

## 3. Interpret the result

| Decision | Meaning | Default exit code |
| --- | --- | --- |
| `READY_FOR_HUMAN_REVIEW` | No substantive findings. Still requires human review. | `0` |
| `NEEDS_EVIDENCE` | Missing or unverifiable non-blocking evidence. | `0` |
| `BLOCKED` | At least one P1 finding and no P0. | `1` |
| `NEEDS_APPROVAL` | Only approval-related P0 findings. | `1` |
| `POLICY_VIOLATION` | A non-approval P0 finding or fail-closed catalog error. | `1` |
| Loader diagnostic | Invalid path, malformed JSON, oversized input, unreadable file. | `2` |

The shipped fixture currently returns `POLICY_VIOLATION` with one P0 `UNSUPPORTED_LICENSE` finding for `terraform-cli` because the repository pins Terraform under `BUSL-1.1`. This is an intentionally surfaced policy conflict. Do not edit the fixture to hide it; obtain an owner-reviewed exception or migrate under a separate reviewed change.

Every report includes `human_review_required: true`, guardrails, diagnostics, and a SHA-256 `report_digest` over canonical decision data. Compare digests across runs to detect drift.

## 4. What is checked

- Inventory of declared integrations, owners, versions, paths, and config keys.
- Numeric version requirements using `==`, `!=`, `>=`, `<=`, `>`, and `<`.
- Missing configuration keys by name only; values are never inferred or exposed.
- Missing/unsupported dependencies, cycles, and SHA-256 integrity metadata for artifact dependencies.
- Duplicate path ownership by different owners.
- Blocked, deprecated, and out-of-support integrations.
- Secret-like config keys, command-like config fields, failed security evidence, and unavailable required tools.
- Human approval identity/date/scope checks; agents, bots, stale scopes, and invalid dates are rejected.
- Approved/restricted/unknown SPDX license classification.
- Unsafe paths, malformed JSON, oversized catalogs, and incompatible schemas fail closed.

## 5. Validation commands

Canonical local checks:

```sh
python -m compileall -q devobs
python -m unittest discover -s tests/integration_readiness -p "test_*.py" -v
python -m pytest -q tests/integration_readiness
python -m ruff check devobs/integration_readiness tests/integration_readiness
git diff --check
```

Repository conformance checks used in CI and/or by owner agreements:

```sh
python scripts/milestone_ledger.py --summary
python scripts/assess_change.py
python scripts/check_action_pins.py
python scripts/check_agent_spec.py
python scripts/validate_ai_eval_fixtures.py
python scripts/verify_gitleaks_coverage.py
```

Official syntax references: [Python `compileall`](https://docs.python.org/3/library/compileall.html), [Python `unittest` discovery](https://docs.python.org/3/library/unittest.html), [GitHub `gh pr create`](https://cli.github.com/manual/gh_pr_create). `pytest` and `ruff` are optional local tools; their absence must be reported as NOT RUN, never as a pass.

## 6. Evidence to attach to a PR

1. Exact source SHA and branch name.
2. Exact commands and final output lines, including NOT RUN checks with their error text.
3. Report digest and decision from both JSON and Markdown renderers.
4. `git diff --stat` and `git diff --check` result.
5. CI run URL after push, if available; do not claim hosted CI success before the run completes.
6. Explicit list of gates that remain blocked: P01, AI-9, Codex runtime acceptance, live integrations, production telemetry/SLOs.

## 7. Stop conditions

Stop and report BLOCKED if any of the following is requested: installing untrusted tools, generating or reading secrets, starting Keycloak or any container, calling hosted APIs, changing cloud/Render/PostgreSQL/Supabase configuration, enabling paid inference, merging, deploying, force-pushing, or changing release gates. The engine's advisory output is not authorization for any of those actions.
