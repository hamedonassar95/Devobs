# Vertex AI fallback for incident investigation

The normal `incident-investigator` remains on GitHub Copilot. The separate
`incident-investigator-vertex` workflow is a manually invoked fallback for a
trusted incident when the Copilot investigation run fails (for example, with an
inference HTTP 429) and no investigation comment has been published.

The fallback uses `gh-aw v0.89.21`'s supported Gemini engine with Vertex AI and
GitHub Actions OIDC Workload Identity Federation (WIF). It does not require a
service-account key or a GitHub secret. The two workflows use the same
incident concurrency key, revalidate the issue immediately before writing, and
skip when a prior investigation comment exists. This prevents simultaneous
Copilot and Vertex runs from publishing duplicate reports.

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
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository == 'hamedonassar95/Devobs' && assertion.ref == 'refs/heads/main'"

# Permit only this repository identity to impersonate the service account.
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/hamedonassar95/Devobs"
```

In **Devobs → Settings → Secrets and variables → Actions → Variables**, add
these repository variables (they are identifiers, not credentials):

| Variable | Value |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID` |
| `GCP_VERTEX_SERVICE_ACCOUNT` | `devobs-vertex-investigator@PROJECT_ID.iam.gserviceaccount.com` |
| `GCP_VERTEX_PROJECT_ID` | Google Cloud project ID |

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
