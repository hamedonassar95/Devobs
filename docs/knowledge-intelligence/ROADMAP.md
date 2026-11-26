# Implementation roadmap

**Plan only.** None of these milestones is implemented or authorized for
production. Work should remain local and use synthetic data until its acceptance
evidence is reviewed.

## Execution order

| Milestone | Objective | Dependencies | Responsible component |
| --- | --- | --- | --- |
| KI-0 | Freeze source admission, privacy and evidence contract | This audit; owner review of scope | Architecture/governance |
| KI-1 | Implement deterministic source/version/chunk contract | KI-0 | Offline ingestion adapter |
| KI-2 | Establish lexical retrieval baseline and frozen synthetic evaluation | KI-1 schema | Retrieval/evaluation |
| KI-3 | Evaluate one local embedding model behind a provider interface | KI-1 and KI-2 fixture | Embedding adapter |
| KI-4 | Evaluate local PostgreSQL/pgvector adapter and tenant RLS | KI-1 schema and synthetic DB tests | Storage adapter |
| KI-5 | Implement hybrid retrieval, citation checks and deletion semantics | KI-2, KI-3, KI-4 | Retrieval API |
| KI-6 | Add optional advisory-only agent/observability integration | KI-5 and all security/eval gates | Agent/operations |

KI-3 and KI-4 may run in parallel after KI-1's schema and KI-2's evaluation
fixture are frozen. They must own distinct files. KI-5 integrates the two
separate branches only after independent review; do not share writable worktrees.

## Common rules for every milestone

- Preserve existing Firebase-disabled behavior, deny-all Firestore rules,
  PostgreSQL read-only contracts, release workflows and gates.
- Do not use the expiring Render Free database or create a replacement cloud
  resource. No cloud activation or paid service is part of this roadmap.
- Synthetic fixtures only unless a separate data-source, rights, privacy and
  retention review expressly approves a corpus.
- Treat retrieved content as untrusted; no production action or tool call based
  solely on model output.
- Every milestone uses a feature branch, small reviewable commit, exact base/head
  SHA, test evidence and rollback instructions.
- The example paths and commands below are proposed future work, not files or
  commands that currently exist.

## Milestone specifications

### KI-0 — Source and trust contract

- **Objective:** Approve which public/local source types can be used, what
  provenance must be retained, and what content is excluded.
- **Reuse:** docs/AI_INTELLIGENCE_CORE.md, source event contract, current
  repository policy and local Graphify manifest.
- **Scope:** Document canonical source IDs, trusted-source admission, threat
  labels, secret/privacy exclusion, retention/deletion owner, limits and
  version fields. No data collection or import.
- **Owner:** Architecture/governance component.
- **Acceptance:** Every source class has owner, scope, permitted operation,
  revision format, data class and deletion rule; unknown sources fail closed.
- **Verification:** Review the decision matrix; run the repository docs and
  policy checks. No runtime benchmark.
- **Rollback:** Revert only the documentation commit; no runtime state changes.
- **Resources:** Existing workstation and repository only.
- **Human approval:** Owner approves source classes and purpose before any
  non-synthetic data is read.

### KI-1 — Deterministic ingestion contract

- **Objective:** Add a local parser contract for one approved synthetic source
  with immutable version and chunk provenance.
- **Reuse:** scripts/devobs_intelligence/contracts.py and existing bounded JSON
  parsing patterns.
- **Proposed files:** scripts/devobs_intelligence/knowledge/source_contract.py;
  tests/knowledge/test_source_contract.py; tests/fixtures/knowledge/source.json.
- **Scope:** Validate source identity, size, encoding, revision, content digest,
  parser version, retention class and stable chunk offsets. Reject unsupported
  input; never execute embedded content.
- **Dependencies:** KI-0.
- **Owner:** Offline ingestion adapter.
- **Acceptance:** Repeated same revision yields identical manifest/chunk IDs;
  changed content yields a new version; malformed, oversized and secret-marked
  fixtures fail closed; no external network or provider call.
- **Verification:** Proposed: python3 -m unittest tests.knowledge.test_source_contract -v;
  python3 -m compileall -q scripts/devobs_intelligence/knowledge tests/knowledge;
  git diff --check.
- **Rollback:** Remove the feature module/tests and keep the existing incident
  event pipeline unchanged.
- **Resources:** Synthetic files, CPU and disk bounded by explicit fixture size.
- **Human approval:** Required before admitting any source outside synthetic
  fixtures.

### KI-2 — Lexical baseline and frozen evaluation

- **Objective:** Measure a deterministic keyword/metadata retriever before
  adding semantic embeddings.
- **Reuse:** existing offline evaluation package, digest-pinned fixtures,
  duplicate-case rejection and CI validation.
- **Proposed files:** scripts/devobs_intelligence/knowledge/lexical.py;
  tests/knowledge/test_lexical.py; tests/fixtures/knowledge/retrieval-cases.jsonl;
  docs/knowledge-intelligence/evaluation-baseline.json.
- **Scope:** Build a small synthetic corpus with source-span labels; report
  Recall@10, MRR, latency, tenant-denial counts and citation-span correctness.
  No model calls.
- **Dependencies:** KI-1 schema frozen.
- **Owner:** Retrieval/evaluation component.
- **Acceptance:** At least 100 synthetic queries with fixed expected source IDs;
  evaluator is deterministic and cannot echo raw document contents; targets in
  ACCEPTANCE_CRITERIA.md are measured and reported, not assumed.
- **Verification:** Proposed: python3 -m unittest tests.knowledge.test_lexical -v;
  python3 scripts/validate_ai_eval_fixtures.py; git diff --check.
- **Rollback:** Remove the lexical index code and report; preserve source
  fixtures only if still useful to existing tests.
- **Resources:** Local CPU; fixture and index size explicitly bounded.
- **Human approval:** Owner reviews the synthetic test design; no real data
  collection is authorized.

### KI-3 — Optional local embedding adapter

- **Objective:** Compare one small CPU-capable model with the lexical baseline
  without changing runtime dependencies.
- **Reuse:** KI-1 source manifest and KI-2 frozen queries; existing
  performance/evaluation report pattern.
- **Proposed files:** scripts/devobs_intelligence/knowledge/embedding_adapter.py;
  tests/knowledge/test_embedding_adapter.py; separate optional lockfile and
  model provenance note.
- **Scope:** One selected model revision and tokenizer, local offline cache,
  explicit dimensions, deterministic output metadata, bounded batch/time/memory.
  No remote provider or production inference.
- **Dependencies:** KI-1 and KI-2; model license and artifact integrity review.
- **Owner:** Embedding adapter.
- **Acceptance:** Record exact model revision/hash, licensing source, dimensions,
  hardware, p50/p95 time, memory and retrieval change on the frozen fixture.
  If weights cannot be verified offline, report BLOCKED.
- **Verification:** Proposed: isolated venv, hash-verified lock install,
  python3 -m unittest tests.knowledge.test_embedding_adapter -v, and a bounded
  offline smoke run. Do not add this command to normal CI by default.
- **Rollback:** Remove optional adapter and lock; lexical retrieval remains
  available and no persistent data needs deletion.
- **Resources:** CPU-only test host target and disk budget must be specified
  before obtaining model files; do not download weights during this audit.
- **Human approval:** Owner review of model terms and local artifact handling
  before any download or installation.

### KI-4 — Local pgvector storage experiment

- **Objective:** Test a local, disposable pgvector schema under tenant RLS.
- **Reuse:** deploy/postgres RLS patterns, PostgresTenantStore read-only checks,
  PostgreSQL integration test harness and synthetic tenant fixtures.
- **Proposed files:** tests/knowledge/sql/001_local_vector_fixture.sql;
  scripts/devobs_intelligence/knowledge/postgres_adapter.py;
  tests/knowledge/test_postgres_adapter.py.
- **Scope:** Test-only local schema/table. Distinct writer/reader roles;
  forced RLS, source-version keys, tenant filters, delete/version operations,
  index rebuild, and backup/restore test. No migration to the existing database.
- **Dependencies:** KI-1 schema and KI-2 evaluation fixture; reviewed local
  PostgreSQL/pgvector image and artifact digests.
- **Owner:** Storage adapter and database security tests.
- **Acceptance:** Cross-tenant reads/writes/deletes all denied; same tenant
  allowed only for permitted roles; restore rebuilds the same manifest; no
  test uses Render, Firebase or Supabase.
- **Verification:** Proposed: a pinned local disposable Postgres container;
  python3 -m unittest tests.knowledge.test_postgres_adapter -v;
  python3 scripts/check_postgres_rls.py; git diff --check.
- **Rollback:** Remove local test container/volume created by the test and revert
  only the isolated experimental files. Never run database destruction against
  a shared or hosted resource.
- **Resources:** Local disk/CPU budget and container image must be pinned before
  implementation. No general sizing is known from this audit.
- **Human approval:** Review the local schema and role split before running
  containerized integration tests.

### KI-5 — Hybrid retrieval, citations and deletion

- **Objective:** Combine lexical and vector candidates behind stable adapters
  with tenant/source authorization and verifiable citations.
- **Reuse:** KI-2/KI-3/KI-4 adapters, incident-memory provenance patterns,
  deterministic policy and audit event contracts.
- **Proposed files:** scripts/devobs_intelligence/knowledge/retriever.py;
  tests/knowledge/test_hybrid_retrieval.py;
  tests/knowledge/test_deletion_contract.py.
- **Scope:** Fixed-rank fusion, deduplication across paths, freshness checks,
  source offsets and deletion from index/cache/derived artifacts. Read-only
  response API; no model generation or agent tool.
- **Dependencies:** KI-2, KI-3 and KI-4 pass their separate reviews.
- **Owner:** Retrieval API component.
- **Acceptance:** Proposed Recall@10/citation targets measured; cross-tenant
  denied; deletion test confirms all searchable copies are removed within the
  proposed target; stale citations are rejected.
- **Verification:** Proposed focused unittest, RLS suite, deterministic
  evaluation and git diff --check; inspect generated report for PII/secrets.
- **Rollback:** Disable the new retrieval adapter and return to the existing
  static/local APIs; delete only test-generated indexes/data.
- **Resources:** Bounded local test corpus, selected model and storage; no hosted
  service.
- **Human approval:** Review source rights, retention/deletion semantics and
  API authorization before integrating any application client.

### KI-6 — Advisory-only agent integration and operations

- **Objective:** Let existing agent consumers request cited evidence and
  produce a proposal without gaining write or scheduling authority.
- **Reuse:** current deterministic policy, task ownership validator, Codex
  human-review gates, OTel/Prometheus/Grafana local stack.
- **Proposed files:** an adapter under scripts/devobs_intelligence/knowledge/,
  focused tests, runbook and metrics allowlist. No deployment workflow change.
- **Scope:** Retrieval API read-only; output marked advisory; human approval
  remains external and mandatory. Add bounded local metrics for latency,
  abstention, source freshness, cache/index health, resource use and cost
  estimates—no prompt/document labels.
- **Dependencies:** KI-5, verified identity contract, reviewed budgets and
  successful security/evaluation evidence.
- **Owner:** Agent adapter and operations.
- **Acceptance:** Agent cannot broaden scope, modify storage, execute recovery,
  merge/deploy or call paid providers; audit event can correlate source/model/
  policy versions without content.
- **Verification:** Offline contract tests, security tests, local telemetry
  config tests and repository CI. Hosted identity/metrics remain separate
  acceptance gates.
- **Rollback:** Disable the adapter; keep retriever callable only in local
  tests; preserve existing agent and CI workflows.
- **Resources:** Existing local services only for initial tests; any paid or
  hosted requirement is outside this plan.
- **Human approval:** Required before connecting external agent runtimes, live
  identity, real customer corpus, paid inference, or production actions.

## Independent workstreams and file ownership

After KI-1 freezes the source/chunk schema and KI-2 freezes evaluation cases,
the local embedding experiment (KI-3) and isolated database/RLS experiment
(KI-4) can proceed independently. KI-3 owns only embedding adapter/model
provenance files; KI-4 owns only storage adapter/local SQL/test files. KI-5
owns the integration/retrieval files. Assign separate branches/worktrees and
do not let both workstreams edit shared contracts or evaluation fixtures.

## Rollback model

All milestones are additive local modules or documentation until a separately
reviewed API integration. A failed milestone can be reverted without touching
the existing event pipeline, production workflow, database, Firebase rules,
deployment settings, P01, AI-9, or Codex runtime gates. Delete only resources
created by its own isolated local test, as explicitly scoped in its runbook.
