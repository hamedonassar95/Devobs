# Dedicated hosted Keycloak candidate — review/plan only

This is a separate service and durable PostgreSQL database, not the disposable
local fixture and not the existing Devobs API database. Nothing in these files
starts a service, creates keys/users or authorizes billing. Keep P01 NO-GO.

The image is pinned to Keycloak 26.8.2 and built with PostgreSQL support. Runtime
uses production `start --optimized --import-realm`, Render edge HTTPS and a
fixed HTTPS issuer derived from the service's provider-supplied external URL.
The backend listener uses `PORT`; management port 9000 is not a public endpoint.
The discovery health check is startup evidence only, not full readiness.

## Before any application of the plan

1. Approve a provider/account/region, exact source SHA and total budget boundary.
2. Review the generated resource plan; leave existing resources unchanged.
3. Supply a real exact HTTPS client callback through Render's private interface.
   The application callback/PKCE flow must exist; this bundle does not add a UI.
4. Supply the dedicated database's certificate-validating DNS hostname and mount
   its operator-authenticated public CA as `/etc/secrets/keycloak-db-ca.pem`.
   Verify network access without opening the database to the public internet.
   The template deliberately does not guess Render's private certificate identity
   or weaken TLS to `require`. If hostname/CA/network verification is unavailable,
   stop before approving the plan. The operator must finish this connectivity
   design; the template does not establish Render database TLS compatibility.
5. Password references and the bootstrap password are generated/resolved by
   Render, not put in Git or chat. Only the owner retrieves the temporary admin
   credential through the provider's private interface. Replace that temporary
   account with an appropriately protected administrator and remove it afterward.

The startup guard rejects incomplete configuration without echoing values.
PostgreSQL JDBC uses `verify-full`; checking file presence does not validate the
CA or prove a live TLS handshake. Existing realm imports are skipped: later realm
changes need a controlled migration, not an assumed JSON overwrite.

The public client enables S256 PKCE and authorization code only, RS256,
`at+jwt`, 300-second access tokens, one intended audience, explicit `client_id`,
and optional `devobs.read`. There are no users, embedded credentials, diagnosis
scope or broad default scopes. Live token compatibility remains unverified.

## Published price baseline — checked 2026-11-14

- 2 GB web compute (`1c-2g`): **$25/month**.
- Dedicated PostgreSQL (`0.1c-256mb`): **$6/month**.
- 5 GB database storage at $0.30/GB: **$1.50/month**.
- Baseline: **$32.50/month**, excluding taxes, bandwidth/build overages,
  workspace charges, backup-related charges and existing resources. This is not
  an all-in invoice quote or proof of the owner's <=$100 automatic-stop condition.

Render Free is 512 MB and has no persistent disk. Keycloak's guide recommends
at least 750 MB to approach its previous heap default and 2 GB for a small
production deployment. Do not describe Free as a validated durable identity host.
No payment method is currently confirmed for the workspace; do not apply paid
resources without a separate reviewed spending decision and enforceable boundary.

## Acceptance and rollback

Require HTTPS discovery/JWKS, a real synthetic PKCE login/token accepted by the
unchanged Devobs verifier, denial tests, key rotation, restart persistence and a
backup/restore rehearsal before installing this issuer in the API. Persisting
signing material does not prove restore safety. Record exact SHA and results.
Rollback must protect/export data through approved operator procedures; do not
blindly delete the identity database or switch trust back to stale keys.

References: [Keycloak containers](https://www.keycloak.org/server/containers),
[database](https://www.keycloak.org/server/db), [hostname](https://www.keycloak.org/server/hostname),
[proxy](https://www.keycloak.org/server/reverseproxy), [realm import](https://www.keycloak.org/server/importExport),
[bootstrap admin](https://www.keycloak.org/server/bootstrap-admin-recovery),
[Render Blueprint](https://render.com/docs/blueprint-spec), [pricing](https://render.com/pricing),
[Free limits](https://render.com/docs/free), [backups](https://render.com/docs/postgresql-backups).
