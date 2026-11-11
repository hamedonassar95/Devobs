# AI-9 Confirmation Service-Authorization Boundary v1 — Implementation Record

**Status:** local integration seam only. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**. This change does not implement authentication, tenant isolation, or a production identity provider.

## Implemented contract

The preregistration [`AI9_CONFIRMATION_SERVICE_AUTH_BOUNDARY_V1_PREREGISTRATION.md`](AI9_CONFIRMATION_SERVICE_AUTH_BOUNDARY_V1_PREREGISTRATION.md) was committed before code. `createDetectorConfirmationAdapter` now requires exactly `confirmationLayer` and `authorizeService`. The adapter first checks only the input envelope shape and service-ID syntax, then calls the injected authorization callback with a frozen object containing only `serviceId`. It validates timestamps and parses metric events only after the callback returns literal `true`.

Any false or non-boolean callback result fails with `service_not_authorized`. Callback exceptions fail with the fixed `service_authorization_failed` error without exposing callback details. Denial or callback failure leaves confirmation state unchanged. The implementation has no token, identity-provider, service-catalog, tenant-mapping, network, or database integration. A caller must supply a correctly authenticated and scoped callback; this module cannot prove that it is correct.

## Verification

- `node --check scripts/ai_intelligence/post_detector_confirmation_adapter.mjs` and `node --check tests/post_detector_confirmation_adapter.test.mjs` — **PASS**.
- `node --test tests/post_detector_confirmation_adapter.test.mjs` — **8/8 passed**.
- `node --test tests/*.test.*` — **129/129 passed**, 0 failed, 0 skipped.
- `python3 -m unittest discover -s tests -p 'test_ci_trigger_contract.py' -v` — **2/2 passed**.
- `python3 -m unittest discover -s tests -p 'test_ci_release_gate.py' -v` — **1/1 passed**.
- `python3 scripts/check_action_pins.py` — **39 workflow/template files passed**.
- `python3 scripts/check_agent_spec.py` and `python3 scripts/check_site.py` — **PASS**.
- `git diff --check` — **PASS**.

Hosted PR CI, CodeQL, Vercel Preview, and post-merge `main` CI/Pages are required before this step is complete; their run IDs and final SHA will be recorded after they finish.

## Limits

These tests establish callback ordering and fail-closed behavior with local stubs only. They do not establish real authentication, authorization policy quality, user-to-service mapping, tenant isolation, or service health. No AI-9 evaluator, quality metric, seed, holdout, real telemetry, cloud resource, or production service was run or changed. No gate, threshold, detector behavior, or AI-9 status changed.
