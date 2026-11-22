# AI Provider Evaluation — offline harness

**Status:** deterministic, offline-only, advisory. `DRY_RUN` semantics only; the
harness never calls a live provider, reads a credential, opens a socket, changes
Git state, bills, deploys or grants an approval. It does not change P01 (NO-GO),
AI-9 (BLOCKED) or Codex runtime acceptance (OPEN).

**Base revision:** `origin/main` `10f8dd9b1e884e16cea3ffd847cf20405794cb8b`
(merge of PR #741). Branch: `feature/ai-provider-evaluation-finalization`.

## Purpose

The repository already has two distinct evaluation surfaces:

| Existing surface | What it does | This harness's relationship |
| --- | --- | --- |
| `scripts/devobs_intelligence/evaluation.py` | Offline synthetic adviser scoring with pinned fixture digests. | Reused as precedent for fixtures and digest discipline; not modified. |
| `devobs/ai_quality_gate/` (merged PR #741) | Agent-coordination quality gate (`DRY_RUN`, advisory, no network). | Reused as the authority model for authority invariants; not modified. |

This package adds the missing **provider contract** layer: given a named
provider/model configuration and a deterministic scenario, produce one closed,
structured result that records latency, error category, reliability, estimated
tokens/cost and the safety policy result, plus a cross-provider comparison.

## Owned files

| Path | Role |
| --- | --- |
| `devobs/ai_evaluation/models.py` | Closed contracts, fail-closed validation, redaction. |
| `devobs/ai_evaluation/pricing.py` | Configurable pricing with explicit `UNKNOWN`. |
| `devobs/ai_evaluation/mocks.py` | Seeded deterministic offline mocks. |
| `devobs/ai_evaluation/engine.py` | Composition, routing, cost ceiling, comparison, fingerprint. |
| `devobs/ai_evaluation/cli.py` | Read-only JSON CLI. |
| `examples/ai_evaluation/` | Fixture and pricing inputs. |
| `tests/ai_evaluation/` | Behavioral, contract and security tests. |

No file owned by PR #741 (`devobs/ai_quality_gate/`, `tests/ai_quality_gate/`,
`examples/ai_quality_gate/`, `docs/ai-quality-gate.md`, `.github/workflows/ci.yml`)
was modified. There is no new CI job: the existing reusable Python CI discovers
all tests under `tests/` and compiles `devobs/`.

## Supported providers (offline fixtures only)

The harness is provider-independent. The shipped fixture configurations are
**synthetic identifiers** used to exercise the contract, not endorsements or
live integrations:

| Provider id | Model id | Capabilities | Pricing status |
| --- | --- | --- | --- |
| `fixture-primary` | `grok-4.7` | incident triage, runbook recommendation, structured JSON, advisory only, cost awareness | `ESTIMATED` from a configurable source-linked rate (2.00 / 0.50 USD per million prompt/completion tokens) |
| `fixture-fallback` | `gemini-2.5-pro` | incident triage, advisory only, log redaction | `UNKNOWN` — deliberately unverified in the shipped snapshot |

Live provider selection in the application is a separate startup branch in
`scripts/devobs_intelligence/staging_app.py` (`ollama`/`localai`, `openai`,
`gemini`) with explicit budget and data-policy gates. This harness does not
change that routing or add an `xai` branch. A pending xAI/Grok adapter exists on
another branch and is **not** imported, copied or modified here.

Official pricing sources recorded in the shipped snapshot (read-only reference,
not fetched during evaluation):

- https://docs.x.ai/developers/models
- https://openai.com/api/pricing/

External pricing validity is **UNVERIFIED**; no network lookup was performed.

## Structured result contract

Each case result contains:

| Field | Meaning |
| --- | --- |
| `provider_id`, `model_id` | Configured provider and model identifiers. |
| `latency_ms` | Seeded fixture latency (not a live measurement). |
| `error_category` | `NONE`, `TIMEOUT`, `RATE_LIMIT`, `INVALID_RESPONSE`, `AUTHENTICATION`, `CONFIGURATION`, `COST`, `SAFETY`, `UNAVAILABLE`, `OUTBOUND`. |
| `reliability_score` | Deterministic 0–1 score for the simulated outcome. |
| `prompt_tokens`, `completion_tokens`, `estimated_tokens` | Estimated token usage. |
| `estimated_cost_usd`, `cost_confidence`, `cost_source` | Cost estimate and provenance; `null`/`UNKNOWN` when pricing is unverified. |
| `safety_policy_result` | `ALLOWED`, `BLOCKED` or `NOT_EVALUATED`. |
| `status`, `outcome`, `attempts`, `is_mock` | Fail-closed state and retry evidence. |

The report adds a `fingerprint` (SHA-256 over fixture version, seed, case
outcomes and aggregate costs), `comparison.by_provider` and
`comparison.by_capability`, `offline: true` and `live_calls: 0`.

## Deterministic scenarios

| Scenario | Expected outcome | Error category | Safety result |
| --- | --- | --- | --- |
| `success` | `SUCCESS` | `NONE` | `ALLOWED` |
| `timeout` | `TIMEOUT` | `TIMEOUT` | `NOT_EVALUATED` |
| `rate_limit_then_success` | `SUCCESS` after 2 attempts | `RATE_LIMIT` | `ALLOWED` |
| `malformed_json` | `MALFORMED_RESPONSE` | `INVALID_RESPONSE` | `NOT_EVALUATED` |
| `missing_credentials` | `AUTHENTICATION_ERROR` | `AUTHENTICATION` | `NOT_EVALUATED` |
| `cost_ceiling` | `BUDGET_BLOCKED` | `COST` | `NOT_EVALUATED` |
| `unsafe_action` | `UNSAFE_ACTION_BLOCKED` | `SAFETY` | `BLOCKED` |
| `outage` | `PROVIDER_UNAVAILABLE` | `UNAVAILABLE` | `NOT_EVALUATED` |
| `redirect` | `OUTBOUND_BLOCKED` | `OUTBOUND` | `NOT_EVALUATED` |

## Fail-closed controls

- Provider configs reject endpoint/host/proxy/TLS override keys and any
  credential-like key (`api_key`, `token`, `secret`, `password`, ...).
- Live mode is impossible: `assert_live_mode_allowed` rejects an offline config
  even when a synthetic `LiveModeAuthorization` object is supplied.
- Unknown scenarios are rejected at fixture construction; an invalid pricing
  catalog, empty catalog, negative rate or verified price without a source is
  rejected. Unverified prices become `UNKNOWN`, never `0`.
- Redaction is deterministic and idempotent; mocks cannot return a verified
  live response. The CLI returns status `INVALID` with a fixed reason on any
  invalid input and never echoes file content.

## Usage

```sh
python -m devobs.ai_evaluation.cli \
  --fixtures examples/ai_evaluation/provider_cases.json \
  --pricing examples/ai_evaluation/pricing.json
python -m unittest discover -s tests/ai_evaluation -p "test_*.py" -v
```

To change pricing, edit `examples/ai_evaluation/pricing.json` (or pass your own
file). Set `verified: false` to force `UNKNOWN` for any model.

## Known limitations

- Latency and token counts are seeded fixture values, not measurements.
- Quality proxy is marker/status based; it is not a calibrated accuracy metric
  and uses non-expert-reviewed synthetic prompts.
- Safety results are fixture assertions, not a live policy engine.
- Estimated cost is advisory; reasoning-token pricing and tiered/long-context
  rates are not modelled.
- No live provider comparison, credential preflight or paid inference is
  authorized by this harness. Any such step requires separate owner approval.

## Verification matrix

Filled with fresh local evidence on 2026-11-22 (see final report for exact
commands and final output lines):

| Check | Command family | Result |
| --- | --- | --- |
| Unit + contract + security suite | `python -m unittest discover -s tests/ai_evaluation -p "test_*.py" -v` | PASS — `Ran 16 tests`, `OK` |
| Existing AI evaluation fixtures | `python -m unittest discover -s tests -p "test_ai_eval_fixture_guard.py" -v` | PASS |
| Existing intelligence evaluation tests | `python -m unittest ... test_intelligence_evaluation*.py` | PASS |
| Merged quality-gate regression | `python -m unittest discover -s tests/ai_quality_gate -p "test_*.py" -v` | PASS |
| Full `tests/` discovery | `python -m unittest discover -s tests -p "test_*.py"` | NOT COMPLETED — terminated at 300s (exit 143); pre-existing large-suite runtime, not a failure of the new tests |
| Compile all Python paths | `python -m compileall -q devobs/ai_evaluation tests/ai_evaluation` | PASS (exit 0) |
| JSON fixture/schema validation | CLI run + `json.load` of both example files | PASS (`JSON fixtures: OK`) |
| Production static network/exec scan | source scan of `devobs/ai_evaluation/*.py` | PASS (no network/process/dynamic-exec patterns) |
| Workflow validation | No workflow file changed | NOT APPLICABLE to this diff (`actionlint` present but slow; repo lint script needs an explicit binary path) |
| Lint (`ruff`) / type check (`mypy`) / Bandit / gitleaks | Tool modules and binaries unavailable | NOT RUN — reported, not claimed as passing |
| Live provider / paid API call | Not authorized | BLOCKED by design |
| Draft PR creation | `gh` unavailable; unauthenticated GitHub API returns 401; token reading forbidden by AGENTS.md | BLOCKED — manual creation required |
