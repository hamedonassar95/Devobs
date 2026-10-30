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

**Next read-only question:** tap the **existing project card** and inspect its Project Settings → General overview (full project name, displayed region, project status). Do not view or transmit database passwords, API keys or personal data. The connector may need its account authorization refreshed before it can independently see this new organization.

## Next safe action

1. In Supabase, open **Devobs AI Intelligence** → its **existing** project; read the project **name, region, status and Free plan** without opening API keys, database passwords or personal customer data.
2. Update/reconnect ChatGPT Supabase to the account that sees the new organization; retry `list_organizations`, `list_projects` and `get_project` **read-only**. A screenshot of the project overview is a fallback when the connector stays stale.
3. **Only after identity/region reconciliation**, assess whether to reuse the existing Devobs project for synthetic P01 staging; do not create another project, migrate data, enable a public endpoint, connect Render or activate paid resources.

**P01 remains NO-GO.** No Supabase organization, project, migration, key, billing plan, or provider setting was created or changed by this investigation.
