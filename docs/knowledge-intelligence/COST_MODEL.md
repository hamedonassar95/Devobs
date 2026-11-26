# Cost model

## Phase 01 actual cost

This audit creates documentation only. It installs no software, downloads no
model weights, starts no hosted service, and runs no paid inference. New service
and model spending for this phase is therefore **$0**. That does not estimate
the existing repository's total costs or staff time.

## Future local evaluation

If an owner later approves an isolated local prototype, its marginal provider
bill can remain $0 by using already-owned hardware and OSS software. This is
conditional: electricity, storage wear, developer time, download bandwidth and
hardware ownership are not measured. No database instance is supplied or
authorized by this plan; do not use the expiring Render Free database.

The free software license does not make operations cost-free. A local index
uses RAM, CPU, and disk; backups, restore drills, model verification, dependency
maintenance, security review, and deletion audits use engineering time.

## Cost dimensions for a later estimate

Use a transparent monthly model only after corpus and deployment scope are
approved:

~~~text
monthly total =
  application and worker compute
  + database/vector storage and index overhead
  + backup storage and restore-test capacity
  + embedding inference (local compute or provider requests)
  + model artifact storage and transfer
  + telemetry storage, cardinality and retention
  + network egress and authentication
  + support/license charges
  + human operation and incident response
~~~

For local sizing, start with:

- Raw vector payload = number of chunks × dimensions × bytes per component.
- Add vector index overhead, metadata, PostgreSQL/SQLite pages, write-ahead
  logs, caches, temporary build memory and backup copies.
- Embedding cost is model-specific: record tokens/chunks, batch throughput,
  CPU/GPU, model version, restart/cache behavior and reindex frequency.
- Observability cost grows with samples/spans, cardinality, retention, and
  exported attributes. Keep labels bounded and never use tenant or document text
  as metric dimensions.

These formulas are not capacity estimates. The actual corpus size, embedding
model, concurrency, availability, region, storage price, backup retention and
egress are unknown.

## Free versus paid dependencies

| Item | Cost treatment |
| --- | --- |
| PostgreSQL, pgvector, Qdrant, ChromaDB, FAISS, Sentence Transformers, MLflow, OpenTelemetry, Prometheus, Grafana OSS | Upstream software licenses are open-source as listed in the technology matrix. Legal review of license obligations, plugins, models and redistribution still applies. |
| Sentence-transformer model weights | Model-specific license and distribution conditions; no model selected. Model availability/download is not included in this phase. |
| Existing local CI and local monitoring | Reuse current configured tools; this audit adds no workflow or resource. Existing account costs are not assessed. |
| Managed databases, vector services, hosted MLflow, hosted observability, external embedding or LLM APIs | Paid/usage-based possibilities; no quote, account, service, or payment was activated or evaluated. |
| This documentation audit | $0 new infrastructure, dependency installation, or inference spend. Labor and existing platform charges are outside this figure. |

## Cost controls required before future activation

Keep remote models, cloud vector services, database writes and hosted tracing
disabled by default. Require explicit provider selection, request/token/job
budgets, bounded retries, timeout and cancellation, sanitized usage records,
and an independent human approval before any paid inference or production
change. A workflow boolean is not a verified dollar cap. The existing P01
managed-service gate remains blocked; this document does not change it.

Before presenting a dollar estimate, disclose workload assumptions and request
provider-specific public pricing for the intended region and storage tier. No
price is invented here.
