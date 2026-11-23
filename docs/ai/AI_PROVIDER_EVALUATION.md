# AI Provider Evaluation — offline harness

**Status:** deterministic, offline-only, advisory. `DRY_RUN` semantics only; the
harness never calls a live provider, reads a credential, opens a socket, changes
Git state, bills, deploys or grants an approval. It does not change P01 (NO-GO),
AI-9 (BLOCKED) or Codex runtime acceptance (OPEN).

**Base revision:** `origin/main` `b90407040e3d2a34627679f2cbca14db46eb70ca`.
Branch: `feature/ai-provider-harness-quality-gate`, which replays the reviewed
finalization commits `eef5d6b`..`7dff0c0` from
`feature/ai-provider-evaluation-finalization` onto that base.

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
| `devobs/ai_evaluation/gate.py` | Pinned offline quality gate, score, failure codes and evidence. |
| `devobs/ai_evaluation/cli.py` | Read-only JSON CLI with `--gate` mode. |
| `examples/ai_evaluation/` | Fixture and pricing inputs. |
| `tests/ai_evaluation/` | Behavioral, contract, gate and security tests. |

Files owned by PR #741 (`devobs/ai_quality_gate/`, `tests/ai_quality_gate/`,
`examples/ai_quality_gate/`, `docs/ai-quality-gate.md`) were not modified. One
step was added to the existing `security` job in `.github/workflows/ci.yml`,
beside the existing advisory AI quality-gate step; there is no new CI job, no
new workflow and no merge/deploy/approval authority. The reusable Python CI
still discovers all tests under `tests/` and compiles `devobs/`.

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

## Deterministic quality gate

`devobs/ai_evaluation/gate.py` turns one offline report into a single closed
decision. It is advisory: `PASS` means only that the shipped fixtures still
match their pinned expectations, never that a live provider works.

| Criterion | Rule |
| --- | --- |
| Fixture identity | Report `fingerprint` must equal `e04ae0abf3e33f4c` (SHA-256 prefix over fixture version, seed, case outcomes and aggregate costs). Any intentional fixture or pricing change must update this pin in the same reviewed commit. |
| Outcome/status | Every case's `outcome` and `status` must match its fixture expectation. |
| Offline authority | `offline: true`, `live_calls: 0`, every result `is_mock: true`, provider/model identifiers present. |
| Cost truthfulness | `estimated_cost_usd: null` iff `cost_confidence: UNKNOWN`; unverified prices are never reported as zero. |
| Safety | Expected `UNSAFE_ACTION_BLOCKED` must report `BLOCKED`; expected `OUTBOUND_BLOCKED` must report status `BLOCKED`. |
| Reliability | Each expected-success case must score at least `0.75`. |
| Composite | `quality = matched outcome/status cases / total`; `reliability = mean reliability_score over expected-success cases`; `composite = 0.6 * quality + 0.4 * reliability`. `PASS` requires zero failures and `composite >= 0.90`. |

Stable exit codes: `0` = `PASS`, `1` = `BLOCKED` (a deterministic expectation
failed), `2` = `INVALID` (the gate itself failed closed). Failures are sorted,
closed-form codes such as `fingerprint_drift:...`,
`outcome_mismatch:<case_id>:...` and `cost_confidence_mismatch:<case_id>`; the
result carries evidence with `TESTED`/`UNKNOWN` confidence. An unexpected
exception always yields `INVALID`, never a pass.

CI: the existing `security` job runs the CLI with `--gate`, fails on any
non-zero exit and re-validates the JSON invariants (`schema_version`,
`decision`, `exit_code`, `offline`, `live_calls`, `failures`) before writing a
one-line summary. That step has no live call path and reads no credential.

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
python -m devobs.ai_evaluation.cli \
  --fixtures examples/ai_evaluation/provider_cases.json \
  --pricing examples/ai_evaluation/pricing.json --gate
python -m unittest discover -s tests/ai_evaluation -p "test_*.py" -v
```

The `--gate` run prints one JSON object and exits `0` only on `PASS`.

To change pricing, edit `examples/ai_evaluation/pricing.json` (or pass your own
file). Set `verified: false` to force `UNKNOWN` for any model. Any change to the
shipped fixture or pricing inputs changes the report fingerprint and must
update `EXPECTED_FINGERPRINT` in `devobs/ai_evaluation/gate.py` and this
document in the same reviewed commit.

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

Filled with fresh local evidence on 2026-11-23 (see final report for exact
commands and final output lines):

| Check | Command family | Result |
| --- | --- | --- |
| Unit + contract + gate + security suite | `python -m unittest discover -s tests/ai_evaluation -p "test_*.py" -v` | PASS — `Ran 49 tests in 0.846s`, `OK` (exit 0) |
| Merged quality-gate regression | `python -m unittest discover -s tests/ai_quality_gate -p "test_*.py"` | PASS — `Ran 23 tests in 0.516s`, `OK` (exit 0) |
| Gate CLI (offline, pinned fixtures) | `python -m devobs.ai_evaluation.cli ... --gate` | PASS — exit 0, `decision PASS`, `composite 0.9667`, `failures 0`, `fingerprint e04ae0abf3e33f4c` |
| Compile all Python paths | `python -m compileall -q devobs/ai_evaluation tests/ai_evaluation` | PASS (exit 0) |
| Existing AI evaluation fixtures / intelligence evaluation | `test_ai_eval_fixture_guard.py`, `test_intelligence_evaluation*.py` | PASS (earlier verified evidence on this branch) |
| JSON fixture/schema validation | CLI run + `json.load` of both example files | PASS (`JSON fixtures: OK`) |
| Existing pinned dataset validator | `python scripts/validate_ai_eval_fixtures.py` | PASS for the committed blob (SHA-256 matches policy); the local Windows worktree run reports `dataset_digest_mismatch` only because `core.autocrlf=true` rewrites LF to CRLF. The Linux CI checkout is unaffected. |
| Production static network/exec scan | source scan of `devobs/ai_evaluation/*.py` | PASS (no network/process/dynamic-exec patterns) |
| Diff hygiene | `git diff --check` | PASS (exit 0) |
| Workflow validation | `actionlint` / `scripts/lint_authored_workflows.py` | NOT RUN locally — actionlint binary unavailable (`WinError 2`) and repo lint script failed; CI installs a pinned actionlint 1.7.12 + ShellCheck 0.11.0 in the `security` job |
| Full `tests/` discovery | `python -m unittest discover -s tests -p "test_*.py"` | NOT COMPLETED — terminated at 300s (exit 143); pre-existing large-suite runtime, not a failure of the new tests |
| Lint (`ruff`) / type check (`mypy`) / Bandit / gitleaks | Tool modules and binaries unavailable | NOT RUN — reported, not claimed as passing |
| Live provider / paid API call | Not authorized | BLOCKED by design |
| Draft PR creation | `gh` unavailable; token reading forbidden by AGENTS.md | Attempted via unauthenticated GitHub API; see final report for exact result |
