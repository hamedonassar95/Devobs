# P01 Render budget envelope — paid activation blocked

**Owner decision:** retain the enforceable all-in USD 100/month ceiling;
**do not activate paid resources now**. The owner chose this explicitly after
reviewing the difference between a monitored estimate and a guaranteed stop.
Standing source/CI/merge authorization does not waive this spending condition.
P01 remains **NO-GO / BLOCKED**; no paid pilot or invoice overrun was accepted.

## Planning amounts, not configured billing controls

| Amount | Meaning |
| --- | --- |
| USD 70/month | Operating planning target for the small synthetic stack. |
| USD 80/month | Intervention threshold, matching the historical 80% stop rule. |
| USD 100/month | Maximum combined monthly invoice, conditional on verified enforcement. |
| USD 0 | New paid activation and paid inference authorized at this checkpoint. |

The 70/80/100 amounts are planning decisions. They are not provider limits,
implemented monitoring, automatic service suspension or a guarantee of billing.
Do not ask the owner to pick a generic monthly ceiling again; first resolve
the documented enforcement gap or obtain an explicit revision of this condition.

The canonical historical ceiling and 80% stop rule remain in
[P01 activation readiness](P01_ACTIVATION_READINESS.md). The old USD 10 planning
target is marked superseded in [the earlier comparison](P01_REGION_BUDGET_SECURITY.md).

## Public list-price baseline checked for this decision

Source revision: `12c870be9671ab6c41a17f14280af663aa54e8c4`.
Official [Render pricing](https://render.com/pricing) was fetched for this
review. Prices below are estimates before tax, usage, temporary restore
resources, backup automation and unlisted account charges, not an invoice quote.
Actual workspace tier, eligibility, existing usage and tax treatment are unverified.

| Proposed component | Monthly compute/storage baseline |
| --- | ---: |
| Keycloak web, `1c-2g` | USD 25.00 |
| Separate Keycloak Postgres, `0.1c-256mb`, 5 GB | USD 7.50 |
| Devobs API web, `0.5c-512mb` | USD 7.00 |
| Separate API Postgres, `0.1c-256mb`, 5 GB | USD 7.50 |
| Node console web, `0.5c-512mb` | USD 7.00 |
| **Hobby workspace baseline** | **USD 54.00** |
| Pro workspace fee, if selected | **Additional USD 25.00; USD 79.00 baseline** |

Each database subtotal is USD 6 compute plus 5 GB at USD 0.30/GB/month.
The earlier USD 32.50 figure covers Keycloak and its database only. The small
API/console/database sizes are capacity assumptions, not load-tested production
sizing. The [Keycloak guide](https://www.keycloak.org/server/containers) recommends
2 GB for a small production-ready deployment; Free 512 MB is not a validated
substitute. Dedicated outbound IP sets are excluded: the published USD 100/set
monthly charge plus Pro alone would exhaust this envelope.

## Backup and financial gaps prevent application

**VERIFIED — backup product limits:** [Render backups](https://render.com/docs/postgresql-backups)
document three days of PITR on Hobby and seven on Pro+. Logical exports are
retained seven days on either tier, but documented user-triggered exports do
not prove a daily schedule, RPO/RTO or an isolated restore. Database backups are
[encrypted at rest](https://render.com/docs/databases#encryption). A restore
creates another database instance; budget its applicable compute/storage.
Neither USD 54 nor USD 79 proves the full P01 backup/restore requirement.

**VERIFIED — partial controls only:** the [pipeline spend limit](https://render.com/docs/build-pipeline)
stops pipeline work, not the complete invoice. [Outbound bandwidth](https://render.com/docs/outbound-bandwidth)
overages are billable when a payment method exists. Compute, storage, workspace
fees, usage, taxes and external inference are separate surfaces. No all-in
automatic USD 100 stop has been verified; flags, alerts, a 70-dollar target or
stopping compute at 80 dollars cannot establish that guarantee.

**Execution decision:** do not apply the paid hosted Blueprint, upgrade plans,
add dedicated IPs, enable autoscaling, schedule charged work or enable paid
inference under this decision. It does not change existing Free resources,
billing settings, secrets, data-retention rules or resource-deletion authority.
The existing Blueprint's read-only checkpoint returned no managed resources and
`autoSync=false`; that is not proof of account-wide zero charges.

Further work can validate source and public evidence. Paid activation requires
verified coverage of every billable category and bounded stop/overrun behavior,
plus the remaining identity, actual callback, DB/TLS/network and recovery evidence.
This record does not create another offline checker or relabel a release gate.
