# One-click deployment, rollback, and notifications

The `One-click deploy` workflow provides a manually confirmed production deployment for GitHub Pages. It is separate from the automatic deployment that runs after CI succeeds on `main`; the two paths use different guarded rollback targets.

## Run a deployment

Open **Actions → One-click deploy → Run workflow** and choose:

- `candidate_ref`: `main` for the current main commit, or a full commit SHA already in the repository.
- `rollback_release_tag`: a published stable release such as `v1.0.0` to restore if the production health check fails.
- `confirm_deploy`: select the confirmation box.

The workflow validates both commits and the published stable fallback release, runs Python and Node checks, validates the static page, runs Bandit, deploys the candidate to GitHub Pages, and checks the public page and a `deployment.json` source-SHA manifest against the selected candidate. If the candidate deploy succeeds but its production health check fails, the workflow dispatches the existing `Rollback Pages` workflow as a separate run on the stable release tag, and passes only the original workflow inputs, so older release tags remain dispatchable. The separate run gives GitHub Pages a unique deployment build version. Historical rollback workflows that predate the manifest remain usable and perform their existing HTTP/content check, but cannot prove the restored source SHA. The deployment report marks the rollback as pending and links to the queued run when it can identify one uniquely; otherwise it links to the rollback workflow page. The rollback run records its own final health-check result. The dispatch handoff returns without waiting, so the queued rollback can acquire the shared production concurrency lock after the candidate run finishes. If candidate preparation fails before deploy, rollback is not started.

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

The automatic `main` path now records the currently published manifest and, if candidate health verification fails, can restore that exact prior commit after checking it is still an ancestor of unchanged `main` and passes rollback quality checks. The confirmed one-click path retains its explicitly selected stable-release tag fallback and integrated deployment report. The separate `Rollback Pages` workflow remains available for manual recovery.
