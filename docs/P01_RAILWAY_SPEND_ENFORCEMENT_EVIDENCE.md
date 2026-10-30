# P01 Railway Spend Enforcement Evidence

**Assessment date:** 2026-10-30. **Decision:** P01 remains **NO-GO / BLOCKED**. This is documentation-only preparation against official public Railway documentation; no Railway account, workspace, service, database, volume, or other resource was created, and no spend or test run occurred.

The owner-approved ceiling is **USD 100 total per month**, conditional on verifiable enforcement. Railway is an evaluation candidate for Amsterdam; the location is only preliminarily acceptable, and contractual data-residency terms must be resolved before any real data. The signed conditional decision and remaining P01 controls are in [P01_ACTIVATION_READINESS.md](P01_ACTIVATION_READINESS.md).

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

- **UNVERIFIED:** the longest delay between crossing a hard limit and all applicable workloads becoming unavailable, and the greatest possible usage or invoice overshoot before shutdown.
- **UNVERIFIED:** whether managed PostgreSQL/database deployments, persistent volumes, backups, and PITR are all covered by the same Compute hard limit, or whether any continue accruing charges after shutdown.
- **UNVERIFIED:** whether volumes or backups are retained after a hard-limit shutdown, for how long, and whether they continue to incur charges.
- **UNVERIFIED:** whether the separate Compute and Agent limits cap the complete invoice, including any plan/subscription fees, taxes, or other line items. The official documentation explicitly describes separate Compute and Agent limits and does not establish a combined total-bill ceiling.
- **UNVERIFIED:** contractual Amsterdam data residency, including the locations of database copies, backups, logs, and subprocessors.
- **UNVERIFIED:** Railway's settings for any Devobs account. No Railway account or workspace was inspected.

## Proposed compensating controls — not configured

1. For a future, specifically authorized experiment, set the Compute hard limit to **USD 10**, the documented minimum. This is **USD 90 below** the owner's USD 100 monthly ceiling, leaving a 90% headroom in that budget, but it does not cover the separately metered Agent or prove a total invoice cap.
2. Set a custom email alert at **USD 5** (50% of the proposed Compute limit). Retain Railway's documented reminders at **USD 7.50 (75%)** and **USD 9 (90%)**. Treat every alert as an operator signal only.
3. Configure the Agent hard limit separately at the lowest value the eventual subscription plan accepts; record that value before any test. Do not use Railway Agent during the test or staging until the owner approves its use.
4. Do not use a managed database, persistent volume, backup, or PITR until Railway confirms in writing how each is charged and retained after a hard-limit shutdown. Keep all test data synthetic and ephemeral.
5. Do not create resources or spend money under this evidence packet. The prior USD 100 approval is conditional and does not approve the experiment's spend.

## Pre-registered compute enforcement test — NOT RUN

**Policy ID:** `p01-railway-hard-limit-enforcement-v1`  
**Registration baseline:** `origin/main` `f691baeceabdeecffcd1f6dd826c1972f284b4f3`; this design must be committed before any measurement.  
**Status:** Design frozen for review; **NOT RUN**; one-time owner authorization for test spending is still required.  
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

## Railway support request

Railway's official [Support documentation](https://docs.railway.com/platform/support) says support requests should be submitted through [Central Station](https://station.railway.com) and that Railway does not provide support by email. No request was sent: this workspace has no authenticated Railway support connection. Copy this text into Central Station from the owner's account:

> We plan to set a $100/month hard limit. Please confirm in writing: (1) the maximum delay or overshoot between reaching the limit and workloads being stopped; (2) whether managed databases, volumes, backups and network egress are all covered or continue to accrue charges after shutdown; (3) whether volume data and backups are retained after a hard-limit shutdown, and for how long.

## P01 budget-gate decision

**Current result: NO-GO / BLOCKED.** The documentation confirms a useful Compute hard-stop control, but it does not establish a complete USD 100 total monthly cap or answer the managed-database and post-shutdown storage questions.

The budget evidence path may close only by either:

1. an official written Railway response that resolves the open coverage, delay/overrun, and post-shutdown charge/retention questions for every resource in the approved P01 scope and confirms the resulting exposure can stay within the USD 100 ceiling; or
2. a successful run of this frozen test, after separate owner authorization, meeting every pre-registered criterion above.

The test intentionally excludes databases and persistent storage. Therefore, even a successful test closes only the tested Compute enforcement evidence; managed PostgreSQL, volumes, backups/PITR, and residency remain blocked until Railway confirms those items in writing or the P01 scope is changed and separately approved. A written response that reveals unbounded overrun or continued charges capable of breaching the USD 100 ceiling leaves P01 blocked. A written response or passing test is evidence for the budget sub-gate only; all P01 security, identity, residency, recovery, and owner-signoff gates still apply.
