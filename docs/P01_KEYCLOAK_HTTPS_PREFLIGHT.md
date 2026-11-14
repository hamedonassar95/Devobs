# P01 local Keycloak HTTPS discovery and JWKS preflight

**Live runtime status: NOT_TESTED.** This PR proposes a review-only exception for the disposable Keycloak runtime check; it does not authorize or start a service. No certificate, private key, password, token, or production setting was accessed. Existing automated tests use synthetic public JWKS and injected responses; they are offline contract evidence only.

## Verified baseline

- Current base/source SHA: `5f1a4e6b909f7b1b7d1af218bc059e35c40b698c`. PR [#607](https://github.com/hamedonassar95/Devobs/pull/607) merged at this SHA; exact-SHA post-merge CI [43592555815](https://github.com/hamedonassar95/Devobs/actions/runs/43592555815) and CodeQL [43592555702](https://github.com/hamedonassar95/Devobs/actions/runs/43592555702) succeeded. Incident Response run [43592679051](https://github.com/hamedonassar95/Devobs/actions/runs/43592679051) was skipped by its condition.
- PR [#606](https://github.com/hamedonassar95/Devobs/pull/606) added the disposable public OAuth client configuration at merge SHA `cf2f879c2dfe8ed6498d850aeccbb25244255231`. Its exact-SHA post-merge CI run [43591660408](https://github.com/hamedonassar95/Devobs/actions/runs/43591660408) and CodeQL run [43591660220](https://github.com/hamedonassar95/Devobs/actions/runs/43591660220) succeeded; the incident-response and Claude issue-comment workflows were skipped because their events did not apply.
- Compose retains the pinned Keycloak image `quay.io/keycloak/keycloak:26.8.2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0` and the existing `devobs-local` realm, including the public PKCE client configured by PR #606.

## Port and issuer contract

The fixture publishes **host `127.0.0.1:443` to container port `8443`**. Keycloak's internal HTTPS listener remains on 8443, HTTP remains disabled, and the externally advertised hostname is `https://localhost` with the standard HTTPS port omitted. The exact issuer and JWKS URL are:

- Issuer: `https://localhost/realms/devobs-local`
- JWKS: `https://localhost/realms/devobs-local/protocol/openid-connect/certs`

The image digest, internal HTTPS listener, isolated network, and operator-managed certificate and private-key bind mounts remain unchanged. The certificate and key mounts are read-only and use `create_host_path: false`; this repository neither creates nor reads the private key.

The checker accepts only those exact documents over verified HTTPS. It resolves `localhost`, rejects any non-loopback answer, pins its connection to the resolved loopback address on port 443, requires `CERT_REQUIRED` and `check_hostname=True`, uses only the operator-supplied public CA, limits response sizes and time, and rejects redirects. It passes the authenticated discovery document and JWKS to the existing `trusted_oidc_verifier` contract. That helper continues to enforce HTTPS on the standard port, exact issuer equality, same-origin JWKS, and the repository's public RS256 key requirements. The production verifier and its policies are unchanged.

If host port 443 is already occupied or cannot be bound, treat the local runtime attempt as **BLOCKED**. Do not stop another process or substitute port 8443 or another port: doing so would change the issuer and fail the intended policy check.

## Operator-only local runtime procedure

### Proposed policy exception — PROPOSED, not active

The current root policy prohibits creating secrets and keys. That blocks starting Keycloak for runtime acceptance because the official [Keycloak 26.8.2 Server Administration Guide](https://www.keycloak.org/docs/26.8.2/server_admin/#realm_keys) says realm creation automatically generates a signing key pair and self-signed certificate. This PR proposes a narrow exception for Keycloak to generate and use that realm signing material only inside the existing disposable local container. The proposal is **not authorization to run the test**: until the owner reviews and merges the policy PR, the current prohibition remains in force.

After the policy PR is merged, the owner must explicitly approve each individual run, tied to the exact source SHA and unique Compose project. A standing approval does not suffice. The approval should use this exact template with both placeholders filled:

> I approve one local Keycloak HTTPS runtime test for source SHA `<full-reviewed-SHA>` using Compose project `<unique-project-name>`. I authorize only the pinned Keycloak 26.8.2 container to generate and use temporary realm signing material inside that disposable local container. Use synthetic identities only, the existing loopback-only `127.0.0.1:443:8443` fixture, and operator-managed TLS files mounted read-only. Do not access production accounts, inspect or export private keys, log credentials or tokens, copy private material into Git, or change hosted settings. Verify project-scoped container and network cleanup and return sanitized PASS/FAIL/BLOCKED evidence.

This approval authorizes no user, password, client secret, access token, administrator credential, hosted identity, or production operation. This preflight does not need an authenticated identity. If a future token-acceptance test needs synthetic users or tokens, it requires its own reviewed scope and per-run approval.

### Runtime procedure after policy approval

Only after the proposed exception is approved and merged **and** the owner has given the per-run approval above may an operator run this procedure. Use an already approved local TLS certificate chain, matching private key, and public CA certificate. The server certificate must contain `DNS:localhost` in its SAN and be valid for TLS server authentication. Store the private key outside the repository; the agent must not open or inspect it. The existing Compose file mounts it read-only, and the `--ca-cert` argument accepts a public CA certificate only.

Before running Docker, check the active context and inspect its Docker endpoint using the official [`docker context show`](https://docs.docker.com/reference/cli/docker/context/show/) and [`docker context inspect`](https://docs.docker.com/reference/cli/docker/context/inspect/) commands. A remote Docker endpoint is **BLOCKED**. Also check that loopback port 443 is free; if not, stop without terminating another process or choosing a different port. Use a unique project name; the fixture has no named data volume and the generated Keycloak signing material must remain only in the disposable container layer.

On PowerShell, confirm that no process is listening on port 443:

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

- Base SHA, PR #607, and its exact post-merge CI/CodeQL runs are recorded above. PR #606 evidence is included only as earlier client-configuration history; neither historical run is evidence for changes in this branch.
- `docker compose -f dev/keycloak/compose.https.local.yaml config --quiet` validates only the Compose document.
- `tests/test_p01_keycloak_https_preflight.py` uses synthetic public-only JWKs and injected HTTP response data. It does not establish a live TLS connection or test a running Keycloak service.
- Port availability and live Docker context were not checked in this policy-only task.
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

This change modifies policy guidance and documentation only; it creates no container, key, certificate, identity, token, or persistent data. Revert the PR to roll it back. If a separately approved future run starts the fixture, remove only its uniquely named Compose project with `docker compose -p <project> -f dev/keycloak/compose.https.local.yaml down --remove-orphans`, verify its container and network are gone, and clear process-local path variables. No named volumes or persistent credentials are configured.
