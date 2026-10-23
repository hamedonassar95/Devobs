# DevSecOps controls and scope

This page describes the security checks configured for the original Devobs repository. It is a static GitHub Pages site; the Python dependencies listed in `requirements-dev.txt` are development and CI tools, not application runtime packages.

**VERIFIED from repository files:** the controls listed below are present in this branch's CI and configuration. **UNVERIFIED:** hosted CI results for this change and account-level GitHub security settings.

## CI security checks

| Control | Repository implementation | Scope |
| --- | --- | --- |
| Python source analysis | Bandit in `.github/workflows/ci.yml` | Scans `scripts/`, excluding the static site contract checker. |
| Dependency vulnerability audit | `pip-audit --requirement requirements-dev.txt` | Audits the direct and resolved transitive Python development dependencies. A finding fails the security job. |
| Secret scanning | Gitleaks GitHub Action | Scans repository history during CI. |
| Workflow supply-chain check | `scripts/check_action_pins.py` | Requires third-party GitHub Actions to use full commit SHAs. |
| Dependency updates | `.github/dependabot.yml` | Opens weekly update pull requests for Python packages and GitHub Actions. |
| Security reporting | `SECURITY.md` | Describes private vulnerability reporting and response expectations. |

These checks run in the existing required `security` job and feed the existing `validate` check. They use the repository's current workflow permissions; this change does not add deployment permissions, credentials, or new Actions.

## Run the Python checks locally

From the repository root, using Python 3.10 or newer:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m bandit -r scripts -x scripts/check_site.py
pip-audit --requirement requirements-dev.txt
```

`pip-audit` documents requirements-file auditing and its command options in the [official usage guide](https://github.com/pypa/pip-audit#usage). The audit needs network access to retrieve vulnerability data.

## Scope and operational limits

- The dependency audit covers `requirements-dev.txt`. There is no application dependency manifest for the current static site, so this does not scan runtime packages.
- Gitleaks, Bandit, and `pip-audit` findings still need human review and remediation; a green scan does not prove the site is vulnerability-free.
- This repository change configures the checks. A successful hosted CI run on the resulting commit remains UNVERIFIED until CI runs after the change is merged.
- Repository files cannot establish account-level CodeQL, branch-protection, or Dependabot settings. Confirm those in GitHub if they are required; this change does not modify them.
