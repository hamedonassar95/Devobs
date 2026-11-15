# Dedicated hosted Keycloak candidate — review/plan only

**Current budget decision: no paid activation.** Retain the enforceable all-in
USD 100 ceiling, with a USD 70 planning target and USD 80 intervention threshold.
See the [budget envelope and owner decision](../../docs/P01_RENDER_BUDGET_ENVELOPE.md).

This is a separate service and durable PostgreSQL database, not the disposable
local fixture and not the existing Devobs API database. Nothing in these files
starts a service, creates keys/users or authorizes billing. Keep P01 NO-GO.

The image is pinned to Keycloak 26.8.2 and built with PostgreSQL support. Runtime
uses production `start --optimized --import-realm`, Render edge HTTPS and a
fixed HTTPS issuer derived from the service's provider-supplied external URL.
The backend listener uses `PORT`; management port 9000 is not a public endpoint.
The discovery health check is startup evidence only, not full readiness.

## Verified database blocker — 2026-11-14

**The current private-only Render manifest is NOT APPLYABLE under the required
TLS policy.** [Render's connection documentation](https://render.com/docs/postgresql-creating-connecting#ssl-modes-for-internal-connections)
explicitly states that internal PostgreSQL connections do not support
`sslmode=verify-ca` or `sslmode=verify-full`; their self-signed TLS path supports
`require`. This contradicts the private-only design in `render.yaml`, whose
database has `ipAllowList: []`, while `start.sh` requires certificate and hostname
verification. Supplying a CA file does not establish a supported internal route.
Do not create the paid resources from this manifest or weaken `verify-full`.

A replacement design could use Render's external TLS endpoint with the exact
database hostname/SNI, authenticated CA trust and an explicitly reviewed narrow
allowlist for the service's verified outbound addresses, or a different provider
with a supported certificate-verifying private route. External TLS is documented
by Render, but that alternative's connectivity, certificate validation, egress
addresses, residency and complete cost boundary have not been verified. It needs
a separate reviewed manifest and network approval; do not open the database to
all addresses or treat this paragraph as permission to change an allowlist.

## Offline external-route candidate builder

`scripts/p01_keycloak_external_plan.py` reuses this Blueprint to write a separate
review candidate. It changes only the dedicated database's `ipAllowList`, using
Blueprint `source` entries. It never contacts Render, discovers IPs, reads
credentials, approves spending or deploys. The base manifest remains closed and
blocked. The startup guard now accepts only the Frankfurt Render external
database DNS shape (`dpg-….frankfurt-postgres.render.com`), preserving
`sslmode=verify-full`. DNS shape alone does not prove ownership or TLS trust.

Prepare a public, name-only route inventory with exactly these fields:

```json
{"schema_version": 1, "region": "frankfurt", "outbound_cidrs": []}
```

The empty list intentionally fails. Replace it privately with **all** service
outbound ranges copied from Render's **Connect → Outbound** details for the
reviewed service and region. Do not infer them from one observed connection.
[Render documents](https://render.com/docs/outbound-ip-addresses) that any address
in these ranges may be used and regional ranges are shared by other services;
an allowlist is not service authentication. Dedicated outbound IPs require their
own availability/cost review. The inventory records proposed public ranges,
not evidence that they were verified or approved. Do not include DSNs, passwords,
tokens, environment exports or other fields.

This builder deliberately accepts only canonical public IPv4 `/24` through
`/32` CIDRs, at most 20, without overlaps. Broader provider ranges or IPv6 require
a separately reviewed policy change; never truncate a required provider range
to make it pass. Empty, private/reserved, multicast, all-address, duplicate and
malformed ranges fail with a fixed message and no candidate. This is a local
plan policy, not a statement of Render's API limits.

Using Python's standard library (no new dependency or CI workflow):

```sh
python3 scripts/p01_keycloak_external_plan.py --inventory /path/to/public-route-inventory.json --output /path/to/keycloak-external-review.yaml
python3 -m unittest discover -s tests -p '*keycloak*' -v
```

Exit `0` means **PLAN ONLY**, not readiness. Exit `2` means blocked. Existing
outputs are never overwritten. A SHA-256 drift guard rejects any change to the
reviewed base template; update that guard only after reviewing the new base.
The builder preserves all other template bytes, including Render's `off` enum
strings and actual `false` booleans. Delete a local candidate to undo generation;
the builder has no provider side effects. Review its diff against this base
before considering any provider action. The API's existing database and the
root `render.yaml` are outside its scope.

The generated candidate is **not ready to apply** until service-egress
provenance, the exact callback/PKCE implementation, external database DNS,
authenticated CA, certificate-verifying network connectivity and spending
boundary are resolved. The database hostname and secrets remain manual/private
provider settings; the builder does not invent them. After any separately
approved provisioning, confirm the assigned hostname and egress again before
acceptance. No live connection or identity readiness is established by these
offline checks.

## Before any application of the plan

1. Approve a provider/account/region, exact source SHA and total budget boundary.
2. Review the generated resource plan; leave existing resources unchanged.
3. Supply a real exact HTTPS client callback through Render's private interface.
   The application callback/PKCE flow must exist; this bundle does not add a UI.
4. Resolve the verified database blocker above in a separately reviewed design.
   Only then supply the dedicated database's certificate-validating DNS hostname
   and operator-authenticated public CA at `/etc/secrets/keycloak-db-ca.pem`.
   Prove the approved network route and a real certificate-verifying connection;
   file presence and the existing offline shell test do not prove either.
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
