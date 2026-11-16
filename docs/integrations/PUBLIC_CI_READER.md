# A useful free API: public Devobs CI evidence

**VERIFIED implementation and local browser read; not production acceptance.**
The optional [public CI page](https://hamedonassar95.github.io/Devobs/assets/public-ci/)
reads real public GitHub metadata only when its button is activated. It adds no
backend, account, API key, paid inference, dependency or recurring task.
The existing synthetic free preview keeps its self-only CSP and makes no API call.

## Applying the video idea responsibly — 2026-11-16

The supplied [Short](https://www.youtube.com/shorts/dTYl4wE6C2U),
«بطل تدور على API لمشروعك! (كنز مجاني على GitHub)», suggests using a Public APIs
catalogue to discover APIs, then reading the selected API documentation.
Its captioned text was available through a public web reader; no paid video
analysis, credits, account registration or upstream code installation was used.

The reviewed [public-apis/public-apis catalogue](https://github.com/public-apis/public-apis)
has an [MIT licence](https://github.com/public-apis/public-apis/blob/master/LICENSE)
for the catalogue, not every service it lists. Entries can require keys, OAuth,
subscriptions or quota review. Its GitHub row lists OAuth, but the official docs
explicitly allow the particular public reads selected here without authentication.
The catalogue is discovery evidence; individual official API terms take precedence.

## Exact public scope

One activation performs exactly two fixed GETs:

```text
https://api.github.com/repos/hamedonassar95/Devobs/branches/main
https://api.github.com/repos/hamedonassar95/Devobs/actions/workflows/ci.yml/runs?branch=main&event=push&per_page=1
```

See the official [branch endpoint](https://docs.github.com/en/rest/branches/branches#get-a-branch)
and [workflow endpoint](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow).
The latter permits the filename `ci.yml` and public unauthenticated access.
The client pins supported [API version](https://docs.github.com/en/rest/about-the-rest-api/api-versions)
`2022-11-28`. [CORS](https://docs.github.com/en/rest/using-the-rest-api/using-cors-and-jsonp-to-make-cross-origin-requests)
allows the browser read; the version header can cause an OPTIONS preflight.
Observed headers and a real local Chromium request confirmed access.

GitHub documents [60 anonymous requests/hour per originating IP](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api),
possibly shared by multiple people. Higher quotas seen in an execution environment
are not an entitlement for visitor browsers. There is no polling, retry, token
fallback, proxy, JSONP or arbitrary URL/project input. Rate limits and unavailable
responses are shown honestly; they never preserve an old green result.

## Evidence and privacy boundaries

Both responses must validate before display: repository/head-repository must be
the fixed public Devobs repository, workflow ID/path must match, branch/event must
be main/push, and IDs, SHA and timestamps must be valid. Unknown or contradictory
status/conclusion values fail closed. Run links are constructed from the fixed
GitHub origin and numeric run ID; upstream links, names and messages are ignored.

Only completed/success means successful CI. An unmatched main/run SHA is stale,
not successful current evidence. A match describes the two retrieved responses
at that time; caching or later pushes can change the state. Neither observation
proves deployment, live application health, hosted identity, tenant isolation,
spending enforcement or AI-9 quality. Existing Python backend collectors remain
separate; a downloaded public observation is not imported or release-approved.

Requests use credentials omitted, no referrer, redirects rejected, bounded UTF-8
JSON streams (64 KiB each) and one overall five-second deadline. The page's CSP
permits only the fixed GitHub API origin for connections. Nothing is fetched
before activation; notes, local storage and private project data are never read.
Old evidence is cleared immediately on refresh and on error. There is no account,
token field, write API, automatic remediation or production action.

## Local CloudEvents handoff

After a successful read, a separate button can download one JSONL CloudEvent.
It requires a completed run matching the retrieved main SHA, a supported
conclusion and a positive `run_attempt`. Missing attempt metadata keeps display
available but disables export; it never defaults to attempt 1. Refresh, stale or
running results and request failures clear the previous downloadable event.
`stale` and `startup_failure` conclusions have no existing AI-1 mapping and cannot
export. Supported non-success outcomes retain their exact conclusion.

The event uses wire `specversion: "1.0"`, existing type `devobs.ci.result.v1`,
the fixed public Devobs source and workflow label `CI`. Both its ID and generated
`job` label carry run ID/attempt. The label `workflow-summary-run-…-attempt-…`
means a workflow summary, not an actual fetched job; no job API is called.
This matters because the existing converter drops CloudEvents ID before AI-1
content hashing. Distinct attempts remain distinct even when time/SHA/result
match, and repeated exports of the same terminal observation are idempotent.

GitHub does not supply a workflow-level completion timestamp. The event `time`
uses canonical UTC **run creation time as a consistent occurrence-time proxy**,
not completion or browser observation time. Metadata `updated_at` changes do not
change the export. See official [rerun identity variables](https://docs.github.com/en/actions/reference/variables-reference),
[workflow-run schema](https://github.com/github/rest-api-description/blob/main/descriptions/api.github.com/api.github.com.json),
CloudEvents [identity](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md#id)
and [time substitution](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md#time).
CloudEvents source/ID are self-declared claims, not authenticated webhook provenance.

The local [Blob URL](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static)
and [download](https://developer.mozilla.org/en-US/docs/Web/API/HTMLAnchorElement/download)
save a fixed-name file without another network call, browser storage or upload.
The URL is released after download activation. Only fixed labels, public run/attempt,
SHA, conclusion and creation time are included; upstream titles/URLs/bodies are omitted.
Review the file before optional local conversion. Replace the input placeholder
with your downloaded path; keep generated data outside Git:

```sh
export DEVOBS_CI_EXPORT_DIR="$(mktemp -d)"
node scripts/integrations/cloudevents_ci_adapter.mjs --input /path/to/devobs-public-ci.cloudevents.jsonl > "$DEVOBS_CI_EXPORT_DIR/ai1.jsonl"
node scripts/ai_intelligence/event_ingest.mjs --input "$DEVOBS_CI_EXPORT_DIR/ai1.jsonl" --store "$DEVOBS_CI_EXPORT_DIR/events.jsonl"
```

Repeat the final command to observe zero additional accepted events. The existing
[ingestion contract](../AI_EVENT_INGESTION.md) and [local dashboard](../AI_LOCAL_DASHBOARD.md)
remain unchanged. The store is local and not encrypted; retain/delete it under
your local policy. This handoff is scoped to public CI metadata, not private logs,
hosted tenancy, automatic ingestion or any new webhook receiver.

## Verification and rollback

```sh
node --test tests/public_ci_api.test.mjs tests/public_ci_export.test.mjs
python3 -m unittest discover -s tests -p test_public_ci_site.py -q
python3 scripts/check_site.py
```

When Python Playwright and Chromium are available, stage the reviewed site and
run `python3 tests/browser/public_ci_bootstrap.py`. This optional browser
regression deliberately holds the client module: activation stays disabled until
the click handler is bound, then the first click reads exactly the two controlled
fixtures. No live API call is made. It reproduced the initial fast-activation
race and passed after the readiness fix; it adds no runtime/CI dependency.
It also verifies the downloaded bytes, no extra reads, clearing on ineligible
results, and the original reader with older HTML lacking optional export controls.

Tests cover bindings, stale/missing/running/error states, fixed requests, rate
limits, redirects, invalid MIME/UTF-8/JSON, size limits and request/body deadlines.
Browser checks cover zero initial API calls, double-click concurrency, success,
stale data, failure clearing and mobile/desktop layout. Trusted site validation
requires the three static files and shared CSS whenever the directory exists or
the page is advertised; older candidates without it remain valid. Node CI also
runs for public-page-only edits. Docker uses the exact public file allowlist.

Rollback is a code revert; no cloud resource rollback is required. P01 remains
**BLOCKED/NO-GO**, AI-9 **BLOCKED**, Codex runtime **OPEN**.
