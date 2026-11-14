# P01 Keycloak 26.8.2 localhost smoke evidence

**Result: PASS — disposable localhost-only runtime smoke.** This proves the pinned local container served the expected discovery document and a compatible public RS256 JWKS during this test. It does not prove production identity readiness.

## Source and merged implementation

- Tested source SHA: `6966e67b48a84113c430b8b6697c3c566cbcdcb0` (`origin/main` at test time).
- PR [#603](https://github.com/hamedonassar95/Devobs/pull/603) merged from head `d527fd72736aa77373a4203a7a14e1365b5beeea` to that exact SHA.
- Post-merge main CI [43530151710](https://github.com/hamedonassar95/Devobs/actions/runs/43530151710) and CodeQL [43530151098](https://github.com/hamedonassar95/Devobs/actions/runs/43530151098) succeeded on the exact merge SHA.
- Reused without modification: `dev/keycloak/compose.local.yaml`, `dev/keycloak/realm.local.json`, and `scripts/p01_keycloak_local_preflight.py`.

## Runtime evidence

Tested 2026-11-13 UTC on the local execution host. Docker used its verified local Unix socket context; no remote Docker daemon was selected. `127.0.0.1:8080` was available immediately before startup.

| Check or command | Evidence | Exit |
| --- | --- | ---: |
| `docker version --format '{{.Client.Version}}|{{.Server.Version}}'` | Client/server `28.4.0` | 0 |
| `docker compose version` | Docker Compose v2.40.3 | 0 |
| `docker info` | Engine info command succeeded; raw output was not recorded | 0 |
| `docker compose -f dev/keycloak/compose.local.yaml config --quiet` | Compose configuration accepted | 0 |
| Image pin check | `quay.io/keycloak/keycloak:26.8.2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0` matched exactly | 0 |
| `docker compose -p p01kcsmoke-2210d5f5a4 -f dev/keycloak/compose.local.yaml up -d keycloak` | Only the existing Keycloak service started; configured image reference matched the pinned digest | 0 |
| Bounded discovery startup poll | Discovery returned HTTP 200 on attempt 10 of at most 18; issuer matched `http://127.0.0.1:8080/realms/devobs-local`; JWKS URI matched the realm's local `/protocol/openid-connect/certs` endpoint. All advertised HTTP(S) URLs were local. | PASS |
| `python3 scripts/p01_keycloak_local_preflight.py` | `LOCAL_OIDC_PREFLIGHT_PASS`; one compatible public RS256 key; no redirect followed; `NOT_COMPATIBLE_WITH_LOCAL_HTTP`; `readiness_claim: NOT_ESTABLISHED` | 0 |
| `docker compose -p p01kcsmoke-2210d5f5a4 -f dev/keycloak/compose.local.yaml down --remove-orphans` | Test project's container and network removed | 0 |
| `docker ps -aq --filter label=com.docker.compose.project=p01kcsmoke-2210d5f5a4` | No matching container IDs | 0 |
| `docker network ls -q --filter label=com.docker.compose.project=p01kcsmoke-2210d5f5a4` | No matching network IDs | 0 |

The image remains pinned to the Quay OCI index digest. PR #603's implementation record documents the official registry digest verification and Keycloak source links. The imported realm file has empty `users` and `clients`; no application users or OAuth clients were created or configured by this test. No credentials, tokens, environment values, or raw container logs were read or recorded. Keycloak's internal signing material was not inspected or exported; the container was removed. No external IdP, Render/Supabase service, cloud resource, paid service, or AI inference was used. The downloaded public image may remain in the local Docker image cache; it was not removed because image cleanup could affect other local work.

## Regression checks

- `python3 -m unittest discover -s tests -p 'test_p01_keycloak_local_preflight.py' -v`: 15 passed, exit 0. These use synthetic loopback HTTP fixtures; they are separate from the real Docker smoke above.
- `python3 -m unittest discover -s tests -p 'test_intelligence_keycloak_profile.py' -v`: 9 passed, exit 0.
- `python3 scripts/milestone_ledger.py --summary`: exit 0. P01 remains BLOCKED / NO-GO and AI-9 remains BLOCKED.
- `python3 scripts/check_site.py`: passed, exit 0.
- `git diff --check`: passed, exit 0.

## Limits and next acceptance stage

This runtime check uses HTTP on loopback. Devobs's production issuer verifier requires HTTPS, so this local issuer cannot be used as production OIDC configuration. Discovery/JWKS success is not a signed-token acceptance test; it does not test `typ=at+jwt`, audience, `client_id`, access-token claims/scopes, HTTPS certificate validation, or key rotation. Those checks require a separately approved HTTPS interoperability test with the existing verifier. No users or clients have been registered, and no hosted values have been entered.

The test also does not establish Render startup, database/RLS readiness, budget enforcement, backup/restore, or AI-9 quality. P01 remains **NO-GO / BLOCKED** and AI-9 remains **BLOCKED**.

## Cleanup and rollback

Cleanup was confirmed for the unique Compose project; no test container or network remains. If this documentation PR is not accepted, close it and delete its feature branch. If merged, revert the PR through GitHub. A future manual rerun should use a new unique Compose project name and remove only that project with `docker compose ... down --remove-orphans`; do not prune shared Docker images or resources.
