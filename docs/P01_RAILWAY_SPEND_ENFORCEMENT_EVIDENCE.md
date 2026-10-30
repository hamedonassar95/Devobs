# P01 Railway Spend Enforcement Evidence

**Assessment date:** 2026-10-30. **Decision:** P01 remains **NO-GO / BLOCKED**. No Railway account, workspace, service, database, volume, or other resource was created, and no spend or test run occurred. Railway Support sent a written response on 2026-10-30 to the owner's pre-sales inquiry; a brief acknowledgement was sent on the owner's behalf and the inquiry was closed. The response is provider correspondence, not a contractual amendment or EU data-processing commitment.

The owner-approved ceiling is **USD 100 total per month**, conditional on verifiable enforcement. Railway is an evaluation candidate for Amsterdam; the location is only preliminarily acceptable, and contractual data-residency terms must be resolved before any real data. The signed conditional decision and remaining P01 controls are in [P01_ACTIVATION_READINESS.md](P01_ACTIVATION_READINESS.md).

## Written Railway Support response — received 2026-10-30

**VERIFIED (owner's Gmail correspondence):** Railway Support (`support@railway.com`) answered the questions in the pre-sales email. The response says:

- There is **no single hard limit for the complete invoice**. Compute and Agent limits are independent; the subscription fee is outside both.
- Compute usage covers CPU, memory, storage, and network egress. At the Compute limit, workloads go offline and bucket access is suspended, including access to the bucket holding PostgreSQL PITR data. At the Agent limit, Agent use stops but workloads continue running.
- Railway provides **no guaranteed maximum enforcement delay or maximum overrun**. It described alerts at 75%, 90%, and 100%.
- Workloads and bucket access are suspended, but volumes, backups, and bucket storage **continue to incur charges**. Nothing is deleted by the limit; the owner must delete a volume or bucket to stop its storage charges, which deletes that data. The response did not specify a retention duration.
- Railway says workloads, volumes, volume backups, and PITR data stay in the deploy region; PITR buckets run on Tigris. Service logs are stored in US West. Railway states that no plan has a contractual EU-only processing commitment.

**Decision from this evidence:** Railway does not meet the owner's total USD 100/month cap requirement. Its limit cannot stop every billable category, the provider gives no bounded overrun, and some storage charges continue after the workload shutdown. The written response also does not satisfy the preliminary Amsterdam residency condition for real data. No Railway resources may be created under this P01 decision.

**Limits:** The response is written support evidence, not a contract. The exact retention period, tax treatment, managed PostgreSQL meter details, and subprocessor-specific transfer terms remain **UNVERIFIED**. The owner can verify the response in the Gmail thread; the public repository does not contain the email or personal mailbox metadata.

## What the official Railway documentation establishes

| Claim | Evidence | Limit of the evidence |
| --- | --- | --- |
| A configured hard usage limit takes all workloads offline when usage reaches the limit. | Railway says all workloads are taken offline at the specified hard limit to prevent further resource usage: [Cost Control — Hard limit](https://docs.railway.com/pricing/cost-control#hard-limit). | The page gives no maximum enforcement latency or maximum overrun. This is a published behavior, not a measured result for a Devobs workspace. |
| The minimum hard limit is USD 10. | [Cost Control — Usage limits FAQ](https://docs.railway.com/pricing/cost-control#usage-limits-faq) says the minimum is $10; usage limits are available on all subscription plans. | This is a minimum configurable usage threshold, not a USD 10 maximum invoice guarantee. |
| Compute Usage includes CPU, memory, storage, and network egress for services. | [Cost Control — Compute vs. Agent usage limits](https://docs.railway.com/pricing/cost-control#compute-vs-agent-usage-limits). | The documentation does not explicitly state how managed database templates, persistent volumes, backups, or PITR are treated after the workloads stop. |
| Agent Usage is a separate meter and separate hard limit. | The same [Compute vs. Agent section](https://docs.railway.com/pricing/cost-control#compute-vs-agent-usage-limits) says reaching the Compute limit takes workloads offline while the Agent remains available; reaching the Agent limit disables the Agent while workloads continue running. | These are separate controls, not one combined USD 100 cap. A Compute limit alone does not stop Agent usage. |
| Railway documents early email notifications. | [Cost Control — Custom email alert and hard limit](https://docs.railway.com/pricing/cost-control#custom-email-alert) allows a custom email alert; the [Hard limit section](https://docs.railway.com/pricing/cost-control#hard-limit) documents reminders at 75%, 90%, and 100%. | Notifications are alerts, not enforcement, and do not establish delivery latency. |
| Stopped services may restart after the limit changes or at the next billing cycle. | The [Usage limits FAQ](https://docs.railway.com/pricing/cost-control#usage-limits-faq) says Railway automatically redeploys after a limit is raised or removed and will try to restart resources in the next billing cycle. | The documentation does not establish that a limit shutdown permanently disables future billing. A test must not be left active across a new billing cycle. |

## What remains unverified

- **VERIFIED (support response):** Railway does not guarantee a maximum enforcement delay or overrun; the value is therefore unbounded by the evidence available to this assessment.
- **VERIFIED (support response):** storage charges for volumes, backups, and buckets continue during suspension; deletion stops those charges but deletes the data. **UNVERIFIED:** the retention duration and exact billing treatment of every managed PostgreSQL component.
- **VERIFIED (support response):** Compute and Agent use have separate limits, and the subscription fee is outside both. **UNVERIFIED:** whether taxes or other invoice line items have any separate controls; there is no complete-invoice hard cap in the described controls.
- **VERIFIED (support response):** service logs are stored in US West, and Railway offers no contractual EU-only processing commitment on any plan. The response says workload/volume/backup/PITR data stay in the deploy region and that PITR uses Tigris. **UNVERIFIED:** exact replica locations and subprocessor-specific contractual transfer terms.
- **UNVERIFIED:** Railway's settings for any Devobs account. No Railway account or workspace was inspected.

## Proposed compensating controls — not configured; insufficient for P01

1. The Compute limit can be set to **USD 10**, the documented minimum, but the support response confirms this is **not** a safe substitute for a USD 100 total invoice cap: Agent, subscription, and persistent-storage charges are separate or continue after shutdown.
2. Set a custom email alert at **USD 5** (50% of the proposed Compute limit). Retain Railway's documented reminders at **USD 7.50 (75%)** and **USD 9 (90%)**. Treat every alert as an operator signal only.
3. A separate Agent limit does not stop workloads; disabling Agent use does not close the total-bill gap.
4. Do not use a managed database, persistent volume, backup, or PITR on Railway for P01 under the current decision. Support says their storage charges continue during enforcement and no EU-only contractual processing commitment exists.
5. Do not create resources or spend money under this evidence packet. The prior USD 100 approval is conditional and does not approve the experiment's spend.

## Pre-registered compute enforcement test — NOT RUN

**Policy ID:** `p01-railway-hard-limit-enforcement-v1`  
**Registration baseline:** `origin/main` `f691baeceabdeecffcd1f6dd826c1972f284b4f3`; this design must be committed before any measurement.  
**Status:** Design frozen for review; **NOT RUN**. The support response now establishes that this Compute-only test cannot demonstrate a total invoice cap or bound storage charges. It is not a qualifying path to P01 GO and should not be run for that purpose.
**Purpose:** measure the observed workload shutdown delay and actual billed Compute overrun for one isolated, stateless workload. This test does not claim to test managed databases or persistent storage.

### Fixed test settings

| Setting | Frozen value |
| --- | --- |
| Workspace | A new, isolated Railway workspace used only for this test; no shared projects or existing resources. Create only after separate explicit owner authorization. |
| Starting usage | Compute and Agent usage must both display USD 0 for the active billing cycle before deployment; otherwise abort without running the workload. |
| Compute hard limit | USD 10 per billing cycle (documented minimum). |
| Custom email alert | USD 5. |
| Documented Railway notifications | 75% and 90% of the hard limit (USD 7.50 and USD 9); retain the 100% notification as evidence of shutdown. |
| Agent | Separate hard limit at the lowest value allowed by the selected plan; Agent use must remain zero. Record the displayed/configured value before starting. |
| Workload | One synthetic, stateless service with bounded CPU use and a health endpoint; no database, persistent volume, backups/PITR, credentials, customer data, or intentionally generated external egress. |
| Observation interval | Record Railway Usage and workload/health status in UTC at intervals no longer than 15 seconds from the first displayed USD 9 until shutdown. Preserve screenshots or exports and timestamps. |
| Shutdown-delay acceptance | Workload must become unavailable within 60 seconds of the first Railway usage reading at or above USD 10. This is a proposed test criterion, not a Railway promise. |
| Overrun acceptance | After the final Railway invoice/usage record settles, all charges attributable to the test workspace must total no more than USD 20. The allowed Compute overrun is therefore at most USD 10, leaving at least USD 80 below the owner's monthly ceiling. This is a proposed test criterion, not a provider guarantee. |
| Manual safety stop | If the service is still active at USD 20 of displayed test usage, stop the workload immediately and record the test as failed/censored. This manual stop is not a proven financial cap and does not bound later billing adjustments. |

### Measurement and reporting

- Record the exact UTC time each usage reading is observed, the displayed Compute and Agent totals, the email-alert delivery times, the Railway deployment status, and each health-probe result.
- Define `t_limit` as the first observed Railway usage reading at or above USD 10 and `t_offline` as the first confirmed offline status plus failed health probe. Report observed delay as `t_offline - t_limit`, including the 15-second observation resolution. If Railway's usage display is delayed or too coarse to identify a threshold interval, report the enforcement delay as **UNMEASURABLE**, not as zero.
- Define observed Compute overrun as `final_settled_compute_usage - USD 10`, floored at zero. Report the complete final test-workspace charge separately; do not infer the complete invoice from Compute alone.
- Observe the account through the final applicable invoice or settled usage record. If any billable item remains unsettled or is excluded from the visible meter, mark the result **INCONCLUSIVE**.
- Capture all usage and shutdown evidence, then remove the ephemeral test service/workspace under separate owner authorization before the next billing cycle, because Railway documents that stopped resources may restart in a later cycle. If owner-authorized cleanup cannot occur before that boundary, do not start the test.
- Pass only if the workload is taken offline automatically, observed delay is at most 60 seconds, settled test-workspace charges are at most USD 20, Agent use is zero, and the usage record is complete. Any missing observation, manual shutdown before automatic shutdown, later restart, extra charge, or unbounded/unknown billing category is a fail or inconclusive result. No repeat run or parameter change is permitted under this registration.

### Authorization and scope limits

This registration does **not** authorize account creation, resource creation, a payment method, or spending. Before running it, obtain a new explicit owner decision that names the one-time test, its billing period, the accepted exposure, and the authorized pre-cycle cleanup. If that exposure cannot be bounded below the USD 100 monthly ceiling, do not run the test.

A passing compute-only test proves only the observed behavior of that tested workspace, plan, and ephemeral workload. It does not prove managed-database, volume, backup/PITR, Agent, tax, or contractual residency behavior. Because P01 includes a database, these unresolved categories remain outside any GO until Railway answers them in writing or a separately approved test validly covers them. No database or persistent storage may be used to extend this test before written confirmation.

## Railway support request and closure

The pre-sales inquiry below was sent from the owner's Gmail account at the owner's instruction, and Railway replied with the written response summarized above. An acknowledgement was sent on the owner's behalf; no further follow-up is pending. The test registration is retained as a historical, unrun design and is not a route to GO.

> We plan to set a $100/month hard limit. Please confirm in writing: (1) the maximum delay or overshoot between reaching the limit and workloads being stopped; (2) whether managed databases, volumes, backups and network egress are all covered or continue to accrue charges after shutdown; (3) whether volume data and backups are retained after a hard-limit shutdown, and for how long.

## P01 budget-gate decision

**Current result: NO-GO / BLOCKED. Railway is rejected for the current bounded P01 scope.** Its separate limits do not cap the complete invoice; no maximum overrun is guaranteed; persistent-storage charges continue after shutdown; and the support response does not provide the required contractual EU-only processing commitment.

The prior Railway evidence path may not close the budget gate: its written response is negative for the required total cap, and the Compute-only test cannot cover all invoice categories. A future P01 budget gate requires a separately selected provider and evidence that its enforceable ceiling covers every in-scope billable category, including ongoing storage and any fixed or tax charges; any unbounded overrun or excluded billable category keeps P01 blocked. Provider, region, and residency changes need the owner's decision. No provider account, resource, test spend, or integration is authorized by this report.

## Alternative provider candidate — AWS new experience (research only)

**VERIFIED (official AWS documentation; not an account check):** AWS's *new* account experience offers a project-level spend limit on its Paid Plan. AWS says reaching the limit pauses the project and stops its resources; the configured ceiling applies to **pre-tax project costs**, excludes credits, and has a minimum of the greater of USD 20 or AWS's conservative estimate. The feature is unavailable on the advanced account experience, and enabling advanced features removes spend limits. A project owner remains responsible for monthly usage charges and recurring fees. See [AWS spend limits](https://docs.aws.amazon.com/accounts/latest/reference/create-spend-limit.html), [project creation and billing](https://docs.aws.amazon.com/accounts/latest/reference/create-project.html), and [advanced feature effects](https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.html).

AWS assigns new-experience projects by contact-address country to US East (Ohio), Europe (Stockholm), or Asia Pacific (Sydney); it does not let the owner select a specific Region in that experience. The currently documented European region is Stockholm (`eu-north-1`), not Amsterdam or Frankfurt. Advanced signup is required for exact Region selection, but that removes the spend-limit feature. See [AWS project Regions](https://docs.aws.amazon.com/accounts/latest/reference/project-regions.html) and [signup options](https://docs.aws.amazon.com/accounts/latest/reference/sign-up-for-aws.html). This is a material provider/region change and has not been approved by the owner.

**UNVERIFIED for Devobs/P01:** account eligibility; whether every required charge (especially persistent database/storage/backups, recurring fees, and taxes) is bounded by the project limit; any maximum enforcement delay or overrun; the applicable data-processing/residency terms and subprocessor locations; and compatibility with Devobs identity/network controls. AWS's service list includes RDS, EC2, EBS, S3, and VPC in the new experience, but that does not by itself prove all associated charges stop at the limit. See [supported services](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html). No AWS account was created, and no AWS support request was sent.

**Other reviewed controls are not substitutes:** Google Cloud's documented spend caps are scoped to one eligible service in one project, and persistent resources keep accruing charges; in-flight requests can add charges and overages are billed ([official documentation](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)). Laravel Cloud stops app/database/cache compute but retains billable storage and explicitly allows a small overage ([official documentation](https://laravel.com/cloud/docs/spending-limits)). Neither establishes the owner's complete USD 100 monthly invoice ceiling.

### Prepared AWS clarification request — NOT SENT

Before any account or project is created, AWS would need to confirm in writing:

> We are considering AWS's new experience for a synthetic-data-only Devobs staging project and require a USD 100 maximum total monthly invoice. Please confirm: (1) whether the project spend limit pauses all resources and prevents charges for RDS/PostgreSQL, EBS, S3, snapshots/backups, PITR, data transfer, CloudWatch/logging, and any recurring or account fees; (2) whether storage or any other charge continues after the project is paused; (3) the maximum enforcement delay and possible overrun; (4) how taxes are treated, since the documentation describes a pre-tax limit, and whether a lower pre-tax limit can guarantee a total invoice below USD 100; (5) the project Region and data locations, including logs and backups, for the country used in the owner's billing/contact address; and (6) the applicable contractual data-processing terms and subprocessors. Please cite current official terms for each answer.

**Status:** this is a prepared question only. No AWS support request has been sent. Sending it, creating an account, or creating resources requires the owner's explicit authorization for AWS. Before any account or resource creation, the owner would also need to accept or reject the assigned Stockholm region and separately approve any test spending. If no provider demonstrates a bounded complete invoice at or below USD 100, retain offline-only development and keep P01 **NO-GO / BLOCKED**. The existing AI-9 result remains **FAIL**.
