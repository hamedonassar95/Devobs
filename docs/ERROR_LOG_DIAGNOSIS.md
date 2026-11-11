# Error log diagnosis endpoint

The staging WSGI API has one opt-in route for an advisory diagnosis:

```text
POST /v1/tenants/{tenant}/projects/{project}/services/{service}/diagnostics
```

It accepts only `application/json` with `error_log` and `data_redacted: true`. The
caller must have the `devobs.ai.diagnose` token scope and be authorized for the
registered service. Input is limited to 8 KiB of UTF-8 and the complete JSON
request body is limited to 32 KiB. Requests are rate-limited to five diagnoses
per subject and tenant per minute and five total valid diagnoses per process
per minute. Both limits are in-memory, reset on process restart, and do not
enforce a monthly dollar cap. The Render draft uses one Gunicorn worker. The
response contains diagnosis, recommendation, severity, confidence, model id,
and request latency. Logs and model responses are not written to Devobs storage
or echoed into API errors. Provider data handling is provider-specific: the
OpenAI adapter sends `store: false`; Gemini has no equivalent non-retention
claim in this integration, so the operator must check the currently applicable
Google service terms before enabling it.

The route stays unavailable by default. All provider choices require:

- `DEVOBS_AI_DIAGNOSTICS_ENABLED=true`
- an OIDC token carrying `devobs.ai.diagnose`
- an existing service authorization for that tenant, project, and service

OpenAI and Gemini additionally require `DEVOBS_AI_BUDGET_APPROVED=true` and a
selected provider key supplied by the hosting provider's secret manager.
Gemini additionally requires the data-policy approval described below.

For local inference, select `DEVOBS_AI_PROVIDER=ollama` or `localai`, set
`DEVOBS_LOCAL_MODEL` to an installed model, and explicitly set
`DEVOBS_AI_LOCAL_INFERENCE_APPROVED=true`. This approval is separate from the
cloud budget flag: local inference does not call OpenAI or Google and does not
require `DEVOBS_AI_BUDGET_APPROVED`. Local inference is rejected on Render and
is intended only when the API process and model runtime share the same host.
The adapter uses only `127.0.0.1:11434` for Ollama or `127.0.0.1:8080` for
LocalAI; URLs cannot be configured, environment proxies are bypassed, and
redirects are rejected. `LOCALAI_API_KEY`, when configured, is read from the
environment and sent only to the loopback LocalAI endpoint. Ollama needs no API
key for this direct local HTTP integration. The adapter makes one bounded,
non-streaming chat-completion request, rejects tool-call responses, and accepts
only a strictly validated JSON diagnosis. It does not pull images or weights.

Loopback binding means the service cannot reach a model runtime running on a
different host or in a separate container network. The current Compose stack
publishes each model API on host loopback, so run the Devobs API on that same
host; do not change the URLs to a public address. The local model process
receives the redacted log and may have its own logging behavior, which the
Devobs adapter cannot control. Review the selected model's license, resource
use, and runtime data handling before use. No live local inference has been
run by these changes.

The provider defaults to `openai` to preserve existing behavior. `gemini` is an
optional alternative selected with `DEVOBS_AI_PROVIDER=gemini`; it additionally
requires `GEMINI_API_KEY`, `DEVOBS_GEMINI_MODEL`, and
`DEVOBS_AI_GEMINI_DATA_POLICY_APPROVED=true`. It deliberately does not fall back
to `GOOGLE_API_KEY`. For Gemini, that policy flag means an operator has reviewed
the applicable Google terms and approved sending this category of redacted input;
it is not a technical retention control. Startup fails closed if the selected
provider-specific key, model, policy acknowledgment, or budget acknowledgment
is missing. The budget acknowledgment does not create or prove a provider-enforced
spending cap. Cloud-provider activation remains subject to the separate P01
budget and hosted-staging gates.

The endpoint rejects common credential formats in the log and requires the
caller to affirm that the input is redacted. That check cannot detect all
personal or confidential information. Send only logs reviewed and redacted by
the customer. Model output is untrusted advice and must not trigger automated
changes or incident actions.

The OpenAI adapter defaults to `gpt-6-luna` (overridable via `DEVOBS_AI_MODEL`)
and makes one HTTPS request with a 20-second timeout, no redirect or retry, a
strict response schema, `store: false`, and at most 512 output tokens.
The Gemini adapter sends one HTTPS `generateContent` request to Google's fixed
API host, puts `GEMINI_API_KEY` in the `X-Goog-Api-Key` header (not the URL),
requests JSON output, applies the same timeout/output ceiling, and also refuses
redirects and retries. Both adapters reject credential-like values, require the
input to be asserted redacted, limit total requests to five per process/minute,
and only return advisory text. Request limits do not enforce a monthly spending
cap. The Gemini model must be explicitly selected with `DEVOBS_GEMINI_MODEL`;
confirm its availability and current pricing before any live request.

**Gemini data handling needs extra care.** Google's Gemini API terms distinguish
unpaid and paid services: inputs/outputs for unpaid services may be used to
provide, improve, and develop Google products and may be read by human reviewers;
paid-service handling is different but still has provider logging terms. The
account's actual service/quota classification and applicable terms must be
confirmed by the owner. Do not send customer or confidential operational data.
Use synthetic examples until those terms and an explicit spend limit are reviewed.
The feature is not enabled in the checked-in Render blueprint, and no live
Gemini request has been made by these changes.

References:

- [GPT-6 Luna model and supported endpoints](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Responses API endpoint](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Gemini `generateContent` API reference](https://ai.google.dev/api/generate-content)
- [Gemini API key safety guidance](https://ai.google.dev/gemini-api/docs/api-key)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API terms](https://ai.google.dev/gemini-api/terms)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [LocalAI text-generation API](https://localai.io/docs/features/text-generation/)
- [LocalAI authentication](https://localai.io/docs/features/authentication/)
- [OpenAPI contract](openapi/devobs-staging-diagnostics.json)

Offline tests use synthetic inputs and mocked provider responses. They do not
prove that a model call has occurred or that a hosted staging service is live.
