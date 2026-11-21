# xAI Grok adapter (offline-first, advisory only)

**Status:** `VERIFIED(source)` from published xAI documentation and local
behavioral tests; `UNVERIFIED(runtime)` for any live paid call. No live xAI
request was made. This integration does not open P01, AI-9, or Codex runtime
gates and does not authorize billing, merging, or deployment.

## Official contract references

| Topic | Source |
| --- | --- |
| Base URL `https://api.x.ai/v1`, `POST /v1/chat/completions`, Bearer auth, `max_completion_tokens`, response schema | [xAI Chat Completions REST reference](https://docs.x.ai/developers/rest-api-reference/inference/chat-completions) |
| Model `grok-4.7`, 500k context, 200k prompt-token pricing threshold, $2/$0.50/$6 and $4/$1/$12 per 1M tokens | [xAI Models](https://docs.x.ai/developers/models), [Grok 4.7](https://docs.x.ai/developers/models/grok-4.7) |
| `usage.cost_in_usd_ticks`, 1 USD = 10,000,000,000 ticks | [xAI Cost Tracking](https://docs.x.ai/developers/cost-tracking) |
| Reasoning cannot be disabled; reasoning tokens are billed in total consumption | [xAI Reasoning](https://docs.x.ai/developers/model-capabilities/text/reasoning) |

There is no existing Python Model Router or provider registry in Devobs.
Provider selection today is a fixed, opt-in startup branch in
`scripts/devobs_intelligence/staging_app.py`. The new package therefore adds a
self-contained provider interface rather than modifying orchestration code.

## Files

- `devobs/ai/providers/xai_config.py` — validated, non-secret configuration
- `devobs/ai/providers/xai_cost.py` — source-linked pricing and pre-flight estimate
- `devobs/ai/providers/xai_adapter.py` — bounded HTTP adapter, states, redaction, safe logs
- `devobs/ai/providers/xai_mock.py` — deterministic offline mock
- `tests/ai/providers/test_xai_adapter.py`, `test_xai_cost.py`, `test_xai_security.py`

## Default configuration

| Variable | Default | Effect |
| --- | --- | --- |
| `XAI_ENABLED` | `false` | No provider is usable until explicitly enabled |
| `XAI_DRY_RUN` | `true` | Uses the deterministic mock; no network call |
| `XAI_MODEL` | `grok-4.7` | Only models with an explicit pricing entry are accepted |
| `XAI_MAX_OUTPUT_TOKENS` | `2048` | Sent as `max_completion_tokens` |
| `XAI_MAX_REQUESTS_PER_RUN` | `0` | Hard per-instance request ceiling |
| `XAI_MAX_INPUT_TOKENS` | `8192` | Conservative prompt-token cap for estimation |
| `XAI_MAX_REASONING_TOKENS` | `8192` | Explicit allowance for mandatory reasoning tokens |
| `XAI_TIMEOUT_SECONDS` | `20` | Per-attempt HTTP timeout |
| `XAI_MAX_RETRIES` | `0` | Bounded retries, only on retryable statuses/transport errors |
| `XAI_MAX_RESPONSE_BYTES` | `65536` | Response body cap |
| `XAI_MAX_COST_USD` | `0` | Configured USD ceiling for one request |
| `XAI_REASONING_EFFORT` | `low` | Minimizes mandatory reasoning; `xhigh` is available on 4.7 |
| `DEVOBS_AI_BUDGET_APPROVED` | absent/`false` | Existing repo-wide paid-inference flag; must be `true` for live calls |
| `XAI_API_KEY` | unset | Read from the environment only when building a live provider |

Booleans accept only exact `true`/`false`. Integers and USD values are
range-checked. Unknown models, unknown reasoning levels, malformed values, and
token budgets above the 500k context window fail closed.

## Explicit states

| State | Meaning |
| --- | --- |
| `MOCK_SUCCESS` | Deterministic offline reply; `is_mock=True`; never a real Grok response |
| `CONFIGURATION_BLOCKED` | Disabled, invalid config/model, or rejected input |
| `AUTHENTICATION_REQUIRED` | Missing key or HTTP 401/403 |
| `BUDGET_BLOCKED` | Request limit, missing budget flag/authorization, or cost ceiling exceeded |
| `PROVIDER_UNAVAILABLE` | 429, 5xx, timeout, redirect, transport error, or malformed response |
| `VERIFIED_RESPONSE` | Response parsed and validated against the documented schema; not human approval |

## Usage

Offline by default:

```python
from devobs.ai.providers import XaiRequest, create_xai_provider, load_xai_config

config = load_xai_config()          # reads os.environ; stores no key
provider = create_xai_provider(config)  # disabled -> CONFIGURATION_BLOCKED
result = provider.complete(XaiRequest("safe advisory prompt"))
print(result.state, result.is_mock)
```

Deterministic mock:

```python
config = load_xai_config({"XAI_ENABLED": "true"})  # dry_run stays true
result = create_xai_provider(config).complete(XaiRequest("safe prompt"))
assert result.state == "MOCK_SUCCESS" and result.is_mock
```

A live call requires every gate, including explicit per-call authorization:

```python
from decimal import Decimal
from devobs.ai.providers import XaiAuthorization

config = load_xai_config({
    "XAI_ENABLED": "true",
    "XAI_DRY_RUN": "false",
    "XAI_MAX_REQUESTS_PER_RUN": "1",
    "XAI_MAX_COST_USD": "1.00",
    "DEVOBS_AI_BUDGET_APPROVED": "true",
})
# XAI_API_KEY must already be present in the secure environment.
provider = create_xai_provider(config)
authorization = XaiAuthorization(
    approved=True, approver="named-human", max_cost_usd=Decimal("0.50"))
result = provider.complete(XaiRequest("safe prompt"), authorization)
```

`XaiAuthorization` is an in-memory contract for an owner decision. It is not an
approval of a PR, a deployment, or a recurring spend authorization.

## Cost control

`estimate_max_request_cost()` returns a `Decimal` upper bound **before** a call:

```text
tier       = long_context if max_input_tokens >= 200_000 else short_context
billable   = max_input_tokens + max_output_tokens + max_reasoning_tokens
max_usd    = input_rate * max_input_tokens / 1M
           + output_rate * billable_output_tokens / 1M
```

Cached input is assumed to be zero, which over-estimates rather than
under-estimates. The estimate carries `source`, `source_url`, `observed_at`,
`currency`, context window, and threshold. After a real response, the adapter
uses the documented `usage.cost_in_usd_ticks` (or a conservative rate-based
fallback), compares it with both the authorization and configuration ceilings,
and returns `BUDGET_BLOCKED` on overage.

**Known limitation:** xAI does not publish a hard cap on reasoning tokens, and
`max_completion_tokens` bounds visible output only. The adapter enforces its own
`XAI_MAX_REASONING_TOKENS` policy ceiling and checks the returned token totals;
an overage is detected after the request. Operators should also set a spend
limit in the xAI console. This is not a guarantee against all billing variance.

## Safety boundaries

- Fixed endpoint; no configurable base URL, so no caller-controlled destination.
- API key is read from the environment only by `create_xai_provider`; config and
  logs contain only `api_key_present`. `XaiConfig.__repr__` and `XaiAdapter.__repr__`
  omit the key.
- No `tools`, `tool_choice`, `search_parameters`, `web_search_options`,
  `deferred`, or streaming tool surface is sent. `stream` is explicitly `false`.
- No shell, repository write, PR approval, or deployment path exists in the
  package. `XaiRequest` contains only prompt, request id, and optional system
  text; `XaiResult` contains no callables.
- Prompt and system text are bounded and redacted before use; redirects are
  refused; provider error bodies are discarded; retries are bounded by
  `XAI_MAX_RETRIES`.
- Structured logs use an allowlist (`state`, `reason`, `model`, `request_id`,
  `attempt`, `status`, token counts, `cost_usd`, `input_redacted`, `is_mock`,
  `source`, `tier`). Prompt text, response text, and credentials are never logged.
- Mock output is labeled `MOCK RESPONSE - NOT a real Grok response` and can
  never be `VERIFIED_RESPONSE`.

## Future Model Router integration (not implemented)

A future Router could call `create_xai_provider(config)` via the `XaiProvider`
protocol and treat `XaiResult.state` as a routing signal. It must keep the
existing repository-wide gates: `DEVOBS_AI_BUDGET_APPROVED`, `agent-spec.yaml`
direct-provider gates, Vertex failover policy, and the Phase 8 human approval
gate. No router, workflow consumer, scheduler, or orchestration file was
modified by this integration.

## Verification

```sh
python -m compileall -q devobs
python -m unittest discover -s tests/ai/providers -p "test_*.py" -v
```

`pytest` is not installed in the local operator environment, so
`python -m pytest -q tests/ai/providers` is reported as NOT RUN unless the
owner installs it. The tests are plain `unittest.TestCase` classes and are
pytest-compatible without fixtures.
