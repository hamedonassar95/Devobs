# Deployment automation status and setup

This document describes the proposed automation changes on branch
codex/deployment-automation-completion-20261015. They become active only after
review and merge. No AWS deployment or production rollback was run while preparing
this change.

## What the workflow provides

- GitHub Pages continues to deploy only after successful CI on a trusted push to
  main.
- The health-check workflow records the tested commit, source workflow result,
  verification result, run URL, and approximate Actions run duration.
- Each health-check run creates a JSON artifact retained for 90 days and a
  GitHub Actions summary.
- Slack and SMTP email alerts are optional. Missing settings are reported as
  not-configured; notification outages do not hide a failed site health check.
- A failed automated production health check can dispatch the existing validated
  Pages rollback workflow, but only when automatic rollback is explicitly enabled.
  Manual health checks and failed deploy jobs do not trigger automatic rollback.
- The ECS workflow is manual, requires explicit confirmation, is restricted to
  main, checks its configuration and files before requesting AWS credentials,
  and uses GitHub OIDC instead of long-lived AWS access keys.

The duration is an operational measure for one Actions run. It does not prove
time saved or reduced error rates. Establish a baseline and collect enough
successful and failed runs before making a before/after business claim.

## Slack and email setup

Add only the relevant values under GitHub repository Settings → Secrets and
variables → Actions. Do not commit webhook URLs, SMTP credentials, or recipient
addresses.

### Slack

- Secret: SLACK_WEBHOOK_URL
- Use a Slack Incoming Webhook for the intended operations channel. The reporter
  accepts HTTPS URLs on hooks.slack.com only.

### SMTP email

Set all of these secrets to enable email; the workflow requires authenticated
SMTP with STARTTLS:

- DEPLOY_SMTP_HOST
- DEPLOY_SMTP_PORT (optional; defaults to 587)
- DEPLOY_SMTP_USERNAME
- DEPLOY_SMTP_PASSWORD
- DEPLOY_EMAIL_FROM
- DEPLOY_EMAIL_TO (one or more comma-separated recipients)

If either channel is not configured, the deployment report still runs and says
that the channel is not configured. Alert delivery errors are visible as
workflow warnings and do not change the result of the site health check.

## Optional automatic Pages rollback

Automatic rollback is off unless explicitly enabled. After confirming that
the published stable release and GitHub Pages environment are correct, configure
these repository variables:

- PAGES_AUTO_ROLLBACK_ENABLED=true
- PAGES_ROLLBACK_RELEASE_TAG=vX.Y.Z for a published, non-draft, non-prerelease release

The guard accepts only a failed health check caused by the trusted
Deploy Pages → Deployment Health Check workflow chain on main. It then
dispatches Rollback Pages, which revalidates the release, reruns project
checks, deploys the exact release commit, and checks the public site. It does not
rewrite main history. This rollback covers the static GitHub Pages site only;
it does not roll back AWS ECS.

Before enabling, require the desired reviewers on the github-pages environment
and protect stable release tags. Automatic rollback is a production action; the
workflow is intentionally not enabled by this change.

## AWS ECS readiness and enablement

The AWS workflow no longer runs on every push. It accepts a manual request on
main only and requires the confirm_deploy input. Before the deploy job can
obtain an OIDC token, preflight requires:

- ECS_DEPLOY_ENABLED=true
- Repository variables: AWS_REGION, AWS_ROLE_ARN, ECR_REPOSITORY,
  ECS_SERVICE, ECS_CLUSTER, ECS_TASK_DEFINITION, ECS_CONTAINER_NAME
- A repository Dockerfile
- A valid ECS task-definition JSON file whose container name matches
  ECS_CONTAINER_NAME
- An AWS IAM OIDC trust policy restricted to
  repo:hamedonassar95/Devobs:ref:refs/heads/main, with only the ECR push and
  ECS task/service permissions required by this workflow
- A protected GitHub environment named production; configure required reviewers
  before enabling production deployment

This repository currently publishes a static Pages site and has no verified
Docker/ECR/ECS deployment configuration. Keep ECS_DEPLOY_ENABLED unset until
the Dockerfile, task definition, AWS resources, OIDC trust, and production
environment have been created and independently reviewed. Do not add static
AWS access keys.

## Reviewing results

For each Pages run, inspect the Deployment Health Check Actions summary and
download its deployment-report-<run>-<attempt> artifact. The JSON contains
only workflow metadata, status, duration, commit, site URL, and channel delivery
status. It must not contain customer data or secrets.

For business impact, record a baseline before claiming improvements:
manual deployment time, failed deployment count, recovery time, and monthly
deployment volume. Compare the same definitions over an agreed period after
automation. Do not infer a percentage improvement from Actions run duration
alone.
