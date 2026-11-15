# Portfolio free-only integration candidates

**Status: REVIEW_ONLY / NOT_CONNECTED.** Devobs has an offline free-resource preflight at
[the baseline](../strategy/DEVOBS_FREE_RESOURCE_PLAN_2026.md). This second
preflight maps its existing *Devobs files* to six **candidate reviews** across
separately governed repositories; it does not activate any integration.

## Local execution

```sh
python3 scripts/check_free_resource_plan.py --json
python3 scripts/portfolio_free_readiness.py --json
python3 -m unittest discover -s tests -p 'test_portfolio_free_readiness.py' -v
```

The output is **MANIFEST_VALID_ONLY**. It verifies that all required local
Devobs files and candidate policy fields are intact. It never queries the
other six repositories and cannot prove ownership, authentication, CI health,
private data redaction, free billing, runtime suitability or production readiness.

| Project candidate | Existing Devobs resources to *consider*, not connected | Limits |
| --- | --- | --- |
| devobs-saas | CI, CloudEvents offline bridge, OTLP offline bridge | Tenant identity, logs and deployment remain separate |
| phone-repair-assistant-v2 | CI, CloudEvents offline bridge | No customer cases, photos, IMEIs or private diagnostics |
| al-dala-mobile | CI, CloudEvents offline bridge | No business/customer data or publishing |
| LiveOps-Integration | CI, CloudEvents offline bridge | No generation, media transfer or paid inference |
| DevObs-ai-Intelligence- | CI, CloudEvents offline bridge | Existing local console is not hosted AI proof |
| CineForge-AI | Offline CineForge Runner classifier | No private CI logs, Android source or Runner retries |

This list is not an access-control grant or a schedule. Paths refer to Devobs,
not to installed software in other projects. All connections, transfers and
runtime checks remain blocked pending *independent* source/destination owner
review and least-privilege scope validation.

[Offline integration acceptance](../integrations/PORTFOLIO_ACCEPTANCE.md) now
checks CloudEvents, Alertmanager and Grafana fixture ingestion/replay across all
seven existing namespaces, with separate temporary stores and public aggregate
results. This is tested converter behavior; the candidates remain NOT_CONNECTED.

## Safeguards and next gate

- Machine-readable candidates: `docs/portfolio/PORTFOLIO_FREE_CANDIDATES.json`.
- The validator rejects unknown projects/capabilities, duplicates, arbitrary
  resource expansion, any private data claim, and false claims that projects
  are already connected or production-ready.
- Reuse the existing [handoff preflight](../integrations/PROJECT_HANDOFF_PREFLIGHT.md)
  for any *future* review proposal; its limited allowed routes must not be
  broadened by this manifest. Its own REVIEW_ONLY outcome is not permission
  for transmission.
- The [2026-11-10 portfolio snapshot](PORTFOLIO_V1_READINESS.md) is historical;
  no new project's live SHA, CI status or hosted budget was checked here.
- Preserve P01 **NO-GO / BLOCKED**, AI-9 **BLOCKED**, Codex runtime **OPEN**.
  Never activate providers, create secrets, merge automatically, change main,
  or publish private details. Every merge needs explicit owner approval on
  the exact reviewed SHA under root [AGENTS.md](../../AGENTS.md).

References: [Devobs approved sources](../integrations/README.md),
[OpenTelemetry Collector](https://opentelemetry.io/docs/collector/),
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
