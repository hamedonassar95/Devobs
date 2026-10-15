# Amazon ECS deployment setup

The `Deploy to Amazon ECS` workflow is manual and requires an explicit confirmation. Pushes to `main` do not start an AWS deployment. It uses GitHub OIDC to assume an AWS IAM role; no long-lived AWS access keys are stored in GitHub.

## GitHub configuration

Create these repository variables under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Expected value |
| --- | --- |
| `AWS_REGION` | AWS region, such as `us-west-2` |
| `AWS_ROLE_ARN` | IAM role ARN allowed to deploy this repository |
| `ECR_REPOSITORY` | Existing Amazon ECR repository name |
| `ECS_SERVICE` | ECS service name |
| `ECS_CLUSTER` | ECS cluster name |
| `ECS_TASK_DEFINITION` | Path to the task definition JSON in the repository |
| `CONTAINER_NAME` | Container name in that task definition |

The repository must contain a `Dockerfile` and the task definition file. The workflow validates these values before requesting AWS credentials.

## AWS role trust and permissions

Configure an IAM OIDC provider for `token.actions.githubusercontent.com`. Restrict the role trust policy to this repository and the GitHub `production` environment, for example the subject `repo:hamedonassar95/Devobs:environment:production`. Grant only the ECR upload actions for the configured repository and the ECS task-definition/service actions needed for that cluster and service. Do not use IAM user access keys.

Configure the GitHub `production` environment with required reviewers if deployment approval is needed. Then open **Actions → Deploy to Amazon ECS → Run workflow**, select the confirmation checkbox, and review the run summary.

Until all variables, IAM trust, the task definition, and the Dockerfile are configured, a confirmed run stops at preflight validation before any AWS authentication or deployment request.
