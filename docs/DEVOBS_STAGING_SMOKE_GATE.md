# DevObs managed Staging — manual evidence gate

**Status:** proposed GitHub Actions validation gate only; NOT a deployed service.

This read-only smoke gate is tied to [P01 #221](https://github.com/hamedonassar95/Devobs/issues/221) and the [master production program #233](https://github.com/hamedonassar95/Devobs/issues/233).

## Contract

The script `scripts/devobs_intelligence/staging_smoke.py` performs these
**six HTTPS GET requests in order**, always to the same validated, pinned
`*.onrender.com` origin:

1. `GET /healthz` -> HTTP **204** (process liveness).
2. `GET /readyz` -> HTTP **204** (DB role/RLS readiness).
3. `GET /v1/tenants/{tenant}/projects/{project}/ci` without a token ->
   HTTP **401**, exact JSON `{"error":"invalid_token"}`.
4. Same path with a trusted, short-lived signed access token -> HTTP
   **200**, exact `ci_state` plus valid 40/64-character lowercase SHA.
5. Same project ID under the **other** tenant, using a **different** signed
   token authorized for that tenant -> HTTP **200**. This proves the fixture
   exists before checking isolation.
6. Same other-tenant project using the original signed token -> HTTP **403**,
   exact JSON `{"error":"access_denied"}`.

Responses must have `Cache-Control: no-store`, JSON where appropriate,
bounded bodies. No HTTP redirects are followed, no POST, DB migration,
provider API call, self-provisioning or automatic cleanup is executed.
Failures are fixed, non-sensitive codes without token, URL or response-body
echoes. This is a one-time check, not a background monitor or an SLO claim.

## GitHub environment setup — external operator work, not performed here

The workflow `.github/workflows/devobs-staging-smoke.yml` is
`workflow_dispatch` **only**, on protected `main`, with
`contents: read` and environment `devobs-staging`.

An authorized operator must first create and protect that GitHub Environment:
require a human reviewer and restrict allowed branches to protected main.
The workflow itself does not establish that protection. The repository's
account plan must support environment protection and secrets.

Supply the following **environment variables** (not sensitive):

| Name | Description |
| --- | --- |
| `DEVOBS_STAGING_BASE_URL` | Independently verified HTTPS origin, e.g. an actual assigned Render `onrender.com` hostname |
| `DEVOBS_STAGING_EXPECTED_HOST` | Exact verified hostname, same one as URL; prevents accidental off-target request |
| `DEVOBS_STAGING_TENANT` | Approved synthetic tenant id for a test member |
| `DEVOBS_STAGING_PROJECT` | Existing synthetic project in that tenant |
| `DEVOBS_STAGING_DENIED_TENANT` | Different synthetic tenant with an **existing project using the same project ID**; original member must not be a member |

Supply two separate **environment secrets**:

- `DEVOBS_STAGING_TOKEN`: short-lived OAuth JWT **access** token scoped
  `devobs.read`, signed for the authentic target issuer and client, with
  a maximum 15-minute lifetime. It MUST be placed by an authorized operator
  just before manual execution; it will expire.
- `DEVOBS_STAGING_DENIED_TENANT_TOKEN`: **different**, short-lived signed
  access token for an authorized member of the other synthetic tenant and
  its independently seeded same-ID project. The test requires a successful
  read with this token before it accepts the original token's 403 as proof
  of isolation. A 403 for a missing project is not sufficient. Do not store private signing
  keys, refresh tokens, long-lived production API keys or customer credentials
  in GitHub. A future **workload identity federation** flow is needed before
  recurring/automated smoke checks can be safe and reliable.

Do not point these variables at `Phone Repair Assistant v2` or any shared
customer project. Do not use a real customer's data even for a denied case.

## How the operator later runs a test

On the protected default branch after reviewed merge and after Staging actually
exists, select GitHub Actions `DevObs Staging Contract Smoke (manual read-only)`
and run the workflow. GitHub Environments may hold the job pending human
approval if a protection rule is configured. An unset/invalid URL, scope or
token fails closed *before* any network request.

**Passing result proves only the six HTTP assertions at that moment.** It
does not prove credential lifecycle, multi-worker OIDC key rotation,
PostgreSQL pool/lock performance, tenancy for arbitrary users, network
perimeter, cloud backup restore, DDoS controls, SLO or commercial suitability.

## Reproducible offline test command

```bash
python3 -m unittest discover -s tests -p 'test_devobs_staging_smoke.py' -v
```

These tests use a synthetic fake transport and never call the live Staging
service. The workflow is safe to review/merge without activating it.

## Official reference documentation

- GitHub Environments/secrets/protection:
  https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- GitHub environment setup:
  https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
- Render HTTP health checks:
  https://render.com/docs/health-checks
- Render Blueprint auto deploy off:
  https://render.com/docs/blueprint-spec
- Supabase Postgres hostname/certificate verification:
  https://supabase.com/docs/guides/platform/ssl-enforcement

## Blocking next actions

- [ ] Authorize and create a **distinct** DevObs Supabase project and a
      dedicated least-privileged runtime role. Quote and approve any cost first.
- [ ] Deploy and verify a dedicated Render Staging service, trusted CA and
      OIDC provider with a short-lived test access token. Do not enable auto deploy.
- [ ] Configure protected GitHub Staging Environment and explicit variables.
- [ ] Run the hosted smoke, save exact SHA and result links in issue #221.
- [ ] Run backup **restore**, load/latency, leak, stale-keys, and real
      cross-tenant attacks before any production go/no-go decision.

**Never mark production ready from source-code CI alone.**
