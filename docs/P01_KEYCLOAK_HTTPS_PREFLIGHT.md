# P01 local Keycloak HTTPS discovery and JWKS preflight

**Live runtime status: NOT_TESTED.** This change aligns the disposable local fixture with Devobs's HTTPS-only issuer policy. No Keycloak service was started, and no certificate, private key, password, token, or production setting was accessed. The automated tests use synthetic public JWKS and injected responses; they are offline contract evidence only.

## Verified baseline

- Base and tested source SHA: `cf2f879c2dfe8ed6498d850aeccbb25244255231`.
- PR [#606](https://github.com/hamedonassar95/Devobs/pull/606) merged at this SHA. Exact-SHA post-merge CI run [43591660408](https://github.com/hamedonassar95/Devobs/actions/runs/43591660408) and CodeQL run [43591660220](https://github.com/hamedonassar95/Devobs/actions/runs/43591660220) succeeded. The incident-response and Claude issue-comment workflows were skipped because their events did not apply.
- Compose retains the pinned Keycloak image `quay.io/keycloak/keycloak:26.8.2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0` and the existing `devobs-local` realm, including the public PKCE client configured by PR #606.

## Port and issuer contract

The fixture publishes **host `127.0.0.1:443` to container port `8443`**. Keycloak's internal HTTPS listener remains on 8443, HTTP remains disabled, and the externally advertised hostname is `https://localhost` with the standard HTTPS port omitted. The exact issuer and JWKS URL are:

- Issuer: `https://localhost/realms/devobs-local`
- JWKS: `https://localhost/realms/devobs-local/protocol/openid-connect/certs`

The image digest, internal HTTPS listener, isolated network, and operator-managed certificate and private-key bind mounts remain unchanged. The certificate and key mounts are read-only and use `create_host_path: false`; this repository neither creates nor reads the private key.

The checker accepts only those exact documents over verified HTTPS. It resolves `localhost`, rejects any non-loopback answer, pins its connection to the resolved loopback address on port 443, requires `CERT_REQUIRED` and `check_hostname=True`, uses only the operator-supplied public CA, limits response sizes and time, and rejects redirects. It passes the authenticated discovery document and JWKS to the existing `trusted_oidc_verifier` contract. That helper continues to enforce HTTPS on the standard port, exact issuer equality, same-origin JWKS, and the repository's public RS256 key requirements. The production verifier and its policies are unchanged.

If host port 443 is already occupied or cannot be bound, treat the local runtime attempt as **BLOCKED**. Do not stop another process or substitute port 8443 or another port: doing so would change the issuer and fail the intended policy check.

## Operator-only local runtime procedure

This procedure is for a future operator-run smoke test with an already approved local TLS certificate chain, matching private key, and public CA certificate. The server certificate must contain `DNS:localhost` in its SAN and be valid for TLS server authentication. Store the private key outside the repository and do not paste, print, or upload it. The `--ca-cert` argument accepts a public CA certificate only.

First verify that loopback port 443 is free. For example, on PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 443 -State Listen -ErrorAction SilentlyContinue
```

If a listener is returned, stop and report **BLOCKED**. Do not terminate it. Then set process-local variables to paths only and use a unique Compose project name:

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

Run the project-scoped `down` command and remove the process-local variables after every attempt, including a failed startup or preflight. Do not set Keycloak admin bootstrap variables. Do not use a remote Docker context. `docker compose config --quiet` checks Compose syntax but does not check certificate availability, bind permission, or a live Keycloak response.

The preflight makes at most two fixed-path HTTPS GET requests. It follows no redirects and does not accept arbitrary hosts or URLs. Its successful result is `LOCAL_HTTPS_OIDC_PREFLIGHT_PASS`, with `certificate_verification: PASS`, `signed_token_acceptance: NOT_TESTED`, and `readiness_claim: NOT_ESTABLISHED`.

## What this does and does not establish

Offline tests can establish that the checker uses the exact standard-port URLs, rejects a nonstandard issuer port and mismatched JWKS origin, requires TLS chain and hostname verification, rejects redirects and network failures, and fails closed on incompatible public signing keys. A live run, when an operator performs it, can establish only certificate-verified local discovery and public-JWKS compatibility.

Neither offline tests nor this discovery/JWKS preflight establish that a Keycloak-issued access token passes Devobs validation. A separate approved test would need an actual Keycloak-issued token and must verify its signature and claims, including `typ=at+jwt`, exact single-string audience, exact `client_id`, subject, token ID, issue/expiry times, maximum 900-second lifetime, and the required `devobs.read` scope. This work creates no user, client credential, token, signing key, or identity.

Hosted Render configuration, database connectivity and RLS, tenant isolation, provider billing, backup/restore, production TLS, AI-9 natural-incident validation, and staging acceptance are outside this local preflight. **P01 remains NO-GO / BLOCKED and AI-9 remains BLOCKED.** No result here authorizes a production change.

## Verification evidence and limits

- Base SHA, PR #606, and its exact post-merge CI/CodeQL runs are recorded above; those historical checks are not evidence for changes in this branch.
- `docker compose -f dev/keycloak/compose.https.local.yaml config --quiet` validates only the Compose document.
- `tests/test_p01_keycloak_https_preflight.py` uses synthetic public-only JWKs and injected HTTP response data. It does not establish a live TLS connection or test a running Keycloak service.
- Host port availability checked on the implementation environment: **available at check time**. This does not establish availability on an operator's machine.
- Actual HTTPS runtime acceptance and signed-token acceptance: **NOT_TESTED**.

## Official references

- Keycloak container configuration: https://www.keycloak.org/server/containers
- Keycloak hostname configuration: https://www.keycloak.org/server/hostname
- Keycloak TLS configuration: https://www.keycloak.org/server/enabletls
- Python TLS client verification: https://docs.python.org/3/library/ssl.html#ssl.create_default_context
- Docker Compose port publishing: https://docs.docker.com/reference/compose-file/services/#ports
- Devobs strict metadata contract: [`oidc_metadata.py`](../scripts/devobs_intelligence/oidc_metadata.py)
- Devobs token contract: [`oidc_tokens.py`](../scripts/devobs_intelligence/oidc_tokens.py)

## Rollback

This change only modifies the local fixture, offline checker/tests, and documentation. Revert the PR to roll it back. If an operator has run the fixture, remove only its uniquely named Compose project with `docker compose -p <project> -f dev/keycloak/compose.https.local.yaml down --remove-orphans` and clear the process-local path variables. No named volumes or persistent credentials are configured.
