# AI provider resilience for Devobs

## Purpose and source

This document adapts the [SinapsAI Vercel Community showcase](https://community.vercel.com/t/showcase-sinapsai-zero-dependency-in-process-circuit-breaker-failover-adapter-for-vercel-ai-sdk/50911)
to Devobs. The post proposes an in-process circuit breaker, provider failover,
latency-aware routing, and a custom provider for the Vercel AI SDK. Its
performance and reliability statements are the author's claims; the post does
not include reproducible benchmarks or production measurements.

Devobs does not run a Next.js/Vercel AI SDK application. The incident and
repository automation calls run through GitHub Agentic Workflows; the isolated
manual smoke check uses Copilot CLI directly. Adding the SinapsAI package would
intercept neither route. Devobs instead uses the workflow-level breaker below
for trusted incidents; it does not copy the post's in-memory implementation.

## Current Devobs routing

The repository currently has:

- GitHub Copilot with `gpt-4.1` as the primary incident investigator.
- A Vertex AI / Gemini fallback, manually dispatchable and automatically
  dispatched once by the incident-scoped breaker after a failed Copilot call.
- A separate manually invoked Claude investigator experiment.
- A deterministic credential preflight that explicitly does not call a model.
- A separate [manual Copilot inference smoke workflow](../.github/workflows/copilot-inference-smoke.yml) that tests one fixed non-production prompt without using the incident investigator or its Vertex fallback. Its runtime result remains **UNVERIFIED** until the owner explicitly dispatches it after reviewing quota.

These routes are documented in [AI model strategy](AI_MODEL_STRATEGY.md),
[`incident-investigator.md`](../.github/workflows/incident-investigator.md),
[`incident-investigator-vertex.md`](../.github/workflows/incident-investigator-vertex.md),
and [`incident-investigator-claude.md`](../.github/workflows/incident-investigator-claude.md).

## Adapted resilience policy

The useful DevOps adaptation is an **evidence-gated provider breaker**. It should
distinguish provider health failures from configuration and policy failures:

| Failure signal | Proposed handling |
| --- | --- |
| Copilot CLI invocation fails, including a possible 429, provider 5xx, timeout, or other invocation error | Dispatch the configured Vertex fallback once for the trusted incident. The workflow does not parse raw provider errors, so a non-provider CLI error can also trigger this one attempt. |
| Invalid credentials, missing permission, unsupported model, or invalid project configuration | Fail closed and report the setup error. Do not route around it with another provider automatically. |
| Untrusted incident, missing evidence, or failed deterministic gate | Do not invoke any provider. |
| Successful inference | Keep the current route and record its outcome without storing prompts or secret values in the health record. |

A complete breaker would use `CLOSED`, `OPEN`, and `HALF_OPEN` states. A
provider-specific failure threshold opens the circuit; after a cooldown, one
controlled probe may test recovery. Concurrent runs must not each assume they
are the sole probe.

## Incident-scoped breaker implementation

The primary investigator writes a short-lived artifact (one day by default)
containing only the trusted incident number and its own run ID after the
deterministic trust gate passes.
When that workflow completes, the new
[`AI Provider Circuit Breaker`](../.github/workflows/ai-provider-circuit-breaker.yml)
workflow checks that the failed step was specifically `Execute GitHub Copilot
CLI`, verifies the artifact belongs to that run, and revalidates the open,
bot-created incident. It then writes one bot-authored breaker marker and
dispatches the existing Vertex fallback. The marker is the durable per-incident
state: it prevents another automatic dispatch for that incident even if the
primary workflow is re-run.

The integration uses GitHub's [`workflow_run` event](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_run),
[artifact download](https://docs.github.com/en/rest/actions/artifacts#download-an-artifact),
and [workflow dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).
The automatic fallback is triggered by failure of the Copilot CLI invocation
step; the workflow does not inspect the provider's raw error text, so other
failures within that invocation step can also trigger the single fallback.

This is a bounded `CLOSED → OPEN → single fallback probe` circuit per incident,
not a global provider health service. It uses the existing GitHub issue as the
idempotency record and the short-lived artifact only to correlate the exact
failed run with its trusted incident. If the fallback fails, no automatic retry
is scheduled; an operator can inspect the run and use the existing manual path
if appropriate.

## Controls and known limits

1. The trigger uses trusted workflow metadata and the failed Copilot invocation
   step; it never infers a provider failure from user-supplied issue text.
2. Limit fallback to one attempt per incident and verify that the primary run
   failed before dispatching it.
3. Run the selected provider's credential and access preflight first. A
   format-only preflight must not be described as proof that inference works.
4. Apply the existing incident trust gate and duplicate-comment check to every
   route. Reuse the same evidence contract and report validator.
5. Keep every provider investigator read-only. Preserve the single safe-output
   comment path and human review for any proposed recovery.
6. Track provider, outcome class, elapsed time, and whether fallback was used;
   do not record prompts, model responses, tokens, or secret values in breaker
   state.
7. Compare accuracy, evidence grounding, latency, rate-limit frequency, and
   cost on controlled non-production cases before changing the primary route.

## Rollout stages

1. **Implemented in source:** one automatic Vertex fallback after the precise
   primary Copilot invocation step fails, with trusted incident correlation and
   an at-most-once marker.
2. Review the first controlled fallback run for access, report quality, latency,
   and billing before considering a broader provider-health breaker.
3. Do not add Claude or retries until access, expected cost, and a bounded
   evaluation plan are established.

No SinapsAI dependency, credential, or deployment setting is added. A completed
primary Copilot failure now dispatches the configured Vertex workflow once;
when Vertex credentials permit model inference, that fallback may incur Google
Cloud charges ([Vertex AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)).
