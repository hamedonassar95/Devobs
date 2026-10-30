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

## Next safe action

1. In Supabase, open **Devobs AI Intelligence** → its **existing** project; read the project **name, region, status and Free plan** without opening API keys, database passwords or personal customer data.
2. Update/reconnect ChatGPT Supabase to the account that sees the new organization; retry `list_organizations`, `list_projects` and `get_project` **read-only**. A screenshot of the project overview is a fallback when the connector stays stale.
3. **Only after identity/region reconciliation**, assess whether to reuse the existing Devobs project for synthetic P01 staging; do not create another project, migrate data, enable a public endpoint, connect Render or activate paid resources.

**P01 remains NO-GO.** No Supabase organization, project, migration, key, billing plan, or provider setting was created or changed by this investigation.
