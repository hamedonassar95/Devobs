# KI-0 knowledge-source threat model

**Scope:** the local source-policy schema, Python validator, and synthetic
fixtures only. This is not a threat model for a deployed retrieval service,
database, or model runtime.

## Assets and trust boundaries

| Asset | Trust boundary |
| --- | --- |
| Source policy metadata | Untrusted local input; bounded JSON only. |
| Declared tenant, repository, owner and approval | Claims only; no identity or ownership verification occurs. |
| `source_uri` and `content_sha256` | Metadata only; URI is never fetched and digest is not compared with content. |
| Checked-in JSON Schema | Version-controlled contract; validator checks its expected fields/enums before accepting input. |
| Future source content | Untrusted data, even if public or approved; never executable policy or tool authority. |
| Future authorization service | Not implemented; must verify identity, scope, rights, approval, expiry and revocation independently. |

## Threats and controls

| Threat | KI-0 control | Residual risk / next requirement |
| --- | --- | --- |
| Missing or misspelled policy fields silently broaden access | Exact required/allowed field set; reject unknowns. | Schema changes need review and versioning. |
| Duplicate JSON keys change parser interpretation | Duplicate-key rejection in the standard-library parser. | All future consumers must use equivalent strict parsing. |
| Oversized or malformed inputs exhaust or confuse validation | 16 KiB input/schema limits; UTF-8, malformed JSON and recursion fail closed. | This is not a sandbox for parsing actual documents. |
| URI causes SSRF or content is executed | No network access, URI resolution, shell, or source execution. | Future ingestion requires isolated parser, URI allowlist and SSRF controls. |
| Forged `APPROVED` or tenant/owner ID | Output is explicitly `STRUCTURE_ONLY`; no authority decision is claimed. | Trusted identity and signed/action-bound approval are prerequisites for KI-1. |
| Cross-tenant data exposure | Tenant and repository scopes are mandatory in policy. | No runtime data store exists here; synthetic validation does not prove isolation. Require independent auth and storage tests. |
| Prompt injection in retrieved content | Privacy contract states content is untrusted and cannot grant policy or tool authority. | No retriever exists; add adversarial fixtures and renderer/tool-boundary tests before retrieval. |
| Copyright or license misuse | Explicit license status and source-type combinations; unknown status rejected. | A declaration cannot prove rights; a human must review source license and purpose. |
| Data persists after consent expires | Required retention and deletion declarations with bounded combinations. | No deletion engine, index, cache, backup, or timer exists. Verify lifecycle end to end before real data. |
| Sensitive source text appears in errors | Fixed error codes; no echo of source values. | Future logs and consumers need separate privacy review. |
| `RESTRICTED` is accidentally admitted | Recognized but rejected as unsupported in v1. | Do not add restricted-source support without a new reviewed schema version. |

## Trust and failure rules

- Unknown, missing, conflicting, malformed, or unsupported states deny.
- A file field, provenance string, source digest, or local test result is not an
  authenticated approval.
- Retrieved content cannot override system policies, tenant boundaries, human
  approval, or agent tool permissions.
- Do not enable real ingestion until identity, source rights, isolation,
  retention, deletion, audit, prompt-injection, and rollback controls are
  implemented and independently reviewed.

## Reused repository controls

Devobs already has useful source-level patterns in the offline tenant gate,
read/propose/deny action policy, approval state machine, bounded event parser,
and PostgreSQL RLS SQL. The trust caveats are documented in
[the source register](SOURCE_REGISTER.md) and the previous
[architecture audit](README.md). These existing patterns do not prove live
identity, applied RLS, or production readiness for knowledge data.
