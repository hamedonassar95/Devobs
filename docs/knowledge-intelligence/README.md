# Devobs Knowledge Intelligence

**Phase 01 evidence baseline — 2026-11-26**
**Repository baseline:** hamedonassar95/Devobs at
1fc88930a9e66a318009b92f38510907b1793b1a
**Status:** Architecture audit and roadmap only. No runtime or infrastructure
change is included.

## Executive summary

Devobs already has deliberately bounded components: local repository graph
analysis, deterministic incident clustering, exact-scope metadata-only incident
memory, offline evaluation harnesses, a PostgreSQL tenant/RLS contract, and
optional local OpenTelemetry-to-Prometheus instrumentation. These are separate
capabilities, not one deployed knowledge service.

The audit found no general-purpose document ingestion pipeline, semantic
embedding generator, durable vector index, hybrid lexical/vector retriever, or
deployed knowledge API. Existing memory retrieval is exact tenant/project/service/
category filtering over in-memory incident metadata; the incident analyzer's
TF-IDF vectors are temporary clustering features, not reusable embeddings.
Graphify indexes repository structure and code relationships, not customer or
business documents.

This Phase 01 audit is a historical snapshot. KI-0 and KI-1 were subsequently
merged in PRs #787 and #788; KI-2 was merged in PR #789. The KI-2 ingestion
prototype is local-only and synthetic-only. KI-3 is under review on its own
feature branch and adds a deterministic lexical baseline; neither phase is a
general production service or authorizes real data, runtime access, a provider,
or deployment.

## Status labels

- **VERIFIED** — directly established by tracked code, tests, configuration, or
  exact-head GitHub evidence at the recorded commit.
- **PARTIAL** — a bounded local or synthetic implementation exists, but the
  requested end-to-end or production capability is not established.
- **MISSING** — no implementation was found in the inspected tracked source.
- **BLOCKED** — a required control, approval, data source, or prerequisite prevents
  the capability from being safely treated as ready.
- **UNKNOWN** — evidence is insufficient to make a reliable positive or negative
  claim.

These labels describe repository evidence only. A local test does not establish
hosted behavior, live connectivity, product quality, or operational readiness.

## Navigation

1. [Source register and evidence method](SOURCE_REGISTER.md)
2. [Repository audit](REPOSITORY_AUDIT.md)
3. [Capability gaps](GAP_ANALYSIS.md)
4. [Proposed architecture](ARCHITECTURE.md)
5. [Technology comparison](TECHNOLOGY_MATRIX.md)
6. [Dependency-ordered roadmap](ROADMAP.md)
7. [Measurable acceptance criteria](ACCEPTANCE_CRITERIA.md)
8. [Cost model](COST_MODEL.md)
9. [Risk register](RISK_REGISTER.md)
10. [ADR 0001: storage selection](adr/0001-storage-selection.md)
11. [KI-1 source manifest contract](SOURCE_MANIFEST.md)

## KI-0 source governance contract

The follow-on [KI-0 governance contract](KNOWLEDGE_GOVERNANCE.md) defines a
strict, versioned local source-policy envelope. The [privacy contract](PRIVACY_CONTRACT.md)
and [threat model](THREAT_MODEL.md) describe its trust limits. The
[roadmap](ROADMAP.md) now distinguishes the KI-0 implementation branch from
future planned milestones, and [acceptance criteria](ACCEPTANCE_CRITERIA.md)
labels future retrieval thresholds as proposed and reports KI-3 synthetic
measurements separately from production acceptance.

The validator uses only the Python standard library and synthetic fixtures.
Its `STRUCTURE_ONLY` result is not authorization, runtime tenant isolation, or
production readiness. No source content is ingested or fetched.

## KI-1 source manifest

The [KI-1 source manifest](SOURCE_MANIFEST.md) connects the merged KI-0 policy
validator to deterministic synthetic source, document-version, and chunk
records. PR #788 merged this contract and validator. Structural approval checks
are not authentication or runtime tenant isolation.

## KI-2 local ingestion prototype

The [KI-2 ingestion engine](INGESTION_ENGINE.md) reads only explicitly named
synthetic UTF-8 files, chunks by UTF-8 byte boundaries, and validates the full
result through KI-0 and KI-1. It is dry-run only, does not persist document
content, and is not a runtime API. KI-1 v1 caps documents at 65,536 bytes and
rejects overlapping chunks, so the engine fails closed outside those limits.

## KI-3 lexical retrieval baseline

PR #789 merged KI-2 at `d1ccb4d681a775404a0ac1e74977d9c2507fd83e`. The
`feature/ki-3-lexical-retrieval` review branch builds on that exact main SHA.
The KI-3 change reuses KI-0 policy validation, KI-1 manifest and UTF-8
byte-span validation, and KI-2 lifecycle behavior. It adds a deterministic
in-memory BM25 index over explicitly supplied synthetic records only. Results
contain validated references and scores, never raw source content. Scope values
are caller declarations and are not authenticated tenant isolation.

See [the retrieval engine contract](RETRIEVAL_ENGINE.md) and
[the versioned evaluation and measured baseline](RETRIEVAL_EVALUATION.md).
The secret-scan remediation advances only the synthetic fixture revision while
preserving the original v1 digest, query set, labels, and evaluation
methodology. PR #790 remains blocked pending its own required checks; the
evaluation set is synthetic and small, and its Recall@10 result is below the
exploratory target, not evidence of natural-query or production quality.

Existing source documents remain authoritative for their specific contracts;
this audit links to them rather than copying them. Start with
[AI Intelligence Core](../AI_INTELLIGENCE_CORE.md),
[offline evaluation datasets](../AI_EVALUATION_DATASETS.md),
[incident-memory contract](../AI_INTELLIGENCE_INCIDENT_MEMORY_V1.md),
[Graphify repository intelligence](../architecture/repository-intelligence.md),
[multi-agent workflow](../AI_MULTI_AGENT_WORKFLOW.md),
[Automation Hub](../AUTOMATION_HUB.md), and
[local OpenTelemetry integration](../integrations/opentelemetry.md).

## Guardrails

- Existing application/runtime schemas, deployment targets, CI, dependencies,
  and production gates are unchanged by the knowledge phases. KI-0 through
  KI-3 remain local and synthetic; KI-3 does not add a runtime API.
- No purchased PDF was copied, uploaded, or included. Bibliographic references
  are separated from independently written engineering requirements.
- No live databases, secrets, credentials, customer records, or hosted
  authentication were inspected.
- No technology in the comparison was installed or provisioned.
- P01 remains blocked/no-go, AI-9 remains blocked, and the Codex runtime gate
  remains open. The Phase 01 verification table below is a historical snapshot
  at its recorded source revision. This KI-1 branch separately reconciles
  merged PRs #785-#787 in `STATE.md` and the milestone ledger; do not infer
  service readiness from that bookkeeping update. See the
  [source register](SOURCE_REGISTER.md) for the audit's source boundary.
- The Phase 01 audit's acceptance values remain proposed targets. The separate
  KI-3 report records actual small synthetic retrieval and timing measurements;
  it does not establish natural-query or production quality.

## Verification snapshot

| Check | Result |
| --- | --- |
| Base and PR #785 evidence | PASS — exact merge SHA and main SHA match |
| Main CI / CodeQL for audited base | PASS — runs 45812551102 / 45812549606 |
| `python3 scripts/milestone_ledger.py --summary` | PASS, exit 0 — 314 merged milestones; latest recorded PR #784; P01 and AI-9 BLOCKED, Codex runtime OPEN; checkpoint predates merged PR #785 |
| `python3 -m unittest tests.test_milestone_ledger -v` | PASS, exit 0 — 96 tests |
| `python3 scripts/check_two_agent_tasks.py --manifest /tmp/devobs-ki-audit-manifest.json` | PASS, exit 0 — one planned task on this branch, no ownership conflict; generated synthetic manifest was outside the repository and removed after the check |
| `python3 -m unittest tests.test_two_agent_tasks -v` | PASS, exit 0 — 26 tests |
| `python3 scripts/check_agent_spec.py` | PASS, exit 0 — 7 agent specs and policy gates validated |
| `python3 -m unittest discover -s tests/ai_quality_gate -p 'test_*.py' -v` | PASS, exit 0 — 23 tests |
| `python3 scripts/check_action_pins.py` | PASS, exit 0 — 48 workflow/template files |
| `python3 scripts/check_site.py` | PASS, exit 0 — existing HTML page contracts and local HTTP smoke test; this is not a Markdown linter |
| `python3 -m unittest tests.test_check_site -v` | PASS, exit 0 — 9 tests |
| Custom relative-link and immutable source-anchor validation | PASS, exit 0 — 196 local Markdown links and 60 source/line citations validated at the audited SHA |
| Custom Markdown code-fence pairing check | PASS, exit 0 — 12 changed Markdown files |
| `git diff --check` | PASS, exit 0 |
| `python3 scripts/verify_gitleaks_coverage.py` | BLOCKED, exit 1 — requires a GitHub Actions job-summary path; no scanner result was produced. The `gitleaks` executable is not installed locally. |
| Repository Markdown linter | NOT RUN — no Markdown linter or Markdown-specific repository validation command was found; no tool was installed |
| Runtime, live storage, retrieval quality | NOT RUN — intentionally outside this documentation phase |

## Recommended next task

After KI-3 is reviewed, the next independent task is KI-4: evaluate one
optional, local embedding adapter against this frozen lexical baseline only
after model revision, license, artifact hash, offline availability, resource
budget, and human review are established. Do not activate a model, vector
database, hosted service, real source content, or production authorization.
