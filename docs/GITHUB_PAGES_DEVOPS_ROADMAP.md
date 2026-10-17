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
| Policy as code / governance drift | `scripts/check_repo_policy.py`, `.github/workflows/repository-policy-audit.yml` | Added as a read-only weekly/manual check of the default-branch ruleset, required `validate` check, no-bypass policy, and CodeQL thresholds. The latest hosted run exposed a GitHub API `null` representation for an empty bypass list; a focused fix is in review, and a passing hosted rerun remains required. Repository settings remain a reviewed human action. |
| Deployment verification | `deployment-health-check.yml` checks HTTP/content and the published source SHA for automatic deployments | Implemented and verified on 2026-10-15; see run evidence in `docs/DEPLOYMENT.md`. It does not provide metrics, uptime history, or user-experience monitoring. |
| Incident response and recovery | Incident Response, investigation, guarded recovery and rollback workflows | Implemented with human approval boundaries. Validate using documented dry-run drills and inspect actual workflow results. |
| Containers | No application Docker build is needed for this static site | Not currently applicable. Add Docker only if packaging a service or a reproducible local tool becomes useful. |
| Kubernetes | No cluster or long-running workload exists | Not currently applicable. Do not provision a cluster for a static site. |
| Infrastructure as Code / configuration management | No production cloud infrastructure is required for Pages | Not currently applicable. Reassess Terraform or Ansible if external cloud resources are introduced. |
| GitOps | Site source and deployment workflow are versioned in Git | Partly present. Changes are reviewed through Git and deployed from main; there is no separate cluster desired-state controller. |
| Platform engineering | Single repository and maintainer workflow | Not currently needed. Reassess if multiple teams need self-service environments or shared deployment templates. |
| FinOps / GitHub Code Quality | Incident agent workflows have Agentic Workflows limits (default 1,000 AI credits per run and 5,000 per day); these are not dollar budgets. Code Quality enrollment and account budgets cannot be verified from repository files. Vertex fallback has separate Google Cloud billing. | Review Actions, GitHub AI credits, Code Quality licenses, and Vertex usage in their billing consoles. Set separate provider budgets before live AI use. Do not enable Code Quality broadly without a selected-repository pilot and a hard budget. See `docs/GITHUB_CODE_QUALITY_COSTS.md`. |
| Prometheus, Grafana and centralized logs | No server-side workload to instrument | Not currently applicable. GitHub Actions logs and Pages health checks cover current operational needs; retain no production telemetry beyond what is useful. |
| AIOps | AI-assisted incident investigation and guarded recovery workflows exist. iOS claim triage produces an offline rules report and a privacy-minimized manual AI handoff. | Partly present and not yet operationally accepted: the latest documented Copilot and Vertex preflights fail credential-format checks, and live model quality remains advisory. Fix account settings, pass preflight, then score a controlled report before enabling further automation. The iOS handoff does not call a model automatically. See `docs/INVESTIGATOR_ACCEPTANCE.md`, `docs/AI_MODEL_STRATEGY.md`, and `docs/IOS_EXPLOIT_CLAIM_TRIAGE.md`. |

## Practical completion sequence

1. Keep the Pages deployment path as the production target for the static site.
2. Review required checks, environment restrictions, and Pages source in GitHub Settings after workflow changes.
3. Confirm CI, deployment, and health-check runs succeed on the current main commit; the 2026-10-15 evidence is recorded in `docs/DEPLOYMENT.md`.
4. Review security scan findings and Dependabot pull requests regularly.
5. Review the weekly **Repository policy audit** run; use its findings to inspect the default-branch rules in GitHub Settings. It does not change them.
6. The safe incident-response dry run and a main-branch drill completed on 2026-10-15; see `docs/INCIDENT_RESPONSE.md`. The main-branch drill produced the expected controlled incident without a deployment. PR #114 fixed a shell error after investigator dispatch. The investigator posted a report, but its run failed the output-marker check; a narrow deterministic normalization now handles that marker when the required report heading exists. Live revalidation awaits another AI-consuming drill.
7. Revisit containers, cloud infrastructure, metrics, and cost controls only when the project adds a backend, a metered service, or a team need.

## Latest verification — 16 October 2026

PR #137 added the privacy-minimized iOS AI handoff. Its CI, CodeQL, and Vercel
checks passed before merge. On the merged `main` commit, CI run
[38830419953](https://github.com/hamedonassar95/Devobs/actions/runs/38830419953),
CodeQL run
[38830419457](https://github.com/hamedonassar95/Devobs/actions/runs/38830419457),
and deployment health check
[38830491437](https://github.com/hamedonassar95/Devobs/actions/runs/38830491437)
completed successfully. These runs do not verify Google Cloud or Anthropic
account configuration or test AI answer quality.

## Operational evidence

Repository files describe intended automation, but do not prove account-level settings, cloud resources, external credentials, or successful operation. Use GitHub Actions run history and repository Settings as the source of truth for those checks. Never commit credentials or paste them into issues or workflow logs.
