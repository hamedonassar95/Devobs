# AI-9 Confirmation Service-Authorization Boundary v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-confirmation-service-auth-boundary-v1` |
| Status | REGISTERED — IMPLEMENTATION NOT STARTED |
| Base commit | `d7a9ab663bc26ab54b8dcbd07c4e8072844f26af` (`origin/main`, after PR #303) |
| Scope | Make an authorization callback a required, fail-closed dependency of the local detector-confirmation adapter |

## Frozen contract

The detector-confirmation adapter currently accepts a syntactically valid caller-provided `serviceId` without requiring an authorization decision. This step will make `authorizeService` a mandatory injected callback so a future integration cannot instantiate the adapter without an explicit authorization boundary.

1. `createDetectorConfirmationAdapter` requires exactly two dependencies: `confirmationLayer` and `authorizeService`. Missing, extra, or incorrectly typed dependencies fail construction.
2. For each event window, validate only its outer shape and service-ID syntax first. Then call `authorizeService(Object.freeze({ serviceId }))` before parsing events or running the detector. Do not pass raw events, timestamps, metric values, or tokens to this callback.
3. Only the literal boolean `true` authorizes processing. `false`, `undefined`, or any other value rejects with `service_not_authorized`. Callback exceptions reject with the fixed code `service_authorization_failed`; exception text is not propagated.
4. A denied/failed authorization must not invoke the detector-confirmation state transition. Test this by denying a malformed metric batch and asserting the authorization error takes precedence while confirmation state remains unchanged.
5. Existing successful behavior, detector output mapping, confirmation policy, journal delivery semantics, and all gates remain unchanged. No authentication provider, token validation, service catalog, network call, tenant mapping, or real identity is introduced by this contract.
6. Tests use only local callback stubs and synthetic events. They demonstrate ordering and fail-closed behavior only; they do not establish that a production callback is correctly authenticated or maps an identity to a service.

## Verification plan

- Update the adapter's end-to-end contract tests to inject an allow callback.
- Add tests for denied, non-boolean and throwing callbacks; verify only the service ID is passed and denial occurs before event parsing/detector/confirmation.
- Run `node --check` on the adapter/test, the focused adapter test, `node --test tests/*.test.*`, CI trigger and release-gate contract tests, action pin audit, site/agent-spec checks, relative-link validation, and `git diff --check`.
- Hosted PR CI, CodeQL, Vercel Preview, and post-merge main CI/Pages remain required before the step is complete.

## Explicit limits

The callback is an integration seam, not an authentication system. The repository does not supply an authenticated caller context, authoritative service registry, or provider-backed identity. A production caller could still provide an unsafe callback; review and live auth/RLS evidence remain blocked by P01. No cloud, credential, real telemetry, evaluation seed, or live service is used.

AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**. No detector, gate, threshold, evaluation protocol, or production route changes.
