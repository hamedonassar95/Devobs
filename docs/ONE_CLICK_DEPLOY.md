# One-click deployment, rollback, and notifications

The `One-click deploy` workflow provides a manually confirmed production deployment for GitHub Pages. It is separate from the existing automatic deployment that runs after CI succeeds on `main`.

## Run a deployment

Open **Actions → One-click deploy → Run workflow** and choose:

- `candidate_ref`: `main` for the current main commit, or a full commit SHA already in the repository.
- `rollback_release_tag`: a published stable release such as `v1.0.0` to restore if the production health check fails.
- `confirm_deploy`: select the confirmation box.

The workflow validates both commits and the published stable fallback release, runs Python and Node checks, validates the static page, runs Bandit, deploys the candidate to GitHub Pages, and checks the public page. If the candidate deploy succeeds but its production health check fails, the workflow dispatches the existing `Rollback Pages` workflow as a separate run on the stable release tag, with an explicit check that the tag still resolves to the previously validated commit. The separate run gives GitHub Pages a unique deployment build version. The deployment report marks the rollback as pending and links to its queued run; the rollback run records its own final health-check result. The dispatch handoff returns without waiting, so the queued rollback can acquire the shared production concurrency lock after the candidate run finishes. If candidate preparation fails before deploy, rollback is not started.

The workflow does not rewrite Git history. Its fallback is a published stable GitHub Release, matching the existing controlled rollback policy. Candidate validation, deployment preparation, deployment, health-check, and rollback outcomes are reported separately. Rollback dispatch uses the run-scoped `GITHUB_TOKEN` with `actions: write`; no personal token is required. A run that is not confirmed records a GitHub summary but sends no Slack or email notification.

## Optional Slack and email reports

GitHub Actions always records the deployment report in its run summary. To also send notifications, configure:

| GitHub setting | Name | Value |
| --- | --- | --- |
| Secret | `SLACK_WEBHOOK_URL` | Slack incoming webhook URL from an approved workspace |
| Variable | `SMTP_HOST` | SMTP host name |
| Variable | `SMTP_PORT` | SMTP port, usually `587` for STARTTLS or `465` for implicit TLS |
| Secret | `SMTP_USERNAME` | SMTP account name |
| Secret | `SMTP_PASSWORD` | SMTP password or app password |
| Variable | `DEPLOYMENT_EMAIL_TO` | Report recipient email address(es) |
| Variable | `DEPLOYMENT_EMAIL_FROM` | Sender address; defaults to `SMTP_USERNAME` |

Slack and email are optional independently. Unconfigured channels are skipped. Notification errors are shown in the run summary and do not cause a successful deployment to be rolled back. Credentials belong only in GitHub Secrets; do not commit them or paste them into chat.

## Current deployment behavior

The repository also has an automatic Pages deployment after successful `CI` on `main`, plus a separate manually confirmed `Rollback Pages` workflow. This new workflow is intended for a deliberate one-click release with a selected rollback target and an integrated report. The automatic deployment path remains unchanged.
