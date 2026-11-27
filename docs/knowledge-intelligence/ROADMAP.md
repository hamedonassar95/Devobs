# Knowledge Intelligence implementation roadmap

**Baseline checked:** 2026-11-27, `origin/main` at
`442012702a60ebf1bb1df43c4aa9e08fb94cab03`.
**Current work:** KI-2 deterministic local ingestion on
`feature/ki-2-knowledge-ingestion`, pending review. This plan does not authorize
production data, cloud resources, paid services, or deployment.

## Evidence status

- **KI-0 — MERGED:** PR #787, head
  `5bc957b8a4fa101f75b03bb620ae2c0d0165254b`, merge
  `fc6ea340206bb970169a3b1c182fbe83f3a0803f`. Its local validator checks
  declared policy structure; it does not authenticate approval or tenant scope.
- **KI-1 — MERGED:** PR #788, head
  `971e6e464917a86fcc840692f897fd7996d5afed`, merge
  `442012702a60ebf1bb1df43c4aa9e08fb94cab03`. Exact-head CI `45926972145`,
  exact-head CodeQL check `140270646681`, and post-merge main CI `45929601744`
  succeeded. KI-1 v1 is limited to synthetic metadata, a 65,536-byte document
  ceiling, 500 versions, 5,000 manifest chunks and non-overlapping chunk spans.
- **KI-2 — IMPLEMENTED LOCALLY, REVIEW PENDING:** converts explicit synthetic
  UTF-8 input to a KI-1 manifest, in-memory only. Its detailed behavior and
  measured smoke benchmark are in [INGESTION_ENGINE.md](INGESTION_ENGINE.md).
- **P01:** BLOCKED / NO-GO. **AI-9:** BLOCKED. **Codex runtime:** OPEN. None of
  these statuses are changed by knowledge-intelligence work.

## Dependency order

| Milestone | Objective | Depends on | State / owner |
| --- | --- | --- | --- |
| KI-0 | Versioned source-admission, privacy and provenance policy | Architecture audit | Merged; governance |
| KI-1 | Deterministic source, document-version and chunk manifest | KI-0 | Merged; schema/validator |
| KI-2 | Bounded synthetic UTF-8 ingestion into validated KI-1 manifests | KI-0 + KI-1 | Current branch; ingestion engine |
| KI-3 | Deterministic lexical retrieval with frozen synthetic evaluation | KI-1 + KI-2 review | Next; retrieval/evaluation |
| KI-4 | Evaluate optional local embedding adapter against KI-3 | KI-3 fixture + model/license review | Planned; embedding adapter |
| KI-5 | Isolated local storage/RLS experiment with synthetic data | KI-1 + KI-3 contracts | Planned; storage adapter |
| KI-6 | Hybrid retrieval, citation validation and deletion contract | KI-3, KI-4, KI-5 | Planned; retrieval API |
| KI-7 | Advisory-only agent/observability integration | KI-6 + identity/evaluation gates | Planned; agent/operations |

## KI-2 — Deterministic local ingestion

- **Objective:** turn one explicitly supplied, synthetic UTF-8 document into a
  structurally valid KI-1 manifest without saving the document or calling a
  network service.
- **Reuse:** KI-0 `validate_policy`; KI-1 `deterministic_id`, canonical
  serialization, manifest schema and validator. No competing policy or
  manifest subsystem is introduced.
- **Scope:** strict UTF-8 and content-type checks; byte-accurate chunk hashes and
  offsets; bounded input; in-memory idempotency, version chain, revocation and
  deletion; sanitized JSON result; manual benchmark. The CLI is not a runtime
  API.
- **Known contract constraints:** 65,536-byte maximum document inherited from
  KI-1; KI-1 disallows overlap, so KI-2 requires `overlap_bytes=0`; manifests
  accept at most 500 versions/5,000 chunks and the engine caps chunks at 2,048.
  KI-3 must not bypass these limits. If larger documents or overlap are needed,
  review a new manifest schema version first.
- **Acceptance:** local tests verify Arabic/English UTF-8, stable identifiers,
  hashes, spans, KI-0/KI-1 validation, bounded inputs, fail-closed lifecycle,
  no network and no content persistence. These tests prove neither trusted
  authorization nor runtime tenant isolation.
- **Verification:** `python3 -m unittest tests.test_knowledge_ingestion -v`,
  KI-1/KI-0 focused suites, repository governance and security checks,
  `compileall`, manual bounded benchmark, and `git diff --check`.
- **Rollback:** revert the isolated KI-2 commit; there is no durable content or
  infrastructure to clean up.
- **Resources/approval:** repository Python runtime only; no added dependency.
  Human review is required before any non-synthetic use or follow-on storage.

## KI-3 — Lexical retrieval and evaluation

- **Objective:** establish a reproducible non-model retrieval baseline before
  embeddings.
- **Reuse:** KI-1 manifest and KI-2-generated synthetic fixtures; existing
  repository evaluation and duplicate-case patterns.
- **Scope:** a frozen, small synthetic corpus and queries; deterministic token
  or metadata retrieval; source-version and byte-span citations; tenant/repo
  scope filters; explicit abstention; no model call and no production API.
- **Acceptance:** record Recall@10, MRR, latency and exact citation-span
  correctness against a versioned fixture; include unauthorized cross-scope
  negative cases; diagnostics and reports exclude raw content.
- **Verification:** focused offline tests, fixture integrity checks, relevant
  AI-quality/governance checks and `git diff --check`. Targets are proposed in
  `ACCEPTANCE_CRITERIA.md`, not assumed.
- **Rollback:** revert the local lexical adapter and evaluator; retain KI-0–2
  contracts. No persistent index exists.
- **Resources/approval:** local CPU only. Human review freezes the synthetic
  evaluation design before measuring it.

## KI-4 — Optional local embeddings

- **Objective:** compare one CPU-capable local model to the lexical baseline
  behind a replaceable adapter.
- **Dependencies:** KI-3 fixture frozen; model source, license, exact revision,
  artifact hash, resource budget and offline availability verified.
- **Scope:** optional isolated dependency lock and model adapter; no hosted
  provider, automatic download, production dependency or model action.
- **Acceptance:** report exact model/tokenizer revisions, dimensions, license,
  hardware, latency, memory and comparative retrieval metrics; fail closed if
  model artifacts cannot be verified locally.
- **Verification:** hash-verified isolated environment, offline unit tests and
  manually invoked bounded evaluation. Do not add model downloads to CI.
- **Rollback/resources/approval:** remove adapter and optional lock; no durable
  data. Owner reviews licensing and artifact acquisition before any download.

## KI-5 — Local storage and tenant isolation experiment

- **Objective:** assess a disposable local storage adapter and its authorization
  boundary without touching shared or hosted databases.
- **Dependencies:** stable KI-1 manifest, KI-3 evaluation and independent local
  database/container artifact review.
- **Scope:** test-only schema with synthetic records, least-privilege roles,
  forced tenant RLS, read/write/delete denial cases, rebuild and isolated
  backup/restore. No Render, Firebase or Supabase access.
- **Acceptance:** every cross-tenant operation denied; permitted same-tenant
  cases explicitly allowlisted; recovery recreates identical manifest IDs;
  lifecycle/deletion behavior reconciled with retention policy.
- **Verification:** pinned local image and offline test harness, policy tests,
  RLS checks and security review. Never run migrations against a shared DB.
- **Rollback/resources/approval:** remove only the isolated test files and
  resources created by that test. Human review of schema and role separation
  precedes containerized database work.

KI-4 and KI-5 may be separate workstreams after KI-3 freezes its fixture;
they must use separate branches and file ownership. Neither can change shared
contracts without a separate review.

## KI-6 — Hybrid retrieval and citations

- **Objective:** combine lexical and approved local-vector candidates behind
  stable interfaces, with exact source citations and deletion behavior.
- **Dependencies:** KI-3, KI-4, KI-5 all independently reviewed and measured.
- **Scope:** deterministic candidate fusion, source freshness checks,
  authorization re-checks, citation span validation and deletion across each
  local copy/cache. Read-only proposals only; no automatic document actions.
- **Acceptance/verification:** compare against the frozen baseline, meet or
  report proposed criteria without overstating them, run cross-tenant denial,
  stale citation and deletion tests, and complete an independent security
  review.
- **Rollback/resources/approval:** disable the adapter and remove only its
  test-generated local index. Human review is mandatory before any app API or
  non-synthetic data connection.

## KI-7 — Advisory agent and observability

- **Objective:** allow a governed agent to request evidence and produce a
  proposal without receiving write, schedule, merge, deploy or recovery rights.
- **Dependencies:** KI-6, trusted identity/scope contract, measured quality,
  retention/deletion evidence, and separately approved resource budgets.
- **Scope:** read-only retrieval, fixed safe output contract, audit metadata,
  and bounded metrics without prompts or document text. AI analysis remains
  optional and human-reviewed.
- **Acceptance/verification:** adversarial prompt-injection cases cannot widen
  permissions; unsupported or unauthorized inputs cause abstention; no tool
  call occurs from retrieved text alone; audit records correlate source and
  policy versions without content.
- **Rollback/resources/approval:** disable the adapter and preserve existing
  agents and deployment gates. Human approval is required before external agent
  runtime, paid inference, hosted identity or production action.

## Shared guardrails and rollback

- Use synthetic data only; treat source bytes as untrusted inert data.
- Preserve Firebase-disabled behavior, deny-all Firestore rules, PostgreSQL
  contracts, CI security, task ownership, P01, AI-9 and Codex runtime gates.
- No cloud provisioning, paid service, database migration, scheduled ingestion,
  deployment or production configuration change is implied by this roadmap.
- Every implementation remains isolated behind reviewed contracts, exact SHA
  evidence and a documented rollback path. A test pass is not production
  readiness or authenticated isolation.
