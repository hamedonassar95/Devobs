# GitLab Free — manual-only CI smoke pilot (prepared, not activated)

**Canonical source:** GitHub `hamedonassar95/Devobs`, protected `main`.
**Destination candidate:** GitLab public project `hamedonassar95/Devobs` (89037773).
**Status:** REVIEW ONLY. No GitLab pipeline or repository synchronization has run for this pilot.

## Why this is safe to prepare before the monthly quota reset

`.gitlab-ci.yml` intentionally contains **two separate manual gates**:

1. At the pipeline level, `workflow: rules` admits only `CI_PIPELINE_SOURCE == "web"` on the GitLab default branch. All other sources, including pushes, merge requests, schedules, API and triggers, are rejected with `when: never`.
2. At the job level, `free_offline_smoke` uses `when: manual` and `allow_failure: false`. Creating a pipeline alone does not start the job. A separate deliberate job click is required and **can consume GitLab compute minutes**.

The job uses a digest-pinned Python 3.12.15 Bookworm image and only executes the existing `scripts/milestone_ledger.py --summary` command plus its small local regression test. The smoke test validates *repository documentation integrity and release-gate status only*. It makes no provider API calls, installs no packages, reads no credentials and deploys nothing. This is **not** a GitLab mirror, backup, CI replacement, SaaS GO, or acceptance of AI-9/P01.

## Validate now without GitLab minutes

From the canonical GitHub Devobs checkout:

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_free_ci_pilot.py' -v
python3 scripts/milestone_ledger.py --summary
python3 -m compileall -q tests/test_gitlab_free_ci_pilot.py
```

You can also use GitLab's **Pipeline editor → Validate → Lint CI/CD sample** without running a job. A local YAML parser can check syntax, but neither local parsing nor the GitLab lint result proves that a runner was allocated.

## Future activation, only after owner approval and free-quota verification

1. Verify the GitLab namespace's **remaining included compute minutes** and whether GitLab-hosted runners can allocate a job. Do not raise spending limits, subscribe to a paid plan or bypass GitLab verification.
2. Confirm the *exact reviewed* GitHub source SHA and the current GitLab destination SHA. GitLab currently has an old imported `main`; the new YAML does not appear there merely by opening a GitHub PR. Consult the existing [fast-forward preflight](GITLAB_FAST_FORWARD_PREFLIGHT.md). Any GitLab branch write needs separate owner approval and protected-branch compliance; never force-push or use `git push --mirror`.
3. After an independently reviewed source transfer is approved and completed, validate the actual `.gitlab-ci.yml` in GitLab CI Lint. Only then, with the quota available, choose **Build → Pipelines → New pipeline**, select `main`, and manually start the `free_offline_smoke` job. This is an example of a future process, **not** an instruction to use minutes now.
4. Record the exact GitLab commit, job/runner ID, pipeline status, elapsed minutes and any failures. If the runner cannot be assigned, stop and classify `RUNNER_UNAVAILABLE`; do not rerun repeatedly.

The image is pinned to the official Docker Hub Python multi-platform index digest; review and refresh that digest in a separate PR when an updated supported patch is required. Python job scope is read-only verification.

## Mandatory exclusions

- No secrets, tokens, copied private project source, service accounts, privileged or self-hosted runners, paid inference, deployments, or new automatic schedules.
- Do not change `main`, `AGENTS.md`, GitHub/GitLab repository permissions, GitLab budget controls, or existing GitHub CI/CodeQL/Trivy workflows.
- Keep `P01 BLOCKED / NO-GO`, `AI-9 BLOCKED`, `Codex runtime OPEN` until independent acceptance.

References: [GitLab workflow rules](https://docs.gitlab.com/ci/yaml/workflow/), [manual jobs](https://docs.gitlab.com/ci/jobs/job_control/), [CI Lint](https://docs.gitlab.com/ci/yaml/lint/), [Docker Official Python image index](https://hub.docker.com/layers/library/python/3.12-slim-bookworm/).
