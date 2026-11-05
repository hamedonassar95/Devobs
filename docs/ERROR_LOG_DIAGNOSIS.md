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
enforce a monthly dollar cap. The Render draft uses one Gunicorn worker. The response
contains diagnosis, recommendation, severity, confidence, model id, and request
latency. Logs and model responses are not written to Devobs storage or echoed
into API errors. The provider response is not retained by the Responses API
request (`store: false`).

The route stays unavailable by default. Enabling it requires all of:

- `DEVOBS_AI_DIAGNOSTICS_ENABLED=true`
- `DEVOBS_AI_BUDGET_APPROVED=true`
- `OPENAI_API_KEY` supplied by the hosting provider's secret manager
- an OIDC token carrying `devobs.ai.diagnose`
- an existing service authorization for that tenant, project, and service

If the provider is disabled, requests return `503 ai_not_configured`. Startup
fails closed if the feature is enabled without the budget acknowledgment or
provider key. The acknowledgment is only an activation guard; it does not create
or prove a provider-enforced spending cap. The endpoint therefore must not be
activated until the repository's separate P01 budget and hosted-staging gates
are satisfied.

The endpoint rejects common credential formats in the log and requires the
caller to affirm that the input is redacted. That check cannot detect all
personal or confidential information. Send only logs reviewed and redacted by
the customer. Model output is untrusted advice and must not trigger automated
changes or incident actions.

The provider adapter reads only `OPENAI_API_KEY` from the runtime environment,
makes one HTTPS request to `POST /v1/responses` with a 20-second network timeout,
uses a strict JSON Schema response, sets `store: false`, caps generation at 512
output tokens, refuses redirects, and does not retry. It defaults to `gpt-6-luna`,
which OpenAI documents as its efficient model for focused, high-volume tasks.
These request/token limits reduce burst and per-request exposure, but they are
not an account-level monthly spending cap.
The model can be overridden with `DEVOBS_AI_MODEL` after confirming the model is
available to the account and supports Structured Outputs.

References:

- [GPT-6 Luna model and supported endpoints](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Responses API endpoint](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [OpenAPI contract](openapi/devobs-staging-diagnostics.json)

Offline tests use synthetic inputs and mocked provider responses. They do not
prove that a model call has occurred or that a hosted staging service is live.
