# Microsoft Azure Catalyst readiness

Review date: **2026-11-21**. Baseline:
`f02319237b604d5447598cfb6f2d39e66e14d3f0`.
**VERIFIED:** official documentation and repository inspection.
**UNVERIFIED:** tenant/account permissions, live assessments, billing and migration.

## Identity and workload fit

The [official overview](https://learn.microsoft.com/en-us/azure/migrate/migrate-services-overview)
now calls the Azure Migrate evolution **Azure Catalyst**. Its documented scope
includes server, database, web-application and virtual-desktop discovery,
assessment and migration. VMware, Hyper-V, physical-server and some other-cloud
migration paths exist, but this does not establish automatic Devobs/GCP support
or justify changing its default platform.

**ASSUMED fit:** evaluate migration options only if the owner identifies a real
workload and lawful inventory. The current Terraform baseline manages an
optional image registry, not a verified VM estate. There is no reason to deploy
a discovery appliance, upload inventory or migrate a database for this audit.

## API boundary and official manual onboarding

**VERIFIED:** [Azure Migrate REST documentation](https://learn.microsoft.com/en-us/rest/api/migrate/)
exists for underlying resource operations. This review has **not verified a
public automation API for the Catalyst agent's conversational assessments**.
No `/catalyst/assess` endpoint, SDK, native Pulumi bridge or automation guarantee
is invented. Any future REST use needs a separate operation/API-version review.

The [official agent guide](https://learn.microsoft.com/en-us/azure/migrate/azure-copilot-migration-agent)
requires an Azure subscription, appropriate permissions and Azure Copilot enabled
for the tenant. Region and feature availability must also be checked. These are
**UNVERIFIED prerequisites**, not settings changed by this task.

**Official manual path, documented only; NOT RUN:**

1. An authorized operator verifies the subscription, tenant access, permissions,
   intended assessment scope, data policy and costs before signing in.
2. In Azure portal, open Azure Copilot, then New chat and Catalyst agent; or open
   the Catalyst dashboard, All projects, select the approved project, View summary.
3. Start from an existing approved project. Creating a project, enabling tenant
   features or installing an appliance needs a separate reviewed authorization.
4. Ask assessment/readiness questions only about approved inventory. The guide
   also offers mutation/execution flows; those are outside this assessment design.
5. Review an exported assessment locally, minimize/redact identifying data, and
   record its source/date/scope with the existing Devobs evidence controls.
6. Keep GCP and current deployment/state ownership unchanged. A recommendation,
   landing-zone template or estimated ROI is not migration authorization.

No Azure login, account discovery, resource creation, SDK or appliance execution
occurred here. No credentials or service-account keys are handled.

## Permissions, authentication and data

**ASSUMED security requirements:** use operator-managed Entra access and only
the operation-specific roles verified in Microsoft's current documentation.
Read access does not imply project-creation or migration rights. Subscription,
resource-group, tenant policy and source-machine discovery permissions are
separate. Do not ask for Owner or reuse a GCP identity by default.

The proposed adapter initially accepts only synthetic/manual-export fixtures.
Missing authentication evidence must remain denied, never replaced by a fake
credential or a caller-supplied `authenticated=true`. Do not put source hostnames,
IPs, inventory, database contents or private assessment exports in this public
repository. Use the [neutral interface](../architecture/MULTICLOUD_INTEGRATION_ARCHITECTURE.md)
and canonical redaction controls; no Azure SDK is required for its offline tests.

## Free versus paid dependencies

**VERIFIED published pricing, not a quote or an enforced budget:**
[Azure Catalyst pricing](https://azure.microsoft.com/en-us/pricing/details/azure-catalyst/)
states core tools are available at no additional charge. It also identifies:

| Item | Published limitation |
| --- | --- |
| Server replication licence | First 180 days free per machine; subsequently $25/month per replicated instance |
| Replication storage, transactions and transfer | Charges can arise during the first 180 days |
| Agent-based dependency analysis | Standard Log Analytics charges can apply |
| Partner tools and target resources | Separate licences/compute/storage/network charges can apply |

Tenant Copilot availability is not a verified free entitlement. Do not enable an
agent or provision resources to test pricing. Account eligibility, remaining
credits, regional totals, taxes and all-in stopping controls remain **UNVERIFIED**.
Azure is a hosted service governed by applicable
[Microsoft Product Terms](https://www.microsoft.com/licensing/terms/), not an
open-source licence grant. Future SDK and source-data rights require separate review.

**Verdict:** suitable for a bounded manual evaluation proposal; automated agent
integration and live Devobs migration compatibility are **UNVERIFIED**. No
migration, platform replacement or production action is authorized by this audit.
