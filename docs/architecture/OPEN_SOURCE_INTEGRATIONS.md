# Open-Source Integration Readiness Engine — Architecture

Status: **offline, read-only, advisory**. This engine inventories declared integrations, checks explicit versioned compatibility requirements, and produces reproducible JSON/Markdown readiness reports. It does not install packages, call hosted APIs, start containers, restart services, merge pull requests, deploy, or approve production changes.

Starting revision: `4e1dc8f2c9c7a4caf896d7daf681b35be2e22937` (`origin/main` at task start). Rebased and reconciled onto `cfa1e17ee1575da90a0bb4fe30800c6df3b68668` (`origin/main`, PR #738) before handoff.

## 1. Verified repository baseline and gaps

| Finding | Classification | Evidence at starting revision |
| --- | --- | --- |
| Python 3.12/3.15 CI matrix and hash-locked dependencies | VERIFIED | `.github/workflows/ci.yml:60-78`, `requirements-api.lock` |
| Node 24 console build/test/audit | VERIFIED | `.github/workflows/ci.yml:247-268`, `apps/ai-intelligence-console/package.json` |
| CodeQL/Trivy/Gitleaks/Bandit/pip-audit/action-pin/agent-spec checks | VERIFIED | `.github/workflows/ci.yml:283-376`, `434-617` |
| Reusable Python CI compiles `scripts`, `tests`, `tools`, `devobs` and scans `devobs` with Bandit; already present in current main | VERIFIED | `.github/workflows/reusable-python-ci.yml:26-30,127-140`, `.github/workflows/ci.yml:75,345`, `tests/test_python_source_coverage.py:39-40` |
| Manual integration checklist exists but is not executable | VERIFIED | `docs/integrations/INTEGRATION_ACCEPTANCE_CHECKLIST.md:3-8` |
| No `devobs/integration_readiness`, `tests/integration_readiness`, or fixture catalog | VERIFIED | target-path scan at base SHA |
| No single offline catalog joining versions, ownership, config keys, dependencies, security evidence, and approvals | VERIFIED | reconnaissance across existing integration-control, incident, and CI contracts |
| Current main already contains `devobs/integration_control/` for PR/task coordination snapshots | VERIFIED | `origin/main` `cfa1e17ee1575da90a0bb4fe30800c6df3b68668`, `docs/architecture/INTEGRATION_CONTROL_PLANE.md` |
| P01, AI-9, and Codex runtime acceptance remain blocked/open | VERIFIED | `STATE.md:6`, `docs/DEVOBS_READINESS_CURRENT.md`, `docs/CODEX_AGENT_OPERATING_MODEL.md:36,55,57` |
| `docs/runbooks/INTEGRATION_READINESS.md` owned by another active branch | BLOCKED | `feature/integration-evidence-readiness` at `d9268debeb3311b7dc22c6a026a40248288ea372`; not modified here |
| Live hosted integrations and production telemetry | BLOCKED | `docs/INTEGRATION_WORKFLOW.md:11-21`, `docs/DATA_INTEGRATIONS.md:3-10`, `docs/MONITORING.md:3,33,35,45` |

## 2. Design boundaries

```text
local versioned JSON fixture
          |
          v
  catalog.normalize_catalog  -- bounded, schema-checked, no network
          |
          v
  evaluator.evaluate_catalog
     |-- compatibility.parse_spec / satisfies
     |-- security.redact_text / redact_value / safe_relative_path
     |-- classify_license / validate_approval
     |-- dependency graph + ownership conflict analysis
          |
          v
  stable report dict (schema_version 1, digest, guardrails)
          |
          +--> reporting.render_json_report
          +--> reporting.render_markdown_report
          +--> cli.main (read-only stdout/stderr, explicit exit codes)
```

The engine is a pure function of the supplied catalog. No clock, random source, environment secret, subprocess, socket, package installer, cloud SDK, or service client is used. `evaluation_date` and `scope_sha` are explicit fixture fields, which keeps results reproducible and prevents an approval from drifting across revisions.

### Boundary with the merged Integration Control Plane

PR #738 (`cfa1e17ee1575da90a0bb4fe30800c6df3b68668`) added `devobs/integration_control/`, a separate offline engine for PR readiness, agent-task ownership, branch-change detection, and coordination evidence. This readiness engine does **not** consume PR metadata, run agents, evaluate task manifests, or replace that control plane. Its input is a static catalog of third-party integration metadata: exact versions, SPDX licenses, declared config keys, artifact integrity, tool availability, and security evidence. The control plane answers “may this PR proceed to human review?”; this engine answers “is this declared OSS integration inventory internally consistent and policy-conformant?”. Both remain advisory and require human approval.

## 3. Components

| Module | Responsibility |
| --- | --- |
| `models.py` | Stable decisions, priorities, guardrails, limits, and `Finding` value object. |
| `catalog.py` | Bounded local JSON loading, structural validation, default fixture resolution. |
| `compatibility.py` | Offline numeric version parsing and bounded `==/!=/>=/<=/ >/<` requirement clauses. |
| `security.py` | Secret-key and command-field detection, recursive redaction, safe relative paths, SPDX policy, human-approval validation. |
| `evaluator.py` | Deterministic checks, dependency graph analysis, ownership conflicts, decision, digest. |
| `reporting.py` | Stable JSON and bounded Markdown renderers plus structured CLI diagnostics. |
| `cli.py` | `python -m devobs.integration_readiness.cli` entry point with no side effects. |

## 4. Reuse instead of duplication

- Reuses `scripts.ci_failure_intelligence.redact_secrets` rather than creating a competing redaction engine.
- Reuses the repository's `unittest` convention and `collections.abc.Mapping`/dataclass style from `devobs.incidents` and `devobs.incident_intelligence`.
- Reuses the existing `validate` CI gate and `python-tests` job; no duplicate scanning workflow was added. Current main already compiles/scans `devobs` and classifies `devobs/**/*.py` as Python source; this PR changes neither CI nor the classifier.
- Reuses existing pinned GitHub Actions in CI; no new action or unpinned tool was introduced.
- Complements rather than duplicates `devobs.integration_control`: the control plane evaluates PR/task coordination snapshots, while this engine evaluates a static OSS integration catalog. No PR readiness, agent coordination, CI failure intelligence, or incident intelligence logic was copied or modified.

## 5. Catalog contract (version 1)

Top level: `schema_version`, `profile`, `scope_sha`, `evaluation_date`, `component_versions`, `tool_availability`, `integrations`.

Each integration declares: `id`, `name`, `category`, `status`, `version`, `license`, `owner`, `owned_paths`, `required_config`, `config`, `requirements`, `dependencies`, `security_requirements`, `required_tools`, `evidence`, `deprecated`, `support_until`, `requires_human_approval`, `approval`, and optional `notes`.

Safety properties:

- Configuration values are never required for a check; only key presence is evaluated.
- Secret-like keys are reported by name and rendered as `[REDACTED]`; values are not echoed.
- Command-like keys (`command`, `cmd`, `exec`, `script`, `shell`, `run`) are rejected as untrusted fields and never executed.
- Paths must be repository-relative, normalized, and free of traversal, absolute drives, null bytes, and backslashes.
- A dependency with `artifact: true` requires a SHA-256 integrity record; a missing or invalid record blocks readiness.
- Human approval must contain a human identity, a valid date, and a `scope_sha` matching the reviewed catalog scope.

## 6. Decision model

| Condition | Decision | Exit code (without `--allow-findings`) |
| --- | --- | --- |
| Only P3 informational findings or none | `READY_FOR_HUMAN_REVIEW` | 0 |
| Any P2 finding and no P0/P1 | `NEEDS_EVIDENCE` | 0 |
| Any P1 finding and no P0 | `BLOCKED` | 1 |
| Only approval-related P0 findings | `NEEDS_APPROVAL` | 1 |
| Any other P0 finding | `POLICY_VIOLATION` | 1 |
| Malformed, oversized, or schema-incompatible catalog | `POLICY_VIOLATION` with `MALFORMED_CATALOG`/`INCOMPATIBLE_SCHEMA` | 2 for loader diagnostics, 1 for evaluator fail-closed report |

`READY_FOR_HUMAN_REVIEW` is not an approval and grants no merge, deploy, or production authority. `human_review_required` is always `true`.

The shipped fixture is intentionally not green: it records the existing Terraform `BUSL-1.1` pin, so the default report is `POLICY_VIOLATION` with `UNSUPPORTED_LICENSE` for `terraform-cli`. That is a verified integration defect/policy conflict, not a claim that CI is broken. The remediation plan is to obtain an owner-reviewed exception or migrate to an approved-license IaC tool under a separate change.

## 7. Report stability

Reports include `schema_version`, `report_schema`, `profile`, `scope_sha`, `evaluation_date`, `decision`, `human_review_required`, `summary`, `counts`, `findings`, `remediation_plan`, `integration_inventory`, `guardrails`, `diagnostics`, and `report_digest`. Findings and remediation items are sorted by priority, code, integration ID, and message. The digest is SHA-256 over the canonical decision, findings, inventory, profile, and scope SHA.

## 8. Security and concurrency posture

- Files under active ownership (`feature/xai-grok-api-adapter`, integration control/orchestration/verification/evidence work, blocked-task ownership guard, incident intelligence) were treated as read-only during discovery.
- No file in another worktree was read for content or modified. Only git branch/worktree metadata was inspected.
- The runbook was created at `docs/runbooks/OPEN_SOURCE_INTEGRATION_READINESS.md` because `docs/runbooks/INTEGRATION_READINESS.md` is owned by `feature/integration-evidence-readiness`.
- `README.md` was changed minimally to add a pointer and local commands; no CI file, action pin, permission, deployment path, or `devobs/integration_control` file was altered by this PR.
- No secret, token, credential, production environment, cloud project, hosted provider, Keycloak runtime, or paid inference was accessed.

## 9. Open-source selection summary

No candidate tool was installed. The engine itself uses only the Python 3.12 standard library plus the repository's existing redaction helper. The full 28-candidate evidence matrix, official source/license links, maintenance observations, cost caveats, and select/defer rationale are in [OPEN_SOURCE_INTEGRATIONS_RESEARCH.md](OPEN_SOURCE_INTEGRATIONS_RESEARCH.md).

| Candidate group | Disposition | Rationale |
| --- | --- | --- |
| Trivy, Gitleaks, Cosign, OPA/Conftest, Dependabot | Reuse (already present) | Existing pinned CI gates; no duplicate scanner or bot added. Cosign pin drift is recorded for separate owner review. |
| OpenTelemetry SDK, Prometheus, Grafana OSS | Reuse (existing scope) | Existing metrics/dashboards; no trace/log exporter, plugin, or network exposure change. |
| Terraform CLI | Reuse (validate only), restricted license | Existing non-destructive validation. `BUSL-1.1` is surfaced as a P0 finding until an owner exception or migration is approved. |
| Kubernetes manifests, PostgreSQL CI, Ollama config | Reuse (existing scope) | No cluster apply, hosted database, runtime test, model download, or paid inference. |
| Loki, Argo CD, Flux CD, Kyverno, FastAPI, LiteLLM, LangGraph, Redis | Defer | No verified executable gap; new service/control plane, blocked evidence, or open AI/P01 gates. |
| Semgrep CE, Syft, Grype, Renovate, OpenTofu, Kustomize, Helm | Defer | Existing CodeQL/Trivy/SBOM/dependency checks or direct manifests cover adjacent needs; no duplicate pipeline or migration approved. |

License classification is a deterministic policy filter, not legal advice or merge authority. Official docs links and residual unknowns are preserved in the research appendix.

## 10. Known limitations

- The fixture is a declared inventory, not proof that a hosted service is configured, reachable, or secure.
- License classification is a deterministic policy filter, not legal advice.
- P01, AI-9, Codex runtime acceptance, live telemetry, and hosted integrations remain blocked or unverified by this work.
- `scripts/assess_change.py` already classifies `devobs/**/*.py` as Python source in current main; this behavior is covered by a behavioral test, but the classifier is not modified here.
- CI execution for this branch is verified only after push; local checks do not prove hosted GitHub Actions results.
