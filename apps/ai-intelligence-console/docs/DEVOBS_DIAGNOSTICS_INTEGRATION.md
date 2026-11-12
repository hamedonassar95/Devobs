# Devobs diagnostics API integration

**Status: code prepared; not deployed or live-tested.** The incident modal now proxies a user-authorized request to the protected Devobs diagnostics API. It does not use the separate Gemini incident prompt. The API on Devobs remains the model boundary; its configured OpenAI adapter performs the diagnosis.

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

- A user must provide a short-lived OIDC **access token** with `devobs.ai.diagnose` scope. The browser sends it in the HTTPS `Authorization` header. It stays in component memory only, is cleared when the incident changes/closes, and is not written to local or session storage. The proxy does not log it or keep it in server environment variables.
- The UI requires a user confirmation that the incident text has been reviewed for secrets and personal data. The server sends only error code, severity, message, and stack trace. It omits dashboard server IP, CPU/memory/disk metrics, region, and unrelated records. The Devobs API also validates the redaction affirmation and rejects common credential patterns; inspect the trace before sending because automated checks cannot find every sensitive value.
- The server accepts an 8 KiB maximum error log, limits JSON bodies to 32 KiB, allows at most five outbound diagnosis calls per process per minute and two in flight, uses HTTPS only, rejects redirects, and times out after 22 seconds. Devobs applies its own authorization, validation, and rate limits. These limits reduce bursts but do not impose a monthly dollar cap.
- The Devobs diagnostics contract does not persist the submitted log. The UI can still hold mock/dashboard records in browser local storage as before; this integration does not upload those unrelated records.

## Still required before a real customer pilot

1. Deploy/review the Devobs API and prove `/readyz`, OIDC authorization, tenant/service access denial, and OpenAI behavior in the approved staging environment.
2. Choose/configure a supported user OIDC sign-in flow that can issue the required short-lived access token. This change deliberately does not invent an identity provider or add a long-lived shared bearer token.
3. Create and verify the tenant/project/service bindings in Devobs. The UI's mock server IDs are not production service identities.
4. Configure the three runtime variables above in the host and verify the host enforces HTTPS and protects its environment settings.
5. Run the synthetic diagnosis cases against the deployed integration after the API owner has approved the model and spend controls. No inference, deployment, database mutation, or customer data use was performed for this change.

The existing cross-repository `repository_dispatch` remains metadata-only CI reporting. It does not carry incidents, write to the Devobs database, or invoke a model.
