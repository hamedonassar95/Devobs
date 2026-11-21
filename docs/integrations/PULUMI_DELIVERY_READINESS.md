# Pulumi Delivery readiness

Review date: **2026-11-21**. Repository baseline:
`f02319237b604d5447598cfb6f2d39e66e14d3f0`.
**VERIFIED:** source/documentation inspection and offline contract tests only.
**UNVERIFIED:** account eligibility, authentication, live interoperability and costs.
This proposal does not activate Delivery or change existing deployment ownership.

## Product and compatibility

**VERIFIED from official documentation:** [Pulumi Delivery](https://www.pulumi.com/product/delivery/)
is a public-preview release-pipeline product in Pulumi Cloud. Its
[documentation](https://www.pulumi.com/docs/delivery/) describes sources, releases,
stages, stack updates, jobs, artifacts and gates. It is not another name for the
existing Terraform configuration, nor an installed Devobs integration.

**ASSUMED design fit:** Delivery could later consume references to immutable
artifacts already built and checked by GitHub Actions. GitHub Actions remains
the default CI/deployment entry point; existing GCP/Terraform definitions remain
authoritative. Current static publication is Pages, not a verified GCP workload.
See the [baseline and interface](../architecture/MULTICLOUD_INTEGRATION_ARCHITECTURE.md).
No Terraform state, resource ownership or runner is migrated by this proposal.

## Documented API and authentication boundary

**VERIFIED documentation, NOT live-tested:** the
[Delivery REST reference](https://www.pulumi.com/docs/reference/cloud-rest-api/delivery/)
documents preview read operations including:

```text
GET /api/preview/delivery/{orgName}/programs
GET /api/preview/stacks/{orgName}/{projectName}/{stackName}/delivery/program
GET /api/preview/stacks/{orgName}/{projectName}/{stackName}/delivery/runs/{run-number}
```

These routes are explicitly preview and can change without notice. A future
adapter must pin its reviewed schema, reject unknown/incomplete responses,
bound time/bytes, reject redirects and allow only the approved origin and scope.
Do not infer that every credential has read-only scope.

The [Cloud REST authentication reference](https://www.pulumi.com/docs/reference/cloud-rest-api/)
documents token authentication and media type `application/vnd.pulumi+8`.
A future operator must establish account access and least privilege externally;
this task neither obtains a token nor verifies the account. No credential value,
placeholder token, token file or authentication request belongs in the fixtures.
[Cloud credentials](https://www.pulumi.com/docs/delivery/guides/cloud-credentials/)
for deploying stacks are a separate permission boundary. Existing Google WIF
does not automatically grant Pulumi Cloud, ESC or Azure access.

## Stages, human gates and interoperability

**ASSUMED future design, all mutation stages disabled:**

1. Review source, exact SHA, artifact digest and permitted assessment scope.
2. Reuse existing CI results; absent/skipped evidence is not a pass.
3. Produce an offline assessment and cost/permission review packet.
4. Require a separate human decision before any sandbox provider connection.
5. Require another scoped human decision before any production change.

The existing [human approval gate](../../scripts/human_approval_gate.py) and
[integration control plane](../architecture/INTEGRATION_CONTROL_PLANE.md)
remain authoritative. A Delivery decision or agent response cannot approve itself.

**VERIFIED important plan distinction:** [approval gates](https://www.pulumi.com/docs/delivery/concepts/stages-and-gates/)
are Pro/Enterprise features. A manual gate is different: a sufficiently privileged
credential can continue it. Do not claim Free provides named multi-user approval
enforcement. Decision gates invoke a model and are excluded from this proposal.
Vendor previews can omit arbitrary job effects or unavailable stack previews;
Devobs must review the full intent, not only the vendor preview. Stage graphs
also require local cycle checks; vendor docs say cycles are not detected.

Future interoperability should pass an approved artifact reference from the
existing GitHub workflow. It must not add a second auto-deployer or run arbitrary
commands from issue/PR text. No webhook, trigger or GitHub App is installed here.
If future webhooks are selected, separately verify their documented authenticity,
replay protection and delivery behavior; no signature scheme is assumed now.

## Costs and licensing

**VERIFIED published terms, not an account quote:** [pricing](https://www.pulumi.com/pricing/)
advertises Free at $0/no card, one user, one Delivery pipeline and up to 500
workflow minutes. Paid editions advertise additional pipelines at $20/month
and hosted workflow minutes at $0.01/minute outside applicable allowances.
Underlying cloud resources, storage, transfer, IaC/ESC use and AI tokens can add
separate charges. Actual plan, allowance, region/taxes and enforceable stop
behavior are **UNVERIFIED**. A free allowance is not an all-in spending cap.

Pulumi IaC's [Apache-2.0 licence](https://github.com/pulumi/pulumi/blob/master/LICENSE)
does not license the hosted Delivery service or automatically cover every SDK.
[Pulumi terms](https://www.pulumi.com/terms-and-conditions/) and the exact future SDK/provider
licences require review before adoption. No SDK is installed by this change.

## Failure and rollback

**ASSUMED operating design:** missing authentication, approval, scope, price or
evidence blocks the future adapter. Do not retry provider mutations blindly;
first reconcile whether the prior action took effect. Roll back this readiness
change by reverting its code/docs only. Future infrastructure rollback requires
its own reviewed intent and human authorization, not automatic destroy.
Existing [Pages rollback](../../.github/workflows/rollback-pages.yml) is a
separate site mechanism and is not a Pulumi/cloud-data rollback guarantee.

**Verdict:** compatible for an offline, optional assessment design; live account,
approval-plan adequacy and deployment compatibility remain **UNVERIFIED**.
