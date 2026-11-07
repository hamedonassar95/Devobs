# Workflow integration map

Executable GitHub Actions workflows live under [`.github/workflows/`](../.github/workflows/). This folder is a documentation index; it intentionally does not duplicate workflow YAML.

The existing CI already runs validation, security checks, CodeQL, container smoke tests and Trivy. Keep those checks as the source of truth. The existing Codex review and optional PR-Agent review are mutually exclusive through `DEVOBS_AI_REVIEW_PROVIDER`; PR-Agent is disabled unless the provider, budget, provenance, and existing API-secret checks all pass.

External GitHub Actions must use a full commit SHA. Container actions must use an immutable digest. Do not use `pull_request_target` to expose credentials to fork content.
