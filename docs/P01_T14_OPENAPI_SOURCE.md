# P01-T14: Source-only OpenAPI contract

This [OpenAPI 3.1 contract](openapi/devobs-staging-readonly.json) describes the four existing read-only WSGI routes and expected denial, rate-limit and backend-error shapes. It declares **no live server**, authorization provider, write endpoint or deployment.
Run `python3 -m unittest discover -s tests -p 'test_openapi_staging_contract.py' -v` after installing the pinned API dependencies. The test exercises synthetic WSGI requests; no HTTP listener, cloud account, network, database or real JWT is used.
The document is verified against the source's states, HTTP status, headers and bounded output. It does **not** prove hosted TLS, external OIDC/JWKS, real RLS, gateway limits, production OpenAPI conformance or complete T14 acceptance.
**P01 NO-GO / AI-9 FAIL** remain unchanged. Hosted API readiness and real negative-case testing require a separately approved provider, residency, privacy, identity and all-in cost boundary.
Official format: https://spec.openapis.org/oas/v3.1
