# P01 local Keycloak HTTPS discovery and JWKS preflight

**Live runtime status: NOT_TESTED.** This change reconciles the policy proposed by PR #608; it does not start or authorize a service while this reconciliation PR is unmerged. The exception is effective only after this reconciliation PR is merged, and each runtime test still requires separate explicit owner approval. No certificate, private key, password, token, or production setting was accessed. Existing automated tests use synthetic public JWKS and injected responses; they are offline contract evidence only.

## Verified baseline

- Current base/source SHA: `c65d904434bc70102ed5f1df5271611f99ff14bf`. PR [#608](https://github.com/hamedonassar95/Devobs/pull/608) merged at this SHA from reviewed head `39cf6e708a4dae854a964874263c479ff9853c12`. Exact-SHA post-merge CI [43593864381](https://github.com/hamedonassar95/Devobs/actions/runs/43593864381) and CodeQL [43593864050](https://github.com/hamedonassar95/Devobs/actions/runs/43593864050) succeeded. Within CI, Node tests, Python tests, and the controlled incident drill were skipped by existing path/condition rules; separate Incident Response and Claude issue-comment runs were skipped because their events did not apply. PR #608 introduced the exception proposal; this reconciliation defines its activation boundary.
- Previous base: PR [#607](https://github.com/hamedonassar95/Devobs/pull/607) merged at `5f1a4e6b909f7b1b7d1af218bc059e35c40b698c`; exact-SHA post-merge CI [43592555815](https://github.com/hamedonassar95/Devobs/actions/runs/43592555815) and CodeQL [43592555702](https://github.com/hamedonassar95/Devobs/actions/runs/43592555702) succeeded. Incident Response run [43592679051](https://github.com/hamedonassar95/Devobs/actions/runs/43592679051) was skipped by its condition.
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

### Policy activation and per-run authorization

The exception introduced by merged PR #608 is effective only after **this reconciliation PR is merged to `main`**. Until this reconciliation PR is merged, the general secret-handling prohibition in [`AGENTS.md`](../AGENTS.md) remains binding and Keycloak must not be started. Merging this reconciliation makes only the narrow exception described there effective; it does not authorize a runtime test by itself.

After activation, every runtime test requires separate explicit owner approval for every runtime test run. The approval must identify the full reviewed source SHA (40-character SHA), a unique Docker Compose project name, and the exact test scope. No standing or earlier approval carries forward. Use this template, filling in every placeholder:

> I approve one local Keycloak HTTPS discovery/JWKS preflight runtime test for source SHA `<full-40-character-reviewed-SHA>`, Compose project `<unique-project-name>`, exact scope `<HTTPS discovery and public JWKS checks only>`. I authorize only Keycloak 26.8.2 at the existing pinned digest to automatically generate and internally use disposable realm signing material inside that test container. Use synthetic identities only, the existing synthetic realm, a local Unix-socket Docker context, the exact loopback port mapping `127.0.0.1:443:8443`, and operator-managed TLS certificate/key/public-CA files with read-only certificate/key mounts. Do not issue tokens; access production accounts or customer data; access hosted identity providers, Render, PostgreSQL, Supabase, or cloud resources; inspect, export, copy, print, commit, or log private keys; log credentials or tokens; capture raw secret-bearing logs; or change hosted settings. Remove only the named Compose project, confirm its containers and network are gone, and return sanitized PASS/FAIL/BLOCKED evidence.

This approval authorizes no users, passwords, client secrets, access tokens, administrator credentials, hosted identity, paid AI inference, cloud changes, deployment, or production operation. A future signed-token acceptance test would have a different scope and require its own reviewed implementation and per-run owner approval.

Never export, inspect, copy, print, or commit private signing keys. Never log credentials or tokens or capture raw secret-bearing logs. The exception covers no production account or customer data, hosted identity provider, Render/PostgreSQL/Supabase configuration, cloud resource, paid inference, or production deployment.

### Operator-only runtime procedure after activation and approval

Do not run this procedure unless the reconciliation PR is already merged and a separate approval for this exact source SHA, unique project, and discovery/JWKS-only scope is recorded. The project is not started by this policy change. The operator must supply an already managed localhost TLS certificate chain, matching private key, and public CA certificate; certificate ownership remains with the operator, independently of the disposable realm signing-key exception. The certificate must contain `DNS:localhost` in its SAN and be valid for TLS server authentication. Keep the TLS private key outside the repository. Codex must not open, inspect, generate, or modify the certificate or private-key material. The existing Compose file mounts the certificate/key read-only; `--ca-cert` accepts only a public CA certificate.

Run from a local Unix-like shell whose selected Docker endpoint is a local Unix socket. Check the selected context and endpoint with Docker's official [`docker context show`](https://docs.docker.com/reference/cli/docker/context/show/) and [`docker context inspect`](https://docs.docker.com/reference/cli/docker/context/inspect/) commands. Verify locally that the endpoint is a Unix socket; any `ssh://`, `tcp://`, named-pipe, cloud, or remote endpoint is **BLOCKED**. On systems where Docker is exposed only through a named pipe, do not use that context; the test requires an approved local Unix-socket context. Check that host port 443 is free before starting. If occupied or unavailable, stop without terminating another process or choosing another port.

Use a unique project name exactly matching the per-run approval. The example below only describes the operator procedure; it was not executed in this task. Supply paths to existing TLS material, never the file contents:

```sh
set -eu
project='devobs-kc-https-REPLACE-WITH-APPROVED-UNIQUE-SUFFIX'
compose='dev/keycloak/compose.https.local.yaml'
export DEVOBS_KEYCLOAK_TLS_CERT_FILE='/absolute/path/to/operator-managed-localhost-chain.pem'
export DEVOBS_KEYCLOAK_TLS_KEY_FILE='/absolute/path/to/operator-managed-localhost-key.pem'
cleanup() {
  docker compose -p "$project" -f "$compose" down --remove-orphans
  unset DEVOBS_KEYCLOAK_TLS_CERT_FILE DEVOBS_KEYCLOAK_TLS_KEY_FILE
}
trap cleanup EXIT HUP INT TERM
docker compose -p "$project" -f "$compose" config --quiet
docker compose -p "$project" -f "$compose" up -d keycloak
python3 scripts/p01_keycloak_https_preflight.py --ca-cert '/absolute/path/to/operator-managed-public-test-ca.pem'
docker compose -p "$project" -f "$compose" down --remove-orphans
trap - EXIT HUP INT TERM
unset DEVOBS_KEYCLOAK_TLS_CERT_FILE DEVOBS_KEYCLOAK_TLS_KEY_FILE
```

After success or failure, verify only this project's containers and network are gone. Do not set Keycloak admin bootstrap variables, use broad Docker cleanup commands, read container logs, or inspect environment output. `docker compose config --quiet` checks Compose syntax only; it does not prove certificate availability, port binding, or a live Keycloak response. If cleanup cannot be confirmed, report **BLOCKED** and do not touch unrelated Docker resources.

The preflight makes at most two fixed-path HTTPS GET requests. It follows no redirects and does not accept arbitrary hosts or URLs. Its successful result is `LOCAL_HTTPS_OIDC_PREFLIGHT_PASS`, with `certificate_verification: PASS`, `signed_token_acceptance: NOT_TESTED`, and `readiness_claim: NOT_ESTABLISHED`.

## What this does and does not establish

Offline tests can establish that the checker uses the exact standard-port URLs, rejects a nonstandard issuer port and mismatched JWKS origin, requires TLS chain and hostname verification, rejects redirects and network failures, and fails closed on incompatible public signing keys. A live run, when an operator performs it, can establish only certificate-verified local discovery and public-JWKS compatibility.

Neither offline tests nor this discovery/JWKS preflight establish that a Keycloak-issued access token passes Devobs validation. A separate approved test would need an actual Keycloak-issued token and must verify its signature and claims, including `typ=at+jwt`, exact single-string audience, exact `client_id`, subject, token ID, issue/expiry times, maximum 900-second lifetime, and the required `devobs.read` scope. This work creates no user, client credential, token, signing key, or identity.

Hosted Render configuration, database connectivity and RLS, tenant isolation, provider billing, backup/restore, production TLS, AI-9 natural-incident validation, and staging acceptance are outside this local preflight. **P01 remains NO-GO / BLOCKED and AI-9 remains BLOCKED.** No result here authorizes a production change.

## Verification evidence and limits

- Base SHA, merged PR #608, and its exact post-merge CI/CodeQL runs are recorded above. PR #607 and PR #606 evidence is included only as earlier history; none of those runs is evidence for changes in this branch.
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
