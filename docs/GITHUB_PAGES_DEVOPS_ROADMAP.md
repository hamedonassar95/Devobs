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
| AI code review | `.github/workflows/ai-code-review.yml` uses OpenAI Codex on eligible internal PRs and updates one advisory comment with current status | Configured in the repository. The latest inspected run [39710864771](https://github.com/hamedonassar95/Devobs/actions/runs/39710864771) completed as a workflow, but the Codex review step was skipped; live model access is still unverified. Requires the paid `OPENAI_API_KEY` secret. Keep the review advisory and human-reviewed. See `docs/AI_CODE_REVIEW.md`. |
| Policy as code / governance drift | `scripts/check_repo_policy.py`, `.github/workflows/repository-policy-audit.yml` | Read-only weekly/manual audit of the default-branch ruleset, required `validate` check, no-bypass policy, and CodeQL thresholds. The latest audit [39280011409](https://github.com/hamedonassar95/Devobs/actions/runs/39280011409) failed at GitHub API authentication with HTTP 401. The prior audit [39053647920](https://github.com/hamedonassar95/Devobs/actions/runs/39053647920) passed. The owner must verify the read-only `POLICY_AUDIT_TOKEN`; current live branch rules remain unverified. See [the setup guide](REPOSITORY_POLICY_AUDIT.md). |
| Deployment verification | `deployment-health-check.yml` checks HTTP/content and the published source SHA for automatic deployments | Verified on 2026-10-22: CI run [39711232712](https://github.com/hamedonassar95/Devobs/actions/runs/39711232712) published Pages and its production SHA/health verification passed on the same commit. It does not provide metrics, uptime history, or user-experience monitoring. |
| Incident response and recovery | Incident Response, investigation, guarded recovery and rollback workflows | Implemented with human approval boundaries. Validate using documented dry-run drills and inspect actual workflow results. |
| Containers | No application Docker build is needed for this static site | Not currently applicable. Add Docker only if packaging a service or a reproducible local tool becomes useful. |
| Kubernetes | No cluster or long-running workload exists | Not currently applicable. Do not provision a cluster for a static site. |
| Infrastructure as Code / configuration management | No production cloud infrastructure is required for Pages | Not currently applicable. Reassess Terraform or Ansible if external cloud resources are introduced. |
| GitOps | Site source and deployment workflow are versioned in Git | Partly present. Changes are reviewed through Git and deployed from main; there is no separate cluster desired-state controller. |
| Platform engineering | Single repository and maintainer workflow | Not currently needed. Reassess if multiple teams need self-service environments or shared deployment templates. |
| FinOps / GitHub Code Quality | Incident agent workflows have Agentic Workflows limits (default 1,000 AI credits per run and 5,000 per day); these are not dollar budgets. Code Quality enrollment and account budgets cannot be verified from repository files. Vertex fallback has separate Google Cloud billing. | Review Actions, GitHub AI credits, Code Quality licenses, and Vertex usage in their billing consoles. Set separate provider budgets before live AI use. Do not enable Code Quality broadly without a selected-repository pilot and a hard budget. See `docs/GITHUB_CODE_QUALITY_COSTS.md`. |
| Prometheus, Grafana and centralized logs | No server-side workload to instrument | Not currently applicable. GitHub Actions logs and Pages health checks cover current operational needs; retain no production telemetry beyond what is useful. |
| AIOps | AI-assisted incident investigation and guarded recovery workflows exist. iOS claim triage produces an offline rules report and a privacy-minimized manual AI handoff. | **VERIFIED (runtime/run metadata):** provider preflight [39323105297](https://github.com/hamedonassar95/Devobs/actions/runs/39323105297) completed a Copilot token-presence and prefix check; it did not verify account permission or inference. Circuit-breaker run [39322008908](https://github.com/hamedonassar95/Devobs/actions/runs/39322008908) verified incident eligibility and dispatched one Vertex fallback; it did not validate provider credentials. **VERIFIED (runtime/run metadata):** the resulting Vertex workflow [39322055802](https://github.com/hamedonassar95/Devobs/actions/runs/39322055802) passed its activation and Google authentication preflight, then failed at `Execute Gemini CLI`. **UNVERIFIED:** no valid model response is evidenced by these runs, and the isolated Copilot inference smoke has not run. Keep `COPILOT_GITHUB_TOKEN` and `POLICY_AUDIT_TOKEN` separate; use a quota-reviewed, tool-free smoke before claiming a model response. The iOS handoff does not call a model automatically. See `docs/INVESTIGATOR_ACCEPTANCE.md`, `docs/AI_MODEL_STRATEGY.md`, and `docs/IOS_EXPLOIT_CLAIM_TRIAGE.md`. |

## Practical completion sequence

1. Keep the Pages deployment path as the production target for the static site.
2. Review required checks, environment restrictions, and Pages source in GitHub Settings after workflow changes.
3. Confirm CI, Pages publication, and health-check runs succeed on the current main commit; the latest inspected evidence is recorded below and in `docs/DEPLOYMENT.md`.
4. Review security scan findings and Dependabot pull requests regularly.
5. Add `OPENAI_API_KEY` only after setting an OpenAI API budget, then confirm a successful AI review run; review source-sharing terms and keep its result advisory.
6. Review the weekly **Repository policy audit** run; use its findings to inspect the default-branch rules in GitHub Settings. It does not change them.
7. The safe incident-response dry run and a main-branch drill completed on 2026-10-15; see `docs/INCIDENT_RESPONSE.md`. The main-branch drill produced the expected controlled incident without a deployment. PR #114 fixed a shell error after investigator dispatch. The investigator posted a report, but its run failed the output-marker check; a narrow deterministic normalization now handles that marker when the required report heading exists. Live revalidation awaits another AI-consuming drill.
8. Revisit containers, cloud infrastructure, metrics, and cost controls only when the project adds a backend, a metered service, or a team need.

## Earlier verification — 16 October 2026

PR #137 added the privacy-minimized iOS AI handoff. Its CI, CodeQL, and Vercel
checks passed before merge. On the merged `main` commit, CI run
[38830419953](https://github.com/hamedonassar95/Devobs/actions/runs/38830419953),
CodeQL run
[38830419457](https://github.com/hamedonassar95/Devobs/actions/runs/38830419457),
and deployment health check
[38830491437](https://github.com/hamedonassar95/Devobs/actions/runs/38830491437)
completed successfully. These runs do not verify Google Cloud or Anthropic
account configuration or test AI answer quality.

## Latest current-main verification — 22 October 2026

The latest main SHA checked was `40647754fc247195a2c523e9011ddb146201a915`.
CI [39711232712](https://github.com/hamedonassar95/Devobs/actions/runs/39711232712)
and [Push on main 39711231865](https://github.com/hamedonassar95/Devobs/actions/runs/39711231865)
completed successfully on that SHA. The security, site-contract, validation,
Pages publication, and production health/SHA checks passed. Node and Python
test jobs were skipped because this commit changed documentation only.

**VERIFIED (runtime/run metadata):** the latest repository policy audit run
[39280011409](https://github.com/hamedonassar95/Devobs/actions/runs/39280011409)
failed with GitHub API HTTP 401 while reading repository metadata. The previous
successful audit, [39053647920](https://github.com/hamedonassar95/Devobs/actions/runs/39053647920),
completed on 17 October 2026. **UNVERIFIED:** the reason GitHub rejected the
latest request and the current branch protection/ruleset settings; correct or
replace the read-only audit credential, then rerun the audit. The direct
Settings review on 6 October remains the latest manual settings review.
Provider preflights do not establish live AI inference.

## Operational evidence

Repository files describe intended automation, but do not prove account-level settings, cloud resources, external credentials, or successful operation. Use GitHub Actions run history and repository Settings as the source of truth for those checks. Never commit credentials or paste them into issues or workflow logs.
