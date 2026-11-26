# Source register

**Audit date:** 2026-11-26
**Repository evidence SHA:** 1fc88930a9e66a318009b92f38510907b1793b1a

## Repository provenance and evidence rules

origin/main was fetched and verified at the SHA above. GitHub reports PR #785
(feature/pyperformance-suite-expansion) merged at that exact SHA on
2026-11-26T11:39:24Z. Its exact head was
3f8c9c14936bb47cab388b5136daee041ca7d801. The PR's CI and CodeQL checks
completed successfully; required Python 3.12/3.15, Node, security, RLS,
container, Terraform, site-contract, and validation checks succeeded. Production
release and controlled incident-drill jobs were skipped by policy.

On the exact audited main SHA, GitHub reports main CI run
[45812551102](https://github.com/hamedonassar95/Devobs/actions/runs/45812551102)
and CodeQL run
[45812549606](https://github.com/hamedonassar95/Devobs/actions/runs/45812549606)
as successful. Incident Response run 45895490736 was skipped. This establishes
repository checks at the base, not runtime readiness.

The local ledger summary reports 314 merged milestones and latest_pr 784.
STATE.md begins with PR #784 at main SHA
03f2ddfa564092d9cab1dfc5c9a0a008e9761a20; it does not record the later #785
merge. This inconsistency is verified and treated as a stale documentation
checkpoint. No count, status, or gate is silently advanced in this audit. P01
BLOCKED/NO-GO, AI-9 BLOCKED, and Codex runtime OPEN are last-recorded ledger
statuses, not fresh hosted evidence.

All code links below point to the immutable audited commit. Source code proves
what is implemented in the repository; it does not prove deployment,
connectivity, customer use, or service health. Local test commands prove only
their checked-in contract.

## Internal evidence index

| ID | Immutable source and lines | What it establishes | Limit |
| --- | --- | --- | --- |
| R1 | [Repository tree](https://github.com/hamedonassar95/Devobs/tree/1fc88930a9e66a318009b92f38510907b1793b1a) | Tracked repository at the audit SHA | Not a deployed filesystem |
| R2 | [AI Intelligence Core L1-L31](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/AI_INTELLIGENCE_CORE.md#L1-L31) | Offline event contracts, read-only CI collection, deterministic policy, disabled approval transition | Historic doc; no hosted API or live provider proof |
| R3 | [Incident analyzer L1-L80](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/ai_intelligence/incident_analysis.mjs#L1-L80) and [clustering L145-L190](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/ai_intelligence/incident_analysis.mjs#L145-L190) | Bounded deterministic token/TF-IDF cosine grouping | Temporary clustering features, not semantic embeddings or persistent index |
| R4 | [Incident memory L136-L173](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/incident_memory.py#L136-L173) and [retrieval L232-L290](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/incident_memory.py#L232-L290) | In-memory metadata-only records, duplicate rejection, exact scope, freshness and optional signed curator provenance | No general document store, embedding search, retention service, or cross-process replay store |
| R5 | [Offline tenant gate L1-L5](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/tenant_scope.py#L1-L5) and [authorization L66-L142](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/tenant_scope.py#L66-L142) | Synthetic/offline tenant and project checks; writes denied | Trusted identity middleware intentionally excluded |
| R6 | [Approval state machine L1-L42](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/state_machine.py#L1-L42) and [policy L1-L35](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/policy.py#L1-L35) | Advice cannot grant authority; APPROVED has no enabled transition; execution denied | No deployed human-approval service |
| R7 | [PostgreSQL tenant store L51-L139](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/postgres_store.py#L51-L139) and [read paths L141-L220](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/postgres_store.py#L141-L220) | Strict read-only role and RLS/schema contract for three Devobs tables | No live database connection or vector extension proven |
| R8 | [Tenant RLS SQL L1-L54](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/deploy/postgres/001_tenant_rls.sql#L1-L54) and [service RLS SQL L1-L35](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/deploy/postgres/002_service_registry.sql#L1-L35) | Tracked schemas enforce tenant-scoped read policy and forced RLS | SQL source only; migrations were not applied |
| R9 | [Offline evaluator L1-L30](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/evaluation.py#L1-L30) and [scoring contract L100-L150](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/evaluation.py#L100-L150) | Bounded offline case evaluation without provider calls | Existing fixture results do not measure knowledge retrieval |
| R10 | [Task validator L1-L48](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/check_two_agent_tasks.py#L1-L48) and [conflict/approval checks L274-L325](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/check_two_agent_tasks.py#L274-L325) | Offline ownership and conflict validation, no authority | Does not start agents or schedule work |
| R11 | [Local metric wrapper L1-L5](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/otel_metrics.py#L1-L5) and [opt-in L104-L122](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/otel_metrics.py#L104-L122) | Optional local request-duration metric only; off by default | No hosted telemetry, agent spans, SLO proof, or cost accounting |
| R12 | [Graphify architecture L1-L45](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/architecture/repository-intelligence.md#L1-L45) | Local repository/code graph and documentation link graph | Not general document retrieval or vector storage |
| R13 | [Monitoring Compose L1-L75](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/monitoring/compose.yml#L1-L75) and [OTel integration](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/integrations/opentelemetry.md) | Existing local monitoring stack and resource/privacy bounds | No hosted service is proved active |
| R14 | [CI Python matrix L65-L80](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/.github/workflows/ci.yml#L65-L80) and [Node setup L248-L260](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/.github/workflows/ci.yml#L248-L260) | Python 3.12/3.15 and Node 24 CI toolchains | Hosted CI availability is GitHub-controlled |
| R15 | [API dependency lock L360-L420](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/requirements-api.lock#L360-L420) and [monitoring images](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/monitoring/compose.yml#L1-L75) | Existing OTel/psycopg pins and digest-pinned monitoring services | No proposed embedding/vector package included |
| R16 | [Render blueprint L1-L33](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/render.yaml#L1-L33) and [P01 expiry decision](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/p01/RENDER_FREE_DB_EXPIRY_DECISION_2026-11-24.md) | Source declares a Free PostgreSQL 17 resource and owner decision to let it expire naturally | No connection, rows, backups, or hosted state inspected; not a storage target |
| R17 | [STATE checkpoint L1-L8](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/STATE.md#L1-L8) and [ledger head](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/MILESTONE_LEDGER.json#L1-L16) | Last committed gate and ledger checkpoint | Records PR #784, not later PR #785; stale after audited merge |

## External technical sources

Versions below were checked on 2026-11-26 using official project release pages
or package metadata. They are comparison snapshots only, not install requests
or dependency choices. Latest means the latest non-prerelease value observed
on the linked source; it is not a support-life guarantee.

| Technology | Official source |
| --- | --- |
| PostgreSQL + pgvector | [pgvector README](https://github.com/pgvector/pgvector), [changelog/version 0.8.7](https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md), [package metadata/license](https://github.com/pgvector/pgvector/blob/master/META.json), [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) |
| Qdrant | [releases](https://github.com/qdrant/qdrant/releases), [multitenancy](https://qdrant.tech/documentation/manage-data/multitenancy/), [security](https://qdrant.tech/documentation/security/), [snapshots](https://qdrant.tech/documentation/snapshots/), [license](https://github.com/qdrant/qdrant/blob/master/LICENSE) |
| ChromaDB | [releases](https://github.com/chroma-core/chroma/releases), [docs](https://docs.trychroma.com/), [persistence/security usage](https://github.com/chroma-core/docs/blob/main/docs/usage-guide.md), [resources](https://cookbook.chromadb.dev/core/resources/), [license](https://github.com/chroma-core/chroma/blob/main/LICENSE) |
| FAISS | [project README](https://github.com/facebookresearch/faiss), [install/platform notes](https://github.com/facebookresearch/faiss/blob/main/INSTALL.md), [docs](https://faiss.ai/), [license](https://github.com/facebookresearch/faiss/blob/main/LICENSE) |
| Sentence Transformers | [docs](https://www.sbert.net/), [install requirements](https://www.sbert.net/docs/installation.html), [inference efficiency](https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html), [PyPI](https://pypi.org/project/sentence-transformers/), [license](https://github.com/huggingface/sentence-transformers/blob/main/LICENSE) |
| MLflow | [release notes](https://mlflow.org/releases/), [tracking server](https://mlflow.org/docs/latest/tracking/server/), [tracking stores](https://mlflow.org/docs/latest/tracking/), [license](https://github.com/mlflow/mlflow/blob/master/LICENSE) |
| OpenTelemetry | [docs](https://opentelemetry.io/docs/), [Collector](https://opentelemetry.io/docs/collector/), [Python releases](https://github.com/open-telemetry/opentelemetry-python/releases), [license](https://github.com/open-telemetry/opentelemetry-python/blob/main/LICENSE) |
| Prometheus | [overview](https://prometheus.io/docs/introduction/overview/), [storage](https://prometheus.io/docs/prometheus/latest/storage/), [release downloads](https://prometheus.io/download/), [license](https://github.com/prometheus/prometheus/blob/main/LICENSE) |
| Grafana | [stable download](https://grafana.com/grafana/download), [release history](https://github.com/grafana/grafana/releases), [upgrade support](https://grafana.com/docs/grafana/latest/upgrade-guide/when-to-upgrade/), [license](https://github.com/grafana/grafana/blob/main/LICENSE) |

## Bibliographic reference register

Purchased or gated material is not reproduced or treated as evidence. The
engineering requirements in this audit are independently written from source
code, official public documentation, and security constraints.

| Requested reference | Verified metadata | Access/content status |
| --- | --- | --- |
| Introducing MLOps — Bookey summary | Underlying O'Reilly title: Introducing MLOps; Mark Treveil, Nicolas Omont, Clément Stenac, Kenji Lefevre, Du Phan, Joachim Zentici, Adrien Lavoillotte, Makoto Miyazaki, Lynn Heidmann; 1st ed., 2020; ISBN 9781492083290. [Publisher](https://www.oreilly.com/library/view/introducing-mlops/9781492083283/), [Bookey page](https://www.bookey.app/book/introducing-mlops) | Public catalog/summary metadata only. Full book not accessed; summary content not used as a requirement. |
| Canonical MLOps Advisory Services | Exact requested title not independently verified. Canonical's [MLOps page](https://canonical.com/mlops) lists MLOps Consulting and Managed MLOps. | Exact service/package name, terms, price, availability UNVERIFIED. No contact or purchase. |
| Canonical — A Guide to MLOps | Canonical's [MLOps page](https://canonical.com/mlops) identifies a Guide to MLOps whitepaper. | Title/publisher visible. Named author, publication date, ISBN, edition, and full-text access UNVERIFIED. |
| Vector Databases: A Technical Primer | TGE Data Labs document metadata identifies Jide Ogunjobi and December 2023: [source metadata](https://tge-data-web.nyc3.digitaloceanspaces.com/docs/Vector%20Databases%20-%20A%20Technical%20Primer.pdf). | Metadata only; no copy/download or reliance on full text. |
| Vector Databases Cookbook | Closest exact primary source found is OpenAI Cookbook's [Vector Databases examples index](https://github.com/openai/openai-cookbook/blob/main/examples/vector_databases/README.md). | The requested wording is not a verified bibliographic title. Author/editor, date, edition, ISBN UNVERIFIED. Code examples are not a neutral benchmark. |
| Vector Databases for RAG | Phrase does not uniquely identify a publication. A different nearby title is Actian/O'Reilly's Vector Databases for Enterprise AI, by Emma McGrattan: [official report page](https://www.actian.com/lp/vector-databases-for-enterprise-ai-report/). | Do not substitute the different title. Exact requested title, edition, ISBN UNVERIFIED; no full text copied or used. |
