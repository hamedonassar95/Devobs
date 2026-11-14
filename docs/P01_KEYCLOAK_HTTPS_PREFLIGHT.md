# P01 local Keycloak HTTPS discovery and JWKS preflight

**Live runtime status: BLOCKED.** The checker and isolated Compose definition are ready for an operator-provided local TLS certificate, private-key mount, and public CA certificate. No TLS material was provided in this work session, so no HTTPS container or live request was started. The offline tests are contract tests only; they do not establish a real certificate-verified connection.

## Scope and verified baseline

- Based on `main` SHA `3ff67552daea5e03fa52d294ab5f868f4c645832`.
- PR [#604](https://github.com/hamedonassar95/Devobs/pull/604) merged at that SHA from head `461b3b668e2ab269f17368a0a6ce8128aee62d46`. Exact-SHA post-merge CI [43532120776](https://github.com/hamedonassar95/Devobs/actions/runs/43532120776) and CodeQL [43532120146](https://github.com/hamedonassar95/Devobs/actions/runs/43532120146) passed.
- Compose uses the existing Keycloak image pin `quay.io/keycloak/keycloak:26.8.2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0` and imports the existing `devobs-local` realm. No users or OAuth clients are added.
- The HTTPS service publishes only `127.0.0.1:8443`, disables HTTP, uses an internal Compose network, and mounts the operator's TLS certificate and private key read-only. It does not create host directories for absent certificate paths.

## Operator-only runtime procedure

Use an already approved local certificate chain and matching private key from a trusted local CA. The server certificate must contain a `DNS:localhost` SAN and be valid for TLS server authentication. Include `IP:127.0.0.1` as a SAN if your local certificate policy requires it. Keep the private key on the operator's machine; do not copy it into the repository, chat, logs, or CI. The `--ca-cert` argument must point to a public CA certificate PEM file only.

In PowerShell, set process-local paths to the existing files (these variables contain paths, never certificate or key contents):

```powershell
$env:DEVOBS_KEYCLOAK_TLS_CERT_FILE = (Resolve-Path 'C:\path\to\localhost-chain.pem').Path
$env:DEVOBS_KEYCLOAK_TLS_KEY_FILE = (Resolve-Path 'C:\path\to\localhost-key.pem').Path
$project = 'devobs-kc-https-local-<unique-suffix>'
docker compose -p $project -f dev/keycloak/compose.https.local.yaml config --quiet
docker compose -p $project -f dev/keycloak/compose.https.local.yaml up -d keycloak
python3 scripts/p01_keycloak_https_preflight.py --ca-cert 'C:\path\to\public-test-ca.pem'
docker compose -p $project -f dev/keycloak/compose.https.local.yaml down --remove-orphans
Remove-Item Env:DEVOBS_KEYCLOAK_TLS_CERT_FILE
Remove-Item Env:DEVOBS_KEYCLOAK_TLS_KEY_FILE
```

Run cleanup even if the preflight fails. The project name must be unique; cleanup is scoped to that name. The checker makes at most two HTTPS GET requests, each with a four-second timeout and bounded response/header sizes. It accepts no arbitrary URL. It resolves only `localhost`, rejects any non-loopback DNS answer, pins the socket to the checked loopback address, verifies the TLS chain using only the supplied CA, and verifies the certificate hostname with `check_hostname=True` and `CERT_REQUIRED`. Redirects are rejected without following their `Location`.

The Compose defaults point at `dev/keycloak/operator-certs/localhost.crt` and `localhost.key`, but `create_host_path: false` means missing files are not created. Prefer the process-local path variables above. The compose configuration command can be checked without mounting or reading key contents. Do not set any Keycloak admin bootstrap variables.

## What the checker proves

The fixed issuer is `https://localhost:8443/realms/devobs-local`. On a live run it requires:

- a certificate chain that validates against the operator-supplied public CA and a certificate valid for `localhost`;
- HTTP 200 JSON discovery with the exact issuer above;
- the exact same-origin JWKS URI `https://localhost:8443/realms/devobs-local/protocol/openid-connect/certs`;
- one to ten public RSA signing JWKs acceptable to the existing `AccessTokenVerifier` (RS256, `use=sig`, unique `kid`, public key material only, and at least 2048-bit modulus).

The checker reuses the production verifier's public-key validation but does not call `trusted_oidc_verifier`: that metadata builder accepts only the standard HTTPS port, whereas this deliberately loopback-only fixture uses 8443. The checker validates the exact local issuer and JWKS URI itself. No production OIDC setting or verifier is changed.

A successful result is `LOCAL_HTTPS_OIDC_PREFLIGHT_PASS`, with `signed_token_acceptance: NOT_TESTED` and `readiness_claim: NOT_ESTABLISHED`. It does **not** prove that Keycloak issues a Devobs-acceptable access token. It does not test `typ=at+jwt`, `aud`, `client_id`, `sub`, `jti`, `iat`, `exp`, the 900-second lifetime, `devobs.read`, token signatures, RLS, staging, or production readiness. No user, OAuth client, token, signing key, or identity is created by this preflight.

## Verification evidence and limits

- Base SHA and PR #604 merge/CI are verified above.
- `docker compose -f dev/keycloak/compose.https.local.yaml config --quiet` validates Compose structure only; it does not prove the TLS paths exist or the container starts.
- `tests/test_p01_keycloak_https_preflight.py` uses injected JSON documents and a synthetic **public-only** JWK. It verifies fail-closed validation behavior, not TLS, discovery, or JWKS served by a running Keycloak instance.
- Live HTTPS acceptance remains **BLOCKED** until the operator has approved, existing TLS materials and runs the procedure above. Do not replace that evidence with the unit-test result.
- P01 remains **NO-GO / BLOCKED** and AI-9 remains **BLOCKED**.

## Official references

- Keycloak container configuration: https://www.keycloak.org/server/containers
- Keycloak hostname configuration: https://www.keycloak.org/server/hostname
- Keycloak TLS configuration: https://www.keycloak.org/server/enabletls
- Python TLS client verification: https://docs.python.org/3/library/ssl.html#ssl.create_default_context
- Docker Compose bind mounts: https://docs.docker.com/reference/compose-file/services/#volumes
- Devobs's strict token contract: [`oidc_tokens.py`](../scripts/devobs_intelligence/oidc_tokens.py)

## Rollback

This change adds only local tooling and documentation. To roll it back, revert the PR. A local operator should run the project-scoped `docker compose ... down --remove-orphans` command above and remove process-local path variables; no named volumes or persistent credentials are configured.
