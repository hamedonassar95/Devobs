# Terraform: container image registry baseline

This configuration manages one regional Google Artifact Registry Docker repository for the optional static-site image. It does not create a GKE cluster, deploy a workload, grant IAM roles, or modify GitHub settings.

## Validate without cloud access

From the repository root:

```sh
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init -backend=false -input=false -lockfile=readonly
terraform -chdir=infra/terraform validate
```

CI runs these validation commands only; it never runs `terraform plan` or `terraform apply`.

The GCS backend is configured with a placeholder bucket name. Before a normal `terraform init`, replace it with the name of an existing, owner-managed state bucket. The CI command uses `-backend=false` and does not access Google Cloud. See the [official GCS backend documentation](https://developer.hashicorp.com/terraform/language/backend/gcs).

## Apply boundary

Applying this configuration creates a Google Cloud resource and Artifact Registry storage may incur charges after images are uploaded. Before applying, the owner must review the project, region, billing impact, required Artifact Registry API, and IAM access. Supply `project_id` through an untracked local `.tfvars` file or environment configuration; never commit credentials or real tfvars. See the [Google provider resource documentation](https://registry.terraform.io/providers/hashicorp/google/8.8.1/docs/resources/artifact_registry_repository), [Terraform validate documentation](https://developer.hashicorp.com/terraform/cli/commands/validate), and [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing).

## P01-T09: synthetic Terraform plan acceptance (no deployment)

The additional `tests/registry_mock.tftest.hcl` uses Terraform's [mock_provider](https://developer.hashicorp.com/terraform/language/tests/mocking) and explicit `command = plan` in **all three** test runs. It tests a Docker repository's format/region/endpoint and negative variable validation with synthetic identifiers. In contrast, **ordinary** `terraform test` files default to `apply` and may create resources; do not add a test with `apply`, a real provider, external data sources, or secrets without separate security review.

After the offline `init -backend=false` command above, run:

```sh
terraform -chdir=infra/terraform test -no-color
python3 -m unittest discover -s tests -p 'test_terraform_workflow_contract.py' -v
```

CI checks the mocked tests in the existing `terraform-validate` job; it does not run `terraform plan` or `terraform apply`, access the real GCS backend, or use Google Cloud credentials. The provider binary is still downloaded and checked against the committed lockfile during CI initialization. This test does **not** prove a live P01 staging stack, owner-selected region, cloud budget enforcement or actual runtime RLS/OIDC. P01 remains **NO-GO/BLOCKED**.

Terraform native tests: https://developer.hashicorp.com/terraform/language/tests
