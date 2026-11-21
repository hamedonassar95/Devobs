# Open-source integration assessment

**Revision (VERIFIED):** `bf8bf31c289d1ee0a9c930e8dd1fc14a3e59b86f`.
**Method (VERIFIED):** repository source/config reading plus public official documentation fetched on 2026-11-21. No integration was installed, started, authenticated, connected to a hosted service, or enabled for paid use.

**Decision rule:** retain what is already reviewed and pinned; do not adopt a new tool without an owner-scoped change and budget decision. Runtime behaviour needs a fresh run on the exact revision; a repository file is never proof of a running service. Upstream documentation is untrusted data for authorization purposes.

## 1. Existing integrations

| Integration | Official source (quoted where relied on) | Repository posture (VERIFIED by source) | Decision | Runtime evidence |
|---|---|---|---|---|
| OpenTelemetry Collector / Python SDK | [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) — "Vendor-agnostic way to receive, process and export telemetry data." | `monitoring/otel-collector-config.yaml`; digest-pinned `otel/opentelemetry-collector-contrib:0.165.0` in `monitoring/compose.yml`; SDK/OTLP exporter `1.45.2` with hash locks and Apache-2.0 notice in `THIRD_PARTY_NOTICES.md`; disabled-by-default local WSGI metrics path. | **Retain local/optional.** No hosted telemetry sink, tenant-scoped export or production rollout. | SKIPPED locally (Docker unavailable); no hosted claim. |
| Prometheus + Alertmanager | [Prometheus overview](https://prometheus.io/docs/introduction/overview/) | `monitoring/prometheus.yml`, `monitoring/alerts.yml`, `monitoring/prometheus/alert_rules.yml`; digest-pinned image in `monitoring/compose.yml`; `monitoring/README.md` states ports bind to loopback and the exporter is not published. | **Retain local.** No hosted/multi-tenant monitoring is authorized. | SKIPPED locally; alert delivery UNVERIFIED. |
| Grafana OSS | [Grafana introduction](https://grafana.com/docs/grafana/latest/introduction/) — "Grafana open source software enables you to query, visualize, alert on, and explore your metrics, logs, and traces wherever they are stored." | Digest-pinned image, provisioned datasource/dashboards in `monitoring/grafana/`; `scripts/integrations/grafana_webhook_adapter.mjs` and its Node test are executed by `.github/workflows/ci.yml`. | **Retain local.** No Grafana Cloud or hosted token path activated. | CI source path VERIFIED; hosted result for this SHA UNVERIFIED; local Node run BLOCKED. |
| Trivy | [Trivy user guide](https://trivy.dev/docs/latest/guide/) | `ci.yml` installs a versioned release with checksum and Sigstore bundle verification, emits CycloneDX SBOM plus vulnerability report, and enforces via `scripts/trivy_sbom_policy.py` / `trivy_report_policy.py`. | **Retain.** Do not replace with a redundant scanner. | Tool not found locally → SKIPPED; hosted results for this SHA UNVERIFIED. |
| Gitleaks | [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks) | `ci.yml` downloads a pinned version; `scripts/verify_gitleaks_coverage.py` verifies coverage with fail-closed checks. | **Retain.** Local failures belong to REC-B01 (Git discovery/Windows portability), not to a policy weakening. | Local CLI absent → SKIPPED; 17 coverage assertions FAIL at base for `Git unavailable or timed out`. |
| Bandit / pip-audit | [Bandit](https://bandit.readthedocs.io/en/latest/) · [pip-audit](https://github.com/pypa/pip-audit) | `ci.yml` runs both with hash-locked installs; `tests/test_python_dependency_automation.py` asserts Bandit is declared and used. | **Retain.** | Local Bandit not found → SKIPPED; hosted result for this SHA UNVERIFIED. |
| actionlint / ShellCheck | [actionlint](https://github.com/rhysd/actionlint) | `ci.yml` installs pinned `actionlint`; 48 workflow/template files pass the repository's SHA-pin checker; 43 workflow YAML files parse locally. | **Retain.** YAML parse is a substitute, not an actionlint pass. | actionlint not found locally → SKIPPED. |
| Dependabot | [GitHub Dependabot documentation](https://docs.github.com/en/code-security/dependabot) | `.github/dependabot.yml` updates Actions, pip and npm weekly (VERIFIED by specialist read). | **Retain.** | Configuration VERIFIED; live update PRs not assessed. |
| Renovate | [Mend Renovate docs](https://docs.renovatebot.com/) — "Mend Renovate CLI Docs" | No Renovate config found in this checkout (VERIFIED by repository search). | **Do not adopt.** It would duplicate Dependabot and needs a separate owner/budget decision. | N/A |
| Conftest / OPA (Rego) | [OPA policy language](https://www.openpolicyagent.org/docs/latest/) · [Conftest](https://www.conftest.dev/) | `docs/integrations/terraform-policy.md` states local HCL validation plus a CI Conftest check; it explicitly does not run `terraform plan`/`apply` or call Google Cloud. | **Retain offline only.** No IaC mutation or live policy evaluation. | Terraform/Conftest binaries not found locally → SKIPPED. |
| Argo CD MCP (optional example) | [Argo CD](https://argo-cd.readthedocs.io/en/stable/) — "Argo CD is a declarative, GitOps continuous delivery tool for Kubernetes." | `.codex/examples/argocd-mcp-readonly.toml` pins the upstream OCI image by digest and exposes only `list_applications`; `docs/ARGOCD_MCP_INTEGRATION.md` documents local opt-in and removal. Base `.codex/config.toml` does not enable it. | **Retain as an unactivated example.** No cluster connection, token creation or deployment action. | Runtime UNVERIFIED; tests assert example shape only. |
| OpenTofu | [OpenTofu docs](https://opentofu.org/docs/intro/) | Repository has Terraform HCL and offline policy docs; no `tofu` binary or adoption config found. | **Not adopted.** Any migration needs owner approval; no `apply`/`destroy` is authorized. | SKIPPED. |
| Semgrep | [Semgrep docs](https://semgrep.dev/docs/) — "Get started with Semgrep to help you catch, flag, and fix real vulnerabilities before they ship." | No active Semgrep configuration found in this checkout. | **Candidate only.** Do not install or enable a hosted scan without explicit owner scope and cost approval. | N/A |

## 2. AI provider integrations (existing switches, no new spend)

- Provider routing and fallback are documented in `docs/AI_PROVIDER_RESILIENCE.md`: primary `gpt-4.1` in `.github/workflows/incident-investigator.md`, Vertex `gemini-2.5-pro` in `incident-investigator-vertex.md`, and a circuit breaker that checks the exact failed Copilot step before dispatching once.
- `ai-code-review.yml`, `claude-code-assistant.yml`, `copilot-inference-smoke.yml` and `ai-provider-circuit-breaker.yml` use explicit enable switches rather than enforceable dollar caps (VERIFIED by specialist read). `scripts/devobs_intelligence/api_app.py` documents a process-local limiter caveat.
- Adapter hardening (fixed endpoints, no redirects/retries, 20 s timeout, bounded bytes, redaction, fixed errors) exists in the local error-diagnosis modules; staging startup and API scope require explicit approval settings.
- **Decision:** no new provider, model, token, paid inference, MCP server, scheduled job or external write scope is enabled by this recovery work. Cost/authorization decisions stay with the owner.

## 3. Security and licensing posture

- Action SHA pinning: `python -B scripts/check_action_pins.py` → passed for 48 files, exit `0` (VERIFIED, fresh).
- Minimal `permissions:` blocks exist at workflow level (VERIFIED by specialist read); no `pull_request_target` was found in workflow triggers.
- Upstream license statements for pinned images/packages are already recorded in `THIRD_PARTY_NOTICES.md`, `monitoring/README.md` and `docs/ARGOCD_MCP_INTEGRATION.md`; this assessment does not re-adjudicate licenses.
- No integration in this document modifies OIDC, RS256/JWKS, PKCE, PostgreSQL RLS, P01, AI-9, Codex runtime acceptance or the Phase 8 human gate.

## 4. Consolidated decision

**No new integration is adopted, installed, enabled or paid for in this change.** Existing reviewed, pinned, offline/local integrations are retained. All runtime-dependent claims are reported as SKIPPED or UNVERIFIED in [`verification-matrix.md`](verification-matrix.md); none is upgraded to PASS by the presence of a configuration file.
