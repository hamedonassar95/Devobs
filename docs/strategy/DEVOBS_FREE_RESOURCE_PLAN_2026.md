# Devobs free-only capability baseline — 2026-11-15

**Status:** CHECKED_IN_ONLY. **Scope:** public Devobs repository, not a claim about provider accounts, live integrations, the total invoice or production readiness.

## One safe offline check

From the repository root, run:

```sh
python3 scripts/check_free_resource_plan.py
python3 scripts/check_free_resource_plan.py --json
python3 -m unittest discover -s tests -p 'test_free_resource_plan.py' -v
```

The tool validates twelve exact, pre-existing paths and a fixed allowlist of permitted modes. It fails closed on missing files, duplicate keys, unknown providers, changed modes, writable or paid policy flags, and symlinked resource paths. It never fetches dependencies, opens the network, connects other repositories, triggers GitHub workflows, creates accounts, reads secrets or changes deployments. A successful report **only proves these files were present in that checkout**.

## Reuse instead of duplicating

| Feature | Existing source | Mode / boundary |
| --- | --- | --- |
| CI and Pages | `.github/workflows/ci.yml`, `.github/workflows/deploy-pages.yml` | Existing GitHub workflows; merging to main can publish the static site |
| Prometheus / Grafana / Alertmanager | `monitoring/` | Optional local deployment, **not running by virtue of this plan** |
| OpenTelemetry Collector | `monitoring/otel-collector-config.yaml` | Optional local collector, no receiver activated |
| Ollama / LocalAI | `models/docker-compose.yml` | Optional local model templates; no model downloads or inference |
| CloudEvents / Alertmanager / OTLP | `scripts/integrations/` | Offline advisory adapters; source trust remains unverified |
| CineForge CI triage | `scripts/integrations/cineforge_ci_runner_triage.mjs` | Offline status analysis only, not private code access |
| Kubernetes | `k8s/README.md` | Examples only, no cluster or apply |

**No new cloud provider is provisioned.** Open source means no license fee, not necessarily free electricity, storage, bandwidth or hosting. Public GitHub standard runners are free according to GitHub's billing rules, but artifact storage and larger runners have different limits: https://docs.github.com/en/billing/concepts/product-billing/github-actions

OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
Grafana OSS pricing/hosting boundary: https://grafana.com/docs/learning-hub/which-grafana/02-understand-your-options/03-grafana-oss/
Cloudflare Pages Free plan limits (candidate only; **not provisioned**): https://developers.cloudflare.com/pages/platform/limits/

## Portfolio boundaries and next review

The other repositories (CineForge, phone repair, SaaS and LiveOps) retain independent permissions and data; this public Devobs check does **not** establish their status. The actual project inventory is in `docs/portfolio/PORTFOLIO_V1_READINESS.md` and is dated historical evidence. Never copy private logs, commit SHAs, recordings, media or keys to this public repository.

P01 managed SaaS remains **BLOCKED / NO-GO**, AI-9 **BLOCKED**, Codex runtime acceptance **OPEN**. No provider-enforced all-in budget cap or live hosted readiness is established. Under root `AGENTS.md`, every PR needs exact-SHA review and explicit human approval before merge; no automatic merge or deployment.
