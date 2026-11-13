# P01 startup configuration triage

## Purpose and boundary

`scripts/p01_startup_triage.py` is an offline, read-only checker for a manually prepared JSON inventory. It accepts only allowlisted configuration **names** and the states `present`, `missing`, or `not_checked`. It does not read process environment variables, inspect provider accounts, parse configuration values, call a network, or change any service.

The tool reports evidence about names only. A name marked present does not establish that its value is valid, that the service can start, that PostgreSQL is reachable, or that P01 is ready. It never authorizes a deployment. P01 remains **NO-GO / BLOCKED** and AI-9 remains **BLOCKED**.

## Configuration contract in the bootstrap

The current `scripts/devobs_intelligence/staging_app.py` requires these names at startup:

| Name | Why the bootstrap requires it |
| --- | --- |
| `DEVOBS_OIDC_ISSUER` | Expected OIDC issuer supplied to the token verifier. |
| `DEVOBS_OIDC_AUDIENCE` | Expected token audience. |
| `DEVOBS_OIDC_CLIENT_ID` | Expected client identifier supplied to the token verifier. |
| `DEVOBS_OIDC_METADATA_JSON` | Operator-supplied OIDC metadata JSON; startup does not fetch it. |
| `DEVOBS_OIDC_JWKS_JSON` | Operator-supplied public JWKS JSON; startup does not discover or rotate keys. |
| `DEVOBS_PG_DSN` | PostgreSQL connection for the restricted, non-admin runtime identity. |

The default TLS selector is `verify-full` when `DEVOBS_PG_TLS_MODE` is absent. In that mode the DSN must use `sslmode=verify-full` and supply a valid `sslrootcert`. The alternate `render-internal-require` mode is explicitly conditional: the process must identify as `RENDER=true` and `RENDER_SERVICE_TYPE=web`; the DSN must have `sslmode` unset or `require`. That mode encrypts the connection but does not verify the peer certificate identity. Presence-only evidence cannot validate the DSN, the selector value, certificate contents, Render values, or whether the alternate mode is applicable.

The mode and Render names are allowed as optional inventory fields only to track whether an operator checked the relevant names. Their values must never be copied into the inventory. An omitted optional field or `not_checked` means the checker has insufficient evidence.

## Inventory format

Create a local JSON file containing only this schema. Do not copy values from Render or from an environment file. The states below are examples of presence labels, not settings values.

```json
{
  "schema_version": 1,
  "variables": {
    "DEVOBS_OIDC_ISSUER": "present",
    "DEVOBS_OIDC_AUDIENCE": "present",
    "DEVOBS_OIDC_CLIENT_ID": "not_checked",
    "DEVOBS_OIDC_METADATA_JSON": "present",
    "DEVOBS_OIDC_JWKS_JSON": "present",
    "DEVOBS_PG_DSN": "not_checked",
    "DEVOBS_PG_TLS_MODE": "not_checked",
    "RENDER": "not_checked",
    "RENDER_SERVICE_TYPE": "not_checked"
  }
}
```

Only the top-level keys `schema_version` and `variables` are accepted. The `variables` object accepts only the nine allowlisted names in the example. Every state must be exactly `present`, `missing`, or `not_checked`. Unknown fields, duplicate JSON keys, actual values, environment dumps, invalid states, malformed JSON, unreadable input, and files larger than 8 KiB are rejected with a fixed error code. Error output never includes the path or input content.

Do not include a real DSN, password, access token, client secret, private key, full environment export, or screenshot. If an actual value is pasted into the file accidentally, do not run or commit it; remove the file securely and rotate the exposed credential according to the owner's incident process.

## Run locally

From the repository root, using Python's standard library:

```sh
python3 scripts/p01_startup_triage.py --inventory /path/to/p01-presence-inventory.json
```

Exit codes:

- `0`: all six required names are explicitly present and TLS name inventory is sufficient for triage. If `DEVOBS_PG_TLS_MODE` is marked present, both conditional Render-context names must also be marked present; if the mode name is marked missing, the source-defined `verify-full` default applies. Values remain unverified; this is **not** readiness.
- `2`: one or more required names were explicitly marked missing. The JSON report lists only the missing names.
- `3`: one or more required names, the TLS selector, or required conditional TLS-context names were not sufficiently inventoried.
- `4`: the inventory could not be read or failed the strict schema. The diagnostic is fixed and does not echo input.

For each required name, `missing` produces `CONFIRMED_MISSING_CONFIGURATION`; `present` produces `PRESENT_BUT_VALIDITY_UNVERIFIED`; and `not_checked` or an omitted entry produces `INSUFFICIENT_EVIDENCE`. The top-level status follows the same fail-closed priority. TLS receives its own status and remains unverified even when its selector name has been inventoried.

## Operator checklist for the existing Render service

This is a manual name-only comparison in the owner's existing service dashboard. The checker does not log in to Render and no configuration is changed.

1. Open the existing Render web service and its Environment variable-name list.
2. Compare the six required names from the table above. Record only `present`, `missing`, or `not_checked` in the local inventory.
3. If relevant, check whether the names `DEVOBS_PG_TLS_MODE`, `RENDER`, and `RENDER_SERVICE_TYPE` exist. Do not copy their values.
4. For TLS, the owner must privately verify the selected mode and the DSN's TLS fields against the bootstrap contract above. Do not give those values to this tool or include them in a ticket, commit, chat, or screenshot.
5. Run the local checker, review only its sanitized report, then delete the inventory. Do not commit it.
6. If a required name is missing, the owner may decide separately how to configure it. Do not change settings, redeploy, or create resources as part of this triage.

## What the result cannot prove

- OIDC issuer, audience, client ID, metadata or JWKS validity, key ownership, rotation, or token acceptance.
- DSN correctness, role privileges, RLS, database connectivity, schema state, backups, restore, or runtime readiness.
- TLS selector value, DSN TLS parameters, certificate validity/identity, or Render platform values.
- That the expected service is the one displayed in the provider dashboard.
- Hosted Render behavior, production safety, budget enforcement, or owner authorization.

For actual startup and PostgreSQL request-path contract tests, see [staging acceptance](STAGING_ACCEPTANCE.md). Those use the disposable CI database and synthetic identities; they do not verify Render. The latest verified P01 and AI-9 states remain blocked.
