# Repository audit

## Snapshot

| Field | Evidence |
| --- | --- |
| Repository | hamedonassar95/Devobs |
| Branch | feature/knowledge-intelligence-audit |
| Audited base | 1fc88930a9e66a318009b92f38510907b1793b1a (origin/main, fetched 2026-11-26) |
| Latest merge at base | PR #785; head 3f8c9c14936bb47cab388b5136daee041ca7d801; merge SHA equals audited base |
| Exact base CI | 45812551102 — SUCCESS |
| Exact base CodeQL | 45812549606 — SUCCESS |
| Last committed ledger | latest_pr 784; 314 merged milestones |
| Change scope | Documentation only |

The exact merge and check evidence is recorded in the
[source register](SOURCE_REGISTER.md). PR #785 merged after the committed
STATE.md/ledger checkpoint; the ledger was not advanced in this documentation
audit.

## Structure and implementation locations

The tracked tree contains 1,241 files at the audit SHA: 439 Markdown files,
365 Python files, 129 .mjs files, 59 JSON files, 58 .yml files, 50 .yaml files,
37 TSX files, and 31 TypeScript files. There are 371 Markdown files under docs/.
These counts describe the tree, not implementation completeness.

| Area | Paths | What is present |
| --- | --- | --- |
| AI intelligence and event handling | scripts/ai_intelligence/ | Bounded CI event ingestion, deterministic incident analysis, recommendations, anomaly detection, synthetic evaluation and reporting |
| Intelligence API contracts | scripts/devobs_intelligence/ | Evidence contracts, read-only collectors, deterministic policy, local tenant gate, PostgreSQL reader contract, incident memory, offline evaluation, OTel request metrics |
| Repository graph | tools/graphify/, scripts/graphify/ | Offline source graph extraction, query, impact and multi-repository reports |
| Console | apps/ai-intelligence-console/ | React/TypeScript UI, Node/Express development server, package manifests and two lock formats |
| Databases and policies | deploy/postgres/, deploy/postgres/supabase-acl/ | SQL schemas and RLS policies; no migration executed by this audit |
| Infrastructure | infra/terraform/, render.yaml, k8s/, deploy/ | Terraform, Render blueprint, Kubernetes manifests, PostgreSQL configuration and deployment documentation |
| Local observability | monitoring/ | Compose stack for Prometheus, Grafana, Alertmanager, optional Node Exporter and optional OTel Collector |
| Tests and fixtures | tests/, tests/fixtures/ | Python/Node contract tests, synthetic evaluation cases, emulator tests and local integration tests |
| Governance and plans | AGENTS.md, STATE.md, docs/MILESTONE_LEDGER.json, docs/, .agents/ | Human approval gates, offline task contracts, milestone records and runbooks |

## Runtime and dependency baseline

- GitHub CI validates Python 3.12 and 3.15; the reusable Python workflow
  defaults to 3.12. Python API dependencies are separately pinned and hashed in
  requirements-api.lock and requirements-dev.lock.
- GitHub CI uses Node.js 24. The console has package.json, package-lock.json,
  and bun.lock.
- requirements-performance*.lock files isolate optional benchmark tooling.
  They do not add those dependencies to production runtime requirements.
- Terraform provider versions are pinned in
  infra/terraform/.terraform.lock.hcl.
- The Firebase emulator suite has its own Node package and lockfile.
- No root pyproject.toml, root package.json, or root uv.lock was found. This
  does not infer package standards for nested applications.

No package was installed and no dependency file changed.

## CI and release controls

.github/workflows/ci.yml runs for pushes and pull requests and supports a
manually confirmed Pages production release. The workflow uses a Python
3.12/3.15 matrix and Node 24. Reusable language workflows support hash-checked
Python requirements. CodeQL is an independent repository check. Main CI and
CodeQL succeeded on the audited base SHA.

The existing AI Code Review workflow checks the explicit
DEVOBS_AI_BUDGET_APPROVED gate before checking for the provider secret or
executing a model review. This audit did not inspect repository variables or
secrets and did not activate or change the workflow.

The ordinary two-agent coordination contract validates branch/file ownership,
task dependencies, and pending-human approval states. It is a local validator;
it does not start agents, create a queue service, or dispatch work. Scheduled
GitHub workflows are repository maintenance/CI controls, not a tenant-aware AI
resource scheduler.

## Databases and storage abstractions

1. PostgresTenantStore accepts a supplied DSN, checks reader role, table
   privileges, RLS flags/policies, then exposes bounded status reads. This is a
   source-level runtime contract; it is not evidence that a live database was
   connected.
2. deploy/postgres/001_tenant_rls.sql and 002_service_registry.sql define
   tenant/project/member/service tables and forced RLS policies. They are
   checked-in SQL, not proof they were applied to a provider.
3. IncidentMemory is an immutable in-process tuple of metadata-only incident
   records with exact scope, freshness and optional signed curator approval.
   The approval replay registry is bounded process memory; durability across
   workers or restarts is not established.
4. AI event ingestion uses bounded local JSONL storage. It is not a document
   repository or vector index.
5. Graphify writes a local repository/code graph and reports file, link and
   dependency relationships. It is not a persistent business-knowledge store.
6. The Firebase console keeps Firebase disabled by default and the canonical
   Firestore rule is deny-all. Firebase is not a knowledge-storage candidate.
7. render.yaml is source evidence for a PostgreSQL 17 Free staging resource with
   a 2026-12-05 expiry. The existing owner decision is to allow natural expiry,
   with no deletion, upgrade, export, replacement or cost. It must not be used
   for this roadmap. Live rows, backup state and connectivity were not inspected.

No pgvector, Qdrant, ChromaDB, FAISS, Sentence Transformers, or MLflow runtime
dependency/configuration was found in the inspected manifests.

## AI, agent, evaluation and approval controls

- collectors.py uses fixed-origin bounded GET requests for one default-branch
  CI state; it does not dispatch or execute CI.
- policy.py deterministically allows narrowly scoped reads, marks code/PR work
  as proposal-only, and denies other actions.
- state_machine.py has no transition into APPROVED; OfflineTenantGate rejects
  execute.
- Incident memory has a signed curator-envelope path, but key enrollment,
  production identity, persistent replay prevention, and incident data rights
  are explicitly outside its contract.
- AI evaluation tooling uses synthetic or saved outputs without provider calls.
  The AI-9 corpus/gate remains blocked; no natural incident quality benchmark
  was run for this audit.
- Codex/OpenCode task configuration is instruction and work-planning metadata,
  not evidence of live multi-agent execution. AI budget settings and secrets
  were not inspected.

## Existing tests and checks relevant to this audit

Relevant test families include tests/test_intelligence_*.py,
tests/ai_evaluation/, tests/graphify/, tests/test_two_agent_tasks.py,
tests/test_otel_*, and tests/test_monitoring_config_contract.py. Exact commands
run for this documentation-only branch are recorded in the final report and PR.
A source test proves its local contract only; it does not prove hosted services
or retrieval quality.
