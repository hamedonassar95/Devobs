# Devobs diagnostics API integration

**Status: code prepared; not deployed or live-tested.** The incident modal now proxies a user-authorized request to the protected Devobs diagnostics API. It does not use the separate Gemini incident prompt. The API on Devobs remains the model and budget boundary; its separately approved provider performs the diagnosis. The console does not construct an incident Gemini prompt or fabricate a diagnosis when configuration is absent.

Public prototype Gemini/media routes and GitHub text-generation routes are
closed with a fixed no-store 503 before body parsing. The server constructs no
Gemini client and a key cannot activate them. This also prevents legacy local
fallbacks from claiming that servers were healed or generating invented results.
The protected diagnosis route remains separate and retains its own configuration,
bearer, redaction, service-binding and upstream authorization checks.

## Runtime configuration

Set these values in the hosting provider's secret/environment settings after confirming the target API is live and has passed the P01 staging checks. Do not put access tokens or provider keys in this repository.

- `DEVOBS_DIAGNOSTICS_ENABLED=true` explicitly enables the proxy route.
- `DEVOBS_API_BASE_URL` is the **HTTPS origin** of the Devobs diagnostics API, such as `https://<verified-api-host>`; do not include a path, query, credentials, or fragment. The user-provided Cloud Run URL has not been verified against the diagnostics API contract and is not hard-coded here.
- `DEVOBS_SERVICE_BINDINGS_JSON` maps dashboard server IDs to already registered Devobs service identities. Example shape (replace every placeholder with verified registry values):

  ```json
  {
    "srv-01": {
      "tenantId": "<tenant-id>",
      "projectId": "<project-id>",
      "serviceId": "<registered-service-id>"
    }
  }
  ```

  Only mapped dashboard servers can call the endpoint. The sample dashboard IDs are mock data; a mapping does not create tenant, project, or service records.

The API contract is `POST /v1/tenants/{tenant}/projects/{project}/services/{service}/diagnostics`. The configured Devobs service must independently trust the OIDC issuer/JWKS and authorize the supplied user for that service.

## Request and credential handling

- A user must provide a short-lived OIDC **access token** with `devobs.ai.diagnose` scope. The browser sends it in the HTTPS `Authorization` header. It stays in component memory only, is cleared immediately when the request starts and when the incident changes/closes, and is not written to local or session storage. The proxy does not log it or keep it in server environment variables. Closing/changing the incident aborts the browser request and suppresses stale results; it cannot guarantee cancellation of an upstream model request already accepted.
- The UI requires a user confirmation that the incident text has been reviewed for secrets and personal data. The editable log initially contains only error code, severity, message, and stack trace. The server sends only the reviewed text, `data_redacted=true`, and the user-provided Authorization header to the mapped API route. It omits dashboard server IP, CPU/memory/disk metrics, region, and unrelated records. The Devobs API also validates the redaction affirmation and rejects common credential patterns; inspect the trace before sending because automated checks cannot find every sensitive value.
- The server accepts an 8 KiB maximum error log, limits JSON bodies to 32 KiB, allows at most five outbound diagnosis calls per process per minute and two in flight, uses HTTPS only, rejects redirects, bounds streamed response bodies to 32 KiB, validates the six-field diagnosis response, and times out after 22 seconds. Devobs applies its own authorization, validation, and rate limits. These limits reduce bursts but do not impose a monthly dollar cap.
- The Devobs diagnostics contract does not persist the submitted log. The UI can still hold mock/dashboard records in browser local storage as before; this integration does not upload those unrelated records.

Opening the modal makes no network call. The user edits the log, enters a short-lived token, affirms review, and presses **طلب تحليل استشاري**. Missing configuration returns a fixed 503; provider failures never return a guessed cause or raw exception. Syntax checking of the bearer header is not authentication: the Devobs API must validate its signature, scopes and tenant/service access. Editing the log clears the redaction affirmation. This modal cannot deploy a hotfix or assert that a root cause was mitigated; marking an incident resolved updates its prototype record (including optional Firestore sync), not a server. Other Gemini prototype routes remain closed and cannot be enabled through this integration.

## Still required before a real customer pilot

1. Deploy/review the Devobs API and prove `/readyz`, OIDC authorization, tenant/service access denial, and OpenAI behavior in the approved staging environment.
2. Configure and verify a supported user OIDC flow for the required short-lived access token. The optional [Devobs PKCE sign-in](DEVOBS_OIDC_LOGIN.md) prepares a separate **read-only** session; it does not request or grant `devobs.ai.diagnose` and does not auto-fill this modal. A diagnostic grant requires its own review. No identity provider or long-lived shared bearer is invented.
3. Create and verify the tenant/project/service bindings in Devobs. The UI's mock server IDs are not production service identities.
4. Configure the three runtime variables above in the host and verify the host enforces HTTPS and protects its environment settings.
5. Run the synthetic diagnosis cases against the deployed integration after the API owner has approved the model and spend controls. No inference, deployment, database mutation, or customer data use was performed for this change.

The existing cross-repository `repository_dispatch` remains metadata-only CI reporting. It does not carry incidents, write to the Devobs database, or invoke a model.
