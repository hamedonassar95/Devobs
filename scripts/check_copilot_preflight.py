"""Validate Copilot credential setup without printing it or calling a model."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote


PAT_CREATION_PAGE_URL = "https://github.com/settings/personal-access-tokens/new"


def evaluate(token: str | None, repository: str) -> tuple[bool, str]:
    """Return a safe status summary based only on token presence and prefix."""
    repository_path = quote(repository, safe="/-._")
    settings_link = (
        f"[`COPILOT_GITHUB_TOKEN`](https://github.com/{repository_path}/settings/secrets/actions)"
        if repository_path
        else "`COPILOT_GITHUB_TOKEN` in the repository Actions secrets settings"
    )
    base = [
        "## Copilot provider preflight",
        "",
        "No model request was made by this check.",
        "",
    ]

    if not token:
        base.extend([
            "**Result: blocked.** The repository Actions secret `COPILOT_GITHUB_TOKEN` is missing.",
            "",
        ])
        passed = False
    elif not token.startswith("github_pat_"):
        base.extend([
            "**Result: blocked.** The configured secret does not use the required fine-grained token format (`github_pat_`). The value was not shown or logged.",
            "",
        ])
        passed = False
    else:
        base.extend([
            "**Result: format accepted.** The token has the required `github_pat_` prefix.",
            "This check does not verify the `Copilot Requests: Read` permission, Copilot access, quota, or model availability.",
            "Confirm this is a dedicated token saved as `COPILOT_GITHUB_TOKEN` with account permission `Copilot Requests: Read`.",
            "Keep `POLICY_AUDIT_TOKEN` separate; it serves the read-only repository-policy audit (`Administration: Read`).",
            "",
        ])
        return True, "\n".join(base)

    base.extend([
        "### Required setup",
        "",
        f"1. [Create a fine-grained personal access token]({PAT_CREATION_PAGE_URL}) under the GitHub account that owns the Copilot entitlement.",
        "2. Under **Account permissions**, grant **Copilot Requests: Read**.",
        f"3. Save the token as the repository Actions secret {settings_link}.",
        "4. Rerun **Actions → AI Provider Preflight** on `main` and choose `copilot`.",
        "",
        "`POLICY_AUDIT_TOKEN` serves the separate read-only repository-policy audit (`Administration: Read`); create a dedicated Copilot token for `COPILOT_GITHUB_TOKEN`.",
        "Never paste a token into chat, source files, issues, or workflow logs.",
        "",
    ])
    return passed, "\n".join(base)


def main() -> int:
    passed, summary = evaluate(
        os.environ.get("COPILOT_GITHUB_TOKEN"),
        os.environ.get("GITHUB_REPOSITORY", ""),
    )
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as output:
            output.write(summary)
    else:
        print(summary)
    print("Copilot credential format accepted." if passed else "Copilot credential setup needs attention.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
