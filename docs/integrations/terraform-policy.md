# Terraform policy check with Conftest

**Status:** local HCL validation plus a required CI check using Conftest with OPA/Rego policies. This policy reviews the current Terraform source; it does not run `terraform plan` or `apply`, call Google Cloud, provision resources, change P01/P16 status, or authorize a deployment.

## What the policy checks

- Terraform block types are limited to `terraform`, `provider`, `resource`, `variable`, and `output`; new `data` sources and modules require an explicit policy review.
- The only resource type and address currently allowed are `google_artifact_registry_repository.devobs_images`.
- Its format, region and repository ID must use the reviewed values/variables, its labels must be exactly `application=devobs` and `managed_by=terraform`, and unknown resource settings fail closed.
- Only one Google provider block is allowed; it must use `var.project_id` and `var.region`, with no inline credentials or extra provider settings.

This is a narrow repository guard, not a complete Terraform security scan, proof that a later plan is safe, cloud authorization, or evidence that P01 is ready. A policy failure is a request for code and policy review, not a reason to weaken the rule automatically.

## Local validation

Use the checksum-pinned Conftest 0.71.1 release, then run from the repository root:

```sh
conftest --version
conftest test --combine --parser hcl2 --policy policy/terraform infra/terraform/*.tf
python3 -m unittest discover -s tests/terraform_policy -v
```

CI downloads the Linux x86_64 archive from the official v0.71.1 release and checks SHA-256 `c3f6b2a753bd56e377a1e51a95ae3e057f926f2e9139f7d5b5dfbbaf810f7985` before executing it. The test suite includes a positive check against the repository configuration and negative fixtures for an unapproved resource, a changed label, a missing resource, an unreviewed data source and inline provider credentials. It uses only temporary local files.

## Cost and limits

Conftest is Apache-2.0 and the policy evaluation is local, so it adds no hosted policy service or cloud resource. The CI job downloads the pinned binary and uses runner time; any GitHub Actions usage limits or billing depend on the repository plan. No Terraform plan is produced, so this check does not resolve provider data or prove the values that a future plan would use.

## Disable or roll back

Remove the Conftest installation and policy-test steps from `terraform-validate`, then delete `policy/terraform/main.rego`, `tests/terraform_policy/test_conftest_policy.py`, and this document. No cloud cleanup is needed because the check never creates resources.

## Official references

- [Conftest HCL2 parser and CLI options](https://www.conftest.dev/options/)
- [Conftest v0.71.1 release](https://github.com/open-policy-agent/conftest/releases/tag/v0.71.1)
- [Conftest v0.71.1 Apache-2.0 license](https://github.com/open-policy-agent/conftest/blob/v0.71.1/LICENSE)
- [Open Policy Agent Apache-2.0 license](https://github.com/open-policy-agent/opa/blob/main/LICENSE)
- [Terraform JSON format and sensitive values](https://developer.hashicorp.com/terraform/internals/json-format)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [GitHub Actions workflow command for adding a system path](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#adding-a-system-path)
