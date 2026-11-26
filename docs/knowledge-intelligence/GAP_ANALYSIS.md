# Capability gap analysis

**Evidence revision for every row:** 1fc88930a9e66a318009b92f38510907b1793b1a.
Line links are immutable GitHub links. A test proves its local fixture and
contract only; it does not prove a production deployment.

| Capability | Status | Evidence in source | What is established / missing |
| --- | --- | --- | --- |
| Knowledge management | PARTIAL | [Graphify design L1-L45](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/architecture/repository-intelligence.md#L1-L45); [incident memory L136-L173](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/incident_memory.py#L136-L173) | Local code/repository graph and bounded resolved-incident metadata memory exist. No general governed document library, content lifecycle, or unified query API was found. |
| Document ingestion | MISSING | [Bounded CI parser L44-L88](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/contracts.py#L44-L88); [event ingestion L1-L75](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/ai_intelligence/event_ingest.mjs#L1-L75) | Structured event ingestion and local JSONL are not document parsing, versioning, chunking, malware isolation, or retention-controlled corpus ingestion. |
| Embedding generation | MISSING | [Incident analyzer L50-L68](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/ai_intelligence/incident_analysis.mjs#L50-L68); [memory explicitly excludes embeddings](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/incident_memory.py#L1-L1) | Deterministic TF-IDF term vectors are temporary clustering features. No semantic model/library, model pin, or vector output contract exists. |
| Vector storage | MISSING | [Repository graph modules](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/architecture/repository-intelligence.md#L7-L17); [locked API dependencies](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/requirements-api.lock#L360-L420) | Existing stores cover tenant-scoped CI rows and local files/in-memory metadata. No vector extension, vector client, or persistent index was found. Hosted extension availability is UNKNOWN. |
| Hybrid retrieval | MISSING | [Exact-match incident retrieval L242-L290](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/incident_memory.py#L242-L290); [Graphify queries L47-L60](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/architecture/repository-intelligence.md#L47-L60) | Exact metadata filtering and code-graph queries exist. No lexical+dense retrieval, rank fusion, query analyzer, or citation-grounded answer path was found. |
| Agent memory | PARTIAL | [Incident memory contract](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/incident_memory.py#L136-L173); [provenanced retrieval](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/incident_memory.py#L249-L290) | Small local metadata memory retrieves exact-scope resolved incidents and optionally requires active signed curator approval. Durable persistence, semantic recall, cross-process replay protection, and accepted retention policy are missing. |
| Multi-agent coordination | PARTIAL | [Workflow contract](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/AI_MULTI_AGENT_WORKFLOW.md#L8-L27); [task conflict checks](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/check_two_agent_tasks.py#L274-L325) | Human-supervised task contracts and offline ownership checks exist. No live orchestration scheduler or agent runtime is proved; Codex runtime acceptance is OPEN. |
| Resource scheduling | MISSING | [Task manifest validator](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/check_two_agent_tasks.py#L274-L325); [AI core boundaries](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/AI_INTELLIGENCE_CORE.md#L12-L21) | Validator detects task conflicts; it does not allocate CPU/GPU, enforce fair queues, reserve memory, schedule embedding work, or start agents. Repository cron is not an AI resource scheduler. |
| Model evaluation | PARTIAL | [Offline evaluator](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/evaluation.py#L100-L150); [dataset limits](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/AI_EVALUATION_DATASETS.md#L1-L29) | Synthetic offline evaluation and integrity checks exist. No representative retrieval corpus, Recall@k baseline, citation evaluation, or approved natural-incident dataset exists; AI-9 is BLOCKED. |
| Agent observability | PARTIAL | [Local metric wrapper](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/otel_metrics.py#L1-L5); [opt-in gate](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/otel_metrics.py#L104-L122); [monitoring config](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/monitoring/compose.yml#L1-L75) | Local Prometheus/Grafana and optional request metrics exist. Agent traces, prompt/tool spans, hosted telemetry, operational SLOs, and telemetry-backed cost accounting are not established. |
| Cost management | PARTIAL | [AI review budget gate](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/.github/workflows/ai-code-review.yml#L25-L66); [free-resource checker](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/check_free_resource_plan.py) | A workflow opt-in gates an optional model call. It is not metering, a dollar cap, quota enforcement, or a guaranteed spending stop. |
| Data isolation | PARTIAL | [Offline tenant gate](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/tenant_scope.py#L66-L142); [PostgreSQL RLS](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/deploy/postgres/001_tenant_rls.sql#L31-L54) | Synthetic tenant authorization and RLS contracts exist. Trusted hosted identity, applied migration state, live tenant isolation, vector namespace controls and production adversarial tests are UNKNOWN/BLOCKED. |
| Human approval | PARTIAL | [Deterministic action policy](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/policy.py#L22-L35); [non-enterable approved state](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/state_machine.py#L9-L20) | High-impact execution is denied and proposals require review; durable identity-bound, action/SHA-scoped approval is not implemented. |
| Reliability and recovery | PARTIAL | [Incident memory limits](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/AI_INTELLIGENCE_INCIDENT_MEMORY_V1.md#L18-L25); [PostgreSQL fail-closed contract](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/scripts/devobs_intelligence/postgres_store.py#L81-L139); [local OTel limits](https://github.com/hamedonassar95/Devobs/blob/1fc88930a9e66a318009b92f38510907b1793b1a/docs/integrations/opentelemetry.md) | Local bounds, fail-closed behavior and runbooks exist. Durable index backups, restore tests, deletion propagation and recovery targets are not measured. |

## Verified, blocked and unknown boundaries

### VERIFIED

- Audited base is 1fc88930a9e66a318009b92f38510907b1793b1a.
- CI and CodeQL succeeded on that exact main SHA.
- Repository code includes the local components and controls listed above.
- No new vector or semantic-embedding package appears in inspected manifests.

### BLOCKED

- AI-9 quality acceptance is not closed by synthetic fixtures.
- Codex runtime acceptance remains OPEN in the last reconciled ledger.
- P01 managed staging remains NO-GO/BLOCKED in the last reconciled ledger.
- Production retrieval readiness requires trusted identity, tenant enforcement,
  retained-source controls, and a separate operational approval path.

### UNKNOWN

- Whether any hosted PostgreSQL instance is connected, which extensions it
  supports, or what backup/restore state it has.
- Whether an approved customer/business document corpus or retention obligation
  exists.
- Actual retrieval p95, memory/CPU consumption, model quality, storage footprint,
  hosted price, and cost-stop enforcement.
- Whether an external model/runtime integration is enabled outside this source.

Do not recast these unknowns as implemented capability.
