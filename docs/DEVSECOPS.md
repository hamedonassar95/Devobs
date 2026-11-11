# DevSecOps controls and scope

This page describes the security checks configured for the original Devobs repository. It is a static GitHub Pages site; the Python dependencies listed in `requirements-dev.txt` are development and CI tools, not application runtime packages.

**VERIFIED from repository files:** the controls listed below are present in this branch's CI and configuration. **UNVERIFIED:** hosted CI results for this change and account-level GitHub security settings.

## CI security checks

| Control | Repository implementation | Scope |
| --- | --- | --- |
| Python source analysis | Bandit in `.github/workflows/ci.yml` | Scans `scripts/`, excluding the static site contract checker. |
| Dependency vulnerability audit | `pip-audit --requirement requirements-dev.lock` and `pip-audit --requirement requirements-api.lock` | Audits the resolved development/security and proposed API dependency trees. A finding fails the security job. |
| Secret scanning | Gitleaks GitHub Action | Scans repository history during CI. |
| Workflow supply-chain check | `scripts/check_action_pins.py` | Requires third-party GitHub Actions to use full commit SHAs. |
| Dependency updates | `.github/dependabot.yml` | Opens weekly update pull requests for Python packages and GitHub Actions. |
| OpenSSF repository posture | `.github/workflows/reusable-openssf-scorecard.yml` | Checksum-pinned CLI, read-only token, informational report; called manually for Devobs. |
| Security reporting | `SECURITY.md` | Describes private vulnerability reporting and response expectations. |

The CI controls above run in the existing required `security` job and feed the existing `validate` check. The manual OpenSSF workflow below is separate and is not a required check. It adds no deployment permissions or stored secrets; its GitHub token is read-only.

## OpenSSF Scorecard report

The manual `.github/workflows/openssf-scorecard.yml` workflow calls a reusable workflow that installs the official OpenSSF Scorecard CLI v5.6.0 from a SHA-256-pinned release archive and scans the caller repository with read-only GitHub token permissions. Run the Devobs entrypoint from `main`; its summary records the scanned repository, ref, and full source SHA. It is not a merge gate, does not publish to the Scorecard API, and does not call an AI provider. The full JSON artifact is opt-in and defaults off; the Devobs caller leaves it off because this repository is public. Other callers should opt in only when artifact visibility and retention fit that repository.

This repository's P04 offline evaluation scorecard is a separate feature that measures a deterministic synthetic adviser fixture. OpenSSF Scorecard measures repository security practices; neither score substitutes for the other or establishes hosted runtime readiness.

The same reusable workflow can be called by another repository at a reviewed immutable Devobs commit. The [GitHub reusable workflow documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations) describes caller permissions and access rules; the caller must allow reusable workflows in its Actions settings, and the called workflow cannot elevate the caller's `GITHUB_TOKEN` permissions. The phone-repair repository already has its own Scorecard CLI report in [PR #156](https://github.com/hamedonassar95/phone-repair-assistant-v2/pull/156); converting that report to this shared workflow is a separate follow-up after this workflow is merged and its caller settings are confirmed.

The [OpenSSF Scorecard CLI](https://github.com/ossf/scorecard) is used instead of its GitHub Action so the workflow remains usable for private callers without requiring GitHub Advanced Security. Its score and findings are repository-posture signals only; findings still need human review.

## Run the Python checks locally

From the repository root, using Python 3.10 or newer:

```sh
python3 -m pip install --require-hashes -r requirements-dev.lock
python3 -m bandit -r scripts -x scripts/check_site.py
pip-audit --requirement requirements-dev.lock
pip-audit --requirement requirements-api.lock
```

`pip-audit` documents requirements-file auditing and its command options in the [official usage guide](https://github.com/pypa/pip-audit#usage). The audit needs network access to retrieve vulnerability data.

## Scope and operational limits

- The published static site has no application dependencies. The proposed, undeployed API has a separate hash-locked dependency tree in `requirements-api.lock`; it remains unevaluated under a hosted runtime.
- Gitleaks, Bandit, and `pip-audit` findings still need human review and remediation; a green scan does not prove the site is vulnerability-free.
- This repository change configures the checks. A successful hosted CI run on the resulting commit remains UNVERIFIED until CI runs after the change is merged.
- Repository files cannot establish account-level CodeQL, branch-protection, or Dependabot settings. Confirm those in GitHub if they are required; this change does not modify them.
