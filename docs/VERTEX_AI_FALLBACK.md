# Vertex AI fallback for incident investigation

The normal `incident-investigator` remains on GitHub Copilot. The
`ai-provider-circuit-breaker` workflow dispatches the separate
`incident-investigator-vertex` fallback once when the primary Copilot CLI call
fails for a trusted incident. The Vertex workflow remains manually dispatchable
for operator-controlled recovery when appropriate.

The fallback uses `gh-aw`'s supported Gemini engine with Vertex AI and
GitHub Actions OIDC Workload Identity Federation (WIF). It does not require a
long-lived service-account key; the GitHub settings contain only resource
identifiers and can be stored as repository variables or secrets. The two
workflows use the same incident concurrency key, revalidate the issue
immediately before writing, and skip when a prior investigation comment exists.
The breaker verifies the exact failed Copilot invocation, correlates it to the
trusted issue using a one-day artifact, and writes a durable per-issue marker
before dispatch. This allows at most one automatic Vertex attempt per incident.
If Vertex settings are valid, the fallback may incur Google Cloud charges; if
the identity preflight fails, no Vertex inference is made.

## One-time Google Cloud setup

Use a Google Cloud project with billing enabled. These example commands create
a narrowly scoped service account and a WIF provider restricted to this
repository's `main` branch. Run them from an authenticated `gcloud` session and
replace the project ID and project number with your own values.

```bash
PROJECT_ID="your-project-id"
PROJECT_NUMBER="your-project-number"
POOL_ID="devobs-github"
PROVIDER_ID="devobs-main"
SERVICE_ACCOUNT_ID="devobs-vertex-investigator"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
GITHUB_REPOSITORY="OWNER/REPOSITORY"
GITHUB_REPOSITORY_ID="$(curl -fsSL "https://api.github.com/repos/${GITHUB_REPOSITORY}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

# Enable the APIs used for Vertex AI and OIDC service-account impersonation.
gcloud services enable aiplatform.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  --project="$PROJECT_ID"

# Create a service account for this workflow only.
gcloud iam service-accounts create "$SERVICE_ACCOUNT_ID" --project="$PROJECT_ID"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user"

# Create a GitHub Actions identity pool and provider.
gcloud iam workload-identity-pools create "$POOL_ID" \
  --location=global --project="$PROJECT_ID" \
  --display-name="Devobs GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --location=global \
  --workload-identity-pool="$POOL_ID" \
  --project="$PROJECT_ID" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_id == '${GITHUB_REPOSITORY_ID}' && assertion.ref == 'refs/heads/main'"

# Permit only this repository identity to impersonate the service account.
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository_id/${GITHUB_REPOSITORY_ID}"
```

Google recommends mapping `google.subject` from `assertion.sub`, and warns that
GitHub issuer URLs are shared across repositories. The repository ID mapping and
condition above restrict this provider to one repository and the `main` branch;
the numeric ID cannot be claimed by another repository if the name is later
reused. See Google's [GitHub Actions WIF guidance](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
and [provider update reference](https://docs.cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/providers/update-oidc).

### Secure the provider already created in Google Cloud Console

The screenshots shared for the current setup show project ID
`tensile-verve-352716`, project number `198763193327`, pool `github`, and provider
`devobs-github-actions`. They also appear to show `google.subject` mapped from
`assertion.ref` and no attribute condition. Before using this provider, update
its mapping and restriction in Cloud Shell:

```bash
gcloud iam workload-identity-pools providers update-oidc devobs-github-actions \
  --project=tensile-verve-352716 \
  --location=global \
  --workload-identity-pool=github \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_id == '1404102641' && assertion.ref == 'refs/heads/main'"

# Replace this with the service-account email stored as GCP_VERTEX_SERVICE_ACCOUNT.
SERVICE_ACCOUNT="SERVICE_ACCOUNT_EMAIL"
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
  --project=tensile-verve-352716 \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/198763193327/locations/global/workloadIdentityPools/github/attribute.repository_id/1404102641"
```

`1404102641` is the GitHub repository ID for `hamedonassar95/Devobs`. The
condition rejects tokens from other repositories and branches. If service
account access was granted using a `principal://.../subject/...` binding, review
that binding after changing `google.subject`; prefer a `principalSet` binding
for `attribute.repository_id/1404102641`. The setup command above shows that
binding format. Updating the GitHub setting through the connected integration
also failed with HTTP 403: it lacks repository **Secrets: write** and **Variables:
write** permissions. See GitHub's [secret API permissions](https://docs.github.com/en/rest/actions/secrets)
and [variable API permissions](https://docs.github.com/en/rest/actions/variables).

In **Devobs → Settings → Secrets and variables → Actions**, add these values
as repository variables or repository secrets, using the exact names below.
Repository variables are suitable because these are resource identifiers; secrets
also work if the repository already stores them that way. Do not put them in a
GitHub Environment: this workflow does not bind to an environment.

| Setting name | Example value |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID` |
| `GCP_VERTEX_SERVICE_ACCOUNT` | `devobs-vertex-investigator@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_VERTEX_PROJECT_ID` | Google Cloud project ID |

The preferred `GCP_WORKLOAD_IDENTITY_PROVIDER` value is the provider resource
name in this form:
`projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/<POOL_ID>/providers/<PROVIDER_ID>`.
Use the numeric project number. The preflight and Vertex fallback also accept
the full `https://iam.googleapis.com/<provider-resource>` URL copied from Google
Cloud, or the `//iam.googleapis.com/<provider-resource>` form, and normalize it
to the resource name before authentication. One trailing slash is ignored.
Other URL hosts and malformed resource names are rejected. The preflight checks
the value without printing it. If Google still reports an invalid audience,
check the provider's allowed audiences; the Google auth action requests its
default audience, `https://iam.googleapis.com/<provider-resource>`.
For the provider shown in the screenshots, set the value to
`projects/198763193327/locations/global/workloadIdentityPools/github/providers/devobs-github-actions`.
Do not use the issuer URL `https://token.actions.githubusercontent.com` in this
setting; that URL belongs in the Google provider's **Issuer URL** field.

Before launching Gemini, the workflow now checks that all three values are
nonempty, preferring repository variables and falling back to repository secrets.
It then verifies Workload Identity Federation and service-account impersonation
before Gemini starts, using Google's default OIDC audience derived from the
configured provider. This reports Google's authentication error before model
inference. The access token is masked and is not exported to later steps; no
credentials file is created. A successful preflight does not verify Vertex
model access, quota, or billing, so confirm those separately.

The workflow uses `us-central1` for Vertex AI. Confirm the chosen model and
region are available to your Google Cloud project and that billing/quota are
configured there.

## Invoke the fallback

1. Open the failed **Devobs Incident Investigator** Copilot run and verify the
   issue number in its dispatch input.
2. Confirm the incident issue is still open and has no `AI Incident
   Investigation` comment.
3. Open **Actions → Devobs Incident Investigator — Vertex AI fallback → Run
   workflow**, select `main`, and enter the trusted incident issue number.
4. Review the resulting report and workflow logs. The workflow can add one
   investigation comment; it cannot modify code, merge a PR, or execute rollback.

If the issue already has an investigation comment, the trust gate skips the
fallback. Vertex AI has separate billing and quotas from Copilot; enabling it
provides another inference path but does not guarantee the Google service will
never rate-limit requests.

## Live setup check — 15 October 2026

Fallback run
[38806920363](https://github.com/hamedonassar95/Devobs/actions/runs/38806920363)
for issue [#124](https://github.com/hamedonassar95/Devobs/issues/124) passed the
incident trust gate and activation. Gemini then exited with code 41 before
inference, reporting that Vertex AI requires `GOOGLE_CLOUD_PROJECT` and
`GOOGLE_CLOUD_LOCATION`. The compiled workflow sets the location to `us-central1`
and maps the project from `GCP_VERTEX_PROJECT_ID`, so verify that the repository
value is configured along with the workload identity provider and service account
values above. The run posted no comment; do not rerun the fallback until the
Google Cloud configuration and project quota are verified.

## Repository configuration check — 15 October 2026

Run
[38811637323](https://github.com/hamedonassar95/Devobs/actions/runs/38811637323)
for issue [#124](https://github.com/hamedonassar95/Devobs/issues/124) stopped
before Gemini because the three `vars.*` inputs were empty. The workflow now
accepts each setting as either a repository variable or a repository secret.
It still rejects missing values before any Vertex request.

## WIF retry result — 15 October 2026

The failed-job rerun of
[38819361315](https://github.com/hamedonassar95/Devobs/actions/runs/38819361315)
again reached Gemini but could not obtain the Vertex OIDC token. Gemini retried
10 times and used no model tokens; no investigation comment was posted. The new
preflight below checks Google authentication separately, so its next run can
show whether the failure is in WIF/service-account setup or later in the Vertex
model request.

## Google Cloud authentication preflight

The Vertex fallback uses the pinned `google-github-actions/auth` action in the
trusted pre-activation job. This checks the Workload Identity provider,
service-account binding, and GitHub `id-token: write` access before Gemini
starts. If it fails, use that step's Google error to correct the provider
resource path, repository/ref condition, enabled IAM APIs, or service-account
permissions. The preflight does not call Vertex AI or publish an issue comment.

Run
[38822537862](https://github.com/hamedonassar95/Devobs/actions/runs/38822537862)
confirmed all three configuration values were present but Google STS rejected
the OIDC audience. The workflow now leaves `audience` unset so the Google auth
action derives its default audience from the provider resource. The next run,
[38822860325](https://github.com/hamedonassar95/Devobs/actions/runs/38822860325),
received the same Google rejection. The preflight now validates the provider
resource-name format; if it passes but Google still rejects the audience, verify
the provider's allowed audiences and trust configuration in Google Cloud.

## Controlled evaluation attempt — 16 October 2026

Vertex fallback run
[38843374720](https://github.com/hamedonassar95/Devobs/actions/runs/38843374720)
passed the trust gate for controlled-drill issue
[#140](https://github.com/hamedonassar95/Devobs/issues/140), then stopped in
`Validate Vertex AI configuration`. The configured
`GCP_WORKLOAD_IDENTITY_PROVIDER` did not match the required resource-name form:

```text
projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/<POOL_ID>/providers/<PROVIDER_ID>
```

The value must use the numeric project number. Since this check failed, Google
WIF and Vertex model inference did not run, and the workflow posted no report.

## Provider URL normalization — 17 October 2026

Preflight run
[38987158382](https://github.com/hamedonassar95/Devobs/actions/runs/38987158382)
found that the three Vertex settings were present, but the provider value was not
in the bare resource-name form. After the workflow was updated to normalize the
Google IAM URL from the provider's default-audience field, run
[38987980947](https://github.com/hamedonassar95/Devobs/actions/runs/38987980947)
still failed provider-format validation, so the configured value is not the full
provider resource or an accepted IAM URL. Both runs stopped before Google
authentication and model inference. The latest preflight error now distinguishes
the provider resource from GitHub's issuer URL without printing the configured
value. Updating the GitHub setting via API was denied with HTTP 403 because the
connected integration does not have repository Secrets: write permission. Set
the value in the repository's Actions settings, then rerun the preflight. A
successful format check alone does not prove the WIF trust policy,
service-account binding, Vertex API, quota, or model access is correct.
