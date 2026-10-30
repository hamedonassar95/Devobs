# P01 Supabase organization — new owner UI evidence vs connected API

**Observed 2026-10-31. Source:** user-provided screenshot of the Supabase "Your organizations" page in this ChatGPT session, **not** a provider API response. No image, private email or account ID was added to the public repository.

## Evidence reconciliation

| Field | Owner screenshot (visually observed) | Connected Supabase API (re-read after screenshot) |
| --- | --- | --- |
| Organization `Devobs AI Intelligence` | **Visible** | **Not returned** by either connected Supabase account alias |
| `Devobs AI Intelligence` plan | **Free Plan** | **UNVERIFIED** via linked API |
| `Devobs AI Intelligence` project count | **1 project** | **No corresponding project returned** |
| Previous phone-repair organization | Separate **Free Plan**, **1 project** | Old organization and `Phone Repair Assistant v2` project returned |
| New Devobs project's name | **Not shown** | **Unknown** |
| New Devobs project's region | **Not shown** | **Unknown** |
| New project/database operational status | **Not shown** | **Unknown** |

**Interpretation:** owner-provided UI evidence supports that a separate Devobs Free organization exists and already contains **one project**. The connected API currently has an **inconsistent or stale view** and cannot identify that project's ID, region, status, security posture or cost. A refreshed/reauthorized Supabase plugin connection, or a read-only screenshot of the new organization's project overview (name, region and status only), can reconcile it. Do not treat the API omission as proof that the organization is absent or that the project must be created.

**Important supersession:** earlier planning documents and proposal validators that use `organization_created=false`, `project_created=false` or `separate_devobs_supabase_project_exists=false` record **the earlier connector-verified state or lack of authorization by the assistant**, not a fresh denial of the later screenshot. Those historical machine-readable values must **not** trigger a new project create. The new project cannot be designated `devobs-p01-staging` until its actual name/region and independent ownership are confirmed. Do not infer from the project count that it has a working PostgreSQL RLS deployment.

## New screenshot: project-list evidence (2026-10-31)

**Owner UI observed, not API-verified:** Within the selected **Devobs AI Intelligence** organization, the **Projects** screen shows **one existing project**, **Free plan**, a visible **Nano** instance label and the specific AWS region **`us-east-1` (Northern Virginia)**. The project title is visually truncated, beginning with the account-holder's name; **the actual full project name, project reference, deployment status and access settings remain UNKNOWN**. The Free usage view shows **26/500 MB** database storage and **0/5 GB** egress at the screenshot time. Usage figures are a point-in-time screenshot, **not an invoice or a guarantee of continued Free eligibility**.

**Critical region mismatch:** the proposal `eu-central-1` (Frankfurt) and the **existing** project `us-east-1` are different regions. Supabase states a project's region is bound at infrastructure provisioning; changing region requires a new project and a migration. A transfer between organizations **does not** change the region. Do **not** migrate, delete, repurpose or duplicate the project based on this screenshot. Review whether `us-east-1` is acceptable for **synthetic-only lab work** and independently decide any later EU residency requirement.

**Official references:**
- https://supabase.com/kb/troubleshooting/change-project-region-eWJo5Z
- https://supabase.com/docs/guides/platform/regions
- https://supabase.com/docs/guides/platform/project-transfer

**Project Settings → General was viewed (owner screenshot, 2026-10-31):** the project reference and region are now visually confirmed; the default project display name is still partially clipped on mobile. Its reference is intentionally excluded from public documentation. **Next step is reconnecting the correct Supabase account to ChatGPT** to resolve the API permission denial, not creating a new project or requesting credentials.

## New screenshot: existing project dashboard (2026-10-31)

**VERIFIED (owner's screenshot, not connected API):** The project dashboard within the selected Devobs organization reports:
- **Status: Healthy** at screenshot time, instance compute size **Nano**. This is only infrastructure health, not application/API/tenant isolation readiness.
- **Project name:** default account-associated name, partly clipped by the mobile viewport; exact full name not independently confirmed.
- **GitHub: No repository connected.** The [official Supabase deployment guide](https://supabase.com/docs/guides/deployment) explicitly states GitHub integration is **optional**; do not authorize repository access or automatic branching based on this display.
- **Recent branch: No branches.** This is not a requirement to create paid or preview branches on the Free plan.
- **Last backup: No backups** in the dashboard. [Supabase official backups guidance](https://supabase.com/docs/guides/platform/backups) gives automatic accessible daily backups to Pro/Team/Enterprise and recommends independent CLI dump/off-site backups for Free. **No recoverable RPO/RTO or backup/restore evidence exists for Devobs.**
- **Region:** previous same-organization project-list screenshot shows `us-east-1`; new dashboard does not show region. Frankfurt remains merely an earlier alternative proposal.

**VERIFIED (connected tool limitation):** Two linked Supabase aliases re-listed only the older Phone Repair Assistant organization/project; direct read of the new Devobs project reference returned **'You do not have permission to perform this action'** on both. This is a **connector authorization mismatch**, not evidence that the owner's screenshot or project is fake, and not permission to create a duplicate or use the repair database.

**NO-GO effects:** Preserve the working Free project as a candidate **synthetic-only lab**, not customer production. Do **not** enable repository integrations, write migrations, open Data API exposure, add keys, connect Render or upgrade service without a new, scoped owner approval. Account linkage, project name, region acceptance, independent backup-and-restore, least-privilege database identity and OIDC/JWKS remain gates.

**One next owner UI action:** from the existing project, open **Project Settings → General** for the full project name and existing region/status; share only nonsensitive fields. Separately, reconnect the ChatGPT Supabase plugin under the same signed-in Supabase account so the API can re-read the new organization before automation. Never share an access token, password or service-role key.

## Owner screenshot: General settings verification (2026-10-31)

**VERIFIED from user-provided screenshot, NOT from linked Supabase API:** The selected Devobs project now has a visually confirmed **project reference/ID** (intentionally not reproduced in this PUBLIC GitHub report), **Project region: `us-east-1` / East US (North Virginia)**, and an account-derived default **Project name** displayed partially on the mobile screen. A screenshot from the preceding project dashboard showed **Healthy / Nano**. The General settings screen also displays **organization-wide access**; the text says all members of this organization can access the project, but does not prove user counts, authentication configuration or least privilege. Project credentials/passwords were never requested or exposed.

**Fresh read-only connector result:** both linked Supabase account aliases still list only the old repair organization; `get_project` on the new user-supplied project ref produced `ProtocolError: You do not have permission to perform this action` for both aliases. Therefore the project exists **according to owner UI evidence**, but is **not yet accessible for safe automation through the current connected app**. Do not change Supabase organization roles or share secrets to work around this; reconnect/reauthorize the proper account through ChatGPT before attempting any future managed operations.

**Practical next gate:** confirm desired display name (e.g. `Devobs AI Intelligence - Staging`) and only rename after a separate owner instruction. For now keep the existing name and `us-east-1` infrastructure, with **synthetic-only data** and no new migrations. Refresh the linked account, then read organization/project details and independently evaluate the DB's actual schema/RLS and recovery plan **before** a live API integration. The separate phone-repair project remains untouched.

## Next safe action

1. In Supabase, open **Devobs AI Intelligence** → its **existing** project; read the project **name, region, status and Free plan** without opening API keys, database passwords or personal customer data.
2. Update/reconnect ChatGPT Supabase to the account that sees the new organization; retry `list_organizations`, `list_projects` and `get_project` **read-only**. A screenshot of the project overview is a fallback when the connector stays stale.
3. **Only after identity/region reconciliation**, assess whether to reuse the existing Devobs project for synthetic P01 staging; do not create another project, migrate data, enable a public endpoint, connect Render or activate paid resources.

**P01 remains NO-GO.** No Supabase organization, project, migration, key, billing plan, or provider setting was created or changed by this investigation.
