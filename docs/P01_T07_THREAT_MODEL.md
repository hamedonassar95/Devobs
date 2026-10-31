# P01 T07 — Trust boundaries and synthetic abuse-case test matrix

**Scope:** Devobs `hamedonassar95/Devobs`; baseline `a7eeafcb88f06f6afac10bf8a9dbd22ad6d22c84`; task [#221 T07](https://github.com/hamedonassar95/Devobs/issues/221). This is an **offline threat-model deliverable**, not a live security assessment. Model: [threat-model.json](p01/threat-model.json).

## Architecture and trust decisions

- **Network → service (B01):** public traffic must pass TLS, authentication, rate, payload and concurrency bounds. Existing WSGI tests are **candidate references**, not live ingress proof.
- **Identity → service (B02):** verify token signature, issuer, audience, token kind and bounded lifetime; fail closed on JWKS errors, unknown keys and rotation.
- **Service → tenant → database (B03–B04):** source tenant and subject from a verified principal; database reads use non-owner restricted identity, forced RLS, exact permissive-policy inventory, and context isolation across pooled connections.
- **Telemetry → service (B05):** any later OTLP or change event must be allowlisted, time-bounded, source-SHA-bound and tenant-scoped; the present project has no verified live collector.
- **Connector → AI → approval (B06–B07):** remote connector text, PR metadata and model output are **untrusted evidence**, never action credentials. Agents may propose, but do not execute, merge, change IAM, access secrets, deploy or approve themselves.
- **CI → release (B08):** require exact reviewed source, signed-off artifact integrity and human release decision; static GitHub Pages publishing does **not** certify SaaS staging.
- **Provider → service (B09):** the owner's conditional **USD 100/month all-in** ceiling must be *enforceable*, inclusive of storage, bandwidth, model spend, fees and applicable taxes. Cloud region/provider/identity and operational controls need separate approval.

## Executable evidence contract

The model contains **12 synthetic abuse cases (AC01–AC12)** across **9 trust boundaries and 12 zones**. Every row specifies an adverse scenario, expected negative result, and a **candidate** in-repository test reference. A reference confirms only that a test file exists; it does not prove that test currently checks the scenario, nor that the test passes, nor that the live provider boundary is safe.

`python3 scripts/check_p01_threat_model.py` validates structure, exact trust edges, abuse-case completeness, local test-file references and fail-closed authorization/budget status without network or credentials.

`python3 -m unittest discover -s tests -p 'test_p01_threat_model.py' -v` provides mutation-based negative controls for removed/duplicated cases, RLS trust-edge drift, missing fixtures, false live status, unsupported provider spend, and unapproved staging/agent actions.

## Remaining acceptance before any gate promotion

1. Review each AC case with an architecture/security reviewer and demonstrate that the **actual test's assertions** match its stated negative expectation; add dedicated tests where a candidate reference is insufficient.
2. On exact PR head SHA, run CI's Python/security/CodeQL and preserve the resulting run URLs. Do not mark T07 COMPLETE based on this draft alone.
3. After separately authorized managed staging, run real OIDC/JWKS, cross-tenant PostgreSQL/RLS, network and provider cost controls; retain timestamps and redacted outputs. T08–T15 remain blocked independently.
4. Record any reviewed T07 acceptance in the official Issue #221 and checklist only after owner-controlled merge; preserve P01 `NO-GO`, AI-9 `FAIL`, no production release.

**No side effects:** No providers created, secrets accessed, paid AI activated, workflow settings changed or live services deployed.
