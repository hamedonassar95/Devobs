# Plannotator + Codex: optional local visual review pilot

**Status:** DOCUMENTED / RUNTIME UNVERIFIED. This is an operator-initiated local review aid, not an enabled service, CI gate, production safeguard, or automatic agent approval.

## Purpose and compatibility

[Plannotator](https://github.com/backnotprop/plannotator) is a local browser interface for annotating AI-agent plans, Markdown, and code diffs. Its [Codex integration](https://github.com/backnotprop/plannotator/blob/main/apps/codex/README.md) supports manual code review and Markdown annotation. Automatic plan review depends on Codex's **experimental Stop hook**, which is **not enabled** by this pilot.

- **Reviewed upstream release:** [v0.29.0](https://github.com/backnotprop/plannotator/releases/tag/v0.29.0) (2026-11-18). This is a research/reference pin, **not** an installed binary or approved artifact digest.
- **Scope:** optional use by the repository owner on a trusted workstation with a supported Codex CLI/desktop session and browser.
- **Not established:** operation inside ChatGPT iOS, Codex cloud, CI runners, remote browsers, or the Devobs hosted SaaS.
- **No dependency changes:** no third-party code, binary, package, hook, workflow, daemon, service, or container is installed or committed here.

## Setup: manual and opt-in only

1. Read [upstream installation and Codex docs](https://github.com/backnotprop/plannotator/blob/main/apps/codex/README.md) and the [v0.29.0 release](https://github.com/backnotprop/plannotator/releases/tag/v0.29.0) on your own workstation.
2. Before using an upstream installer, inspect its effects: the full Linux/macOS/WSL installer can auto-enable Codex hooks. **Do not run it as part of Devobs development or CI.** If testing the tool, obtain the specific reviewed release artifact only after locally verifying its provenance and published checksum; use its minimal/no-hook installation path.
3. Do **not** change `.codex/config.toml`, add `.codex/hooks.json`, or turn on global/repository hooks. `scripts/check_codex_capabilities.py` deliberately rejects newly enabled repo hooks until a separate security review updates that contract.
4. Keep reviews local; do not use share links, optional hosted AI review, cross-machine Inbox, or routine scheduling for Devobs. Set `PLANNOTATOR_SHARE=disabled` in the operator's own local shell before opening sensitive diffs. Avoid sharing access URLs or forwarding a listening port.
5. To opt out, close the local review process. No repository file or production setting requires changing.

## Manual workflow after a reviewed local install

From a trusted local checkout of the Devobs feature branch, review the intended diff with the **user-triggered** CLI:

```sh
plannotator review
```

For a standalone Markdown review:

```sh
plannotator annotate docs/CODEX_AGENT_OPERATING_MODEL.md
```

In a compatible Codex command environment, upstream also documents `!plannotator review` and `!plannotator annotate <path>`; command availability depends on the actual installed client. Submit comments as suggestions; independently inspect the resulting patch and rerun normal tests. Do not interpret a Plannotator approval as PR approval, production authorization, or proof of CodeQL/Trivy/tenant-isolation status.

## Acceptance and safeguards

1. **Source audit:** `git diff -- .codex .github scripts/check_codex_capabilities.py` shows no hook or CI changes from this pilot.
2. **Existing controls:** `python3 scripts/check_codex_capabilities.py` and `python3 scripts/milestone_ledger.py --summary` must remain valid; required GitHub CI on the exact PR SHA must complete successfully.
3. **Manual runtime evidence, if later approved:** on a user-controlled local workstation, record only Plannotator version, OS, command success/failure, and a sanitized screenshot of a synthetic diff. Do not post proprietary source, credentials, session transcripts, private links, or secrets.
4. **Release gate:** owner reviews the exact PR SHA and CI output before merging. P01 and AI-9 remain BLOCKED; do not enable new paid services, autonomous changes, cloud actions, automatic hooks, or deployment.
5. **Failure policy:** absent local binary/browser, unsupported hook behavior, missing checksum, or failed checks means **UNVERIFIED/BLOCKED**. Never silently activate hooks to make a demo work.

## Official / primary sources

- https://github.com/backnotprop/plannotator
- https://github.com/backnotprop/plannotator/blob/main/apps/codex/README.md
- https://github.com/backnotprop/plannotator/releases/tag/v0.29.0
- [Existing Codex governance](../CODEX_AGENT_OPERATING_MODEL.md) and [repository rules](../../AGENTS.md)
