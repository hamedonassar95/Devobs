# GitHub Pages DevOps roadmap

This roadmap describes the current static-site project in this repository. A checked item means there is repository evidence for it; confirm live GitHub settings and successful runs separately before treating it as operationally verified.

## Current scope

The published site is static HTML on GitHub Pages. It does not currently need a long-running server, container orchestration, or a cloud account. Keep production deployment on Pages unless the application gains a backend or another concrete requirement.

## Capability status

| Area | Current evidence | Status and next step |
| --- | --- | --- |
| CI/CD | `.github/workflows/ci.yml`, `deploy-pages.yml` | Implemented for validation and Pages deployment. Check the latest run before releases. |
| Automated tests | `tests/`, CI runs Python and Node tests plus site checks | Implemented. Add regression tests whenever site behavior or workflows change. |
| DevSecOps | Bandit, Gitleaks, immutable GitHub Actions SHA check, `SECURITY.md`; Dependabot updates GitHub Actions | Implemented in part. Review scan results and Dependabot PRs; consider dependency review when application dependencies are introduced. |
| Deployment verification | `deployment-health-check.yml` checks HTTP/content and the published source SHA for automatic deployments | Implemented and verified on 2026-10-15; see run evidence in `docs/DEPLOYMENT.md`. It does not provide metrics, uptime history, or user-experience monitoring. |
| Incident response and recovery | Incident Response, investigation, guarded recovery and rollback workflows | Implemented with human approval boundaries. Validate using documented dry-run drills and inspect actual workflow results. |
| Containers | No application Docker build is needed for this static site | Not currently applicable. Add Docker only if packaging a service or a reproducible local tool becomes useful. |
| Kubernetes | No cluster or long-running workload exists | Not currently applicable. Do not provision a cluster for a static site. |
| Infrastructure as Code / configuration management | No production cloud infrastructure is required for Pages | Not currently applicable. Reassess Terraform or Ansible if external cloud resources are introduced. |
| GitOps | Site source and deployment workflow are versioned in Git | Partly present. Changes are reviewed through Git and deployed from main; there is no separate cluster desired-state controller. |
| Platform engineering | Single repository and maintainer workflow | Not currently needed. Reassess if multiple teams need self-service environments or shared deployment templates. |
| FinOps / LLM FinOps | No metered application runtime is described here | Not currently applicable. Review GitHub Actions usage and model-provider billing in their respective account settings if usage grows. |
| Prometheus, Grafana and centralized logs | No server-side workload to instrument | Not currently applicable. GitHub Actions logs and Pages health checks cover current operational needs; retain no production telemetry beyond what is useful. |
| AIOps | AI-assisted incident investigation and guarded recovery workflows exist | Partly present. Treat AI output as advisory, verify live prerequisites, and keep the documented human approval gates. |

## Practical completion sequence

1. Keep the Pages deployment path as the production target for the static site.
2. Review required checks, environment restrictions, and Pages source in GitHub Settings after workflow changes.
3. Confirm CI, deployment, and health-check runs succeed on the current main commit; the 2026-10-15 evidence is recorded in `docs/DEPLOYMENT.md`.
4. Review security scan findings and Dependabot pull requests regularly.
5. Run the documented incident-response dry run and confirm it produces evidence without changing production.
6. Revisit containers, cloud infrastructure, metrics, and cost controls only when the project adds a backend, a metered service, or a team need.

## Operational evidence

Repository files describe intended automation, but do not prove account-level settings, cloud resources, external credentials, or successful operation. Use GitHub Actions run history and repository Settings as the source of truth for those checks. Never commit credentials or paste them into issues or workflow logs.
