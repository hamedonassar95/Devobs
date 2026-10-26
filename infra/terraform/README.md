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

## Apply boundary

Applying this configuration creates a Google Cloud resource and Artifact Registry storage may incur charges after images are uploaded. Before applying, the owner must review the project, region, billing impact, required Artifact Registry API, and IAM access. Supply `project_id` through an untracked local `.tfvars` file or environment configuration; never commit credentials or real tfvars. See the [Google provider resource documentation](https://registry.terraform.io/providers/hashicorp/google/8.8.1/docs/resources/artifact_registry_repository), [Terraform validate documentation](https://developer.hashicorp.com/terraform/cli/commands/validate), and [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing).
