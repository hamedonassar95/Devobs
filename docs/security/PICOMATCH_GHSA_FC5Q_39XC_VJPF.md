# picomatch `GHSA-fc5q-39xc-vjpf` (CVE-2026-112366) — withdrawn advisory record

**Status: `WITHDRAWN — NO CODE CHANGE REQUIRED`.**

**Classification: documentation and evidence only.** This record does not change `package.json`, any lockfile, CI security gates, application source, runtime behaviour, or any release gate. It does not claim that the affected code was fixed.

| Field | Value |
|---|---|
| Repository | `hamedonassar95/Devobs` |
| Verified source SHA | `a2950911a8589fd82702f8d4e1ea314c226b7a6c` (`main`, "feat(ops): add fail-closed Windows Plannotator local preflight (#703)") |
| Record date | 2026-11-18 |
| Affected application | `apps/ai-intelligence-console` |
| Advisory | [GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf) / [CVE-2026-112366](https://nvd.nist.gov/vuln/detail/CVE-2026-112366) |
| Recorded status | Withdrawn upstream 2026-11-18T15:38:56Z |
| Local gate result | `npm audit --audit-level=high` → `found 0 vulnerabilities`, exit `0` |

## Scope and non-goals

In scope: recording the advisory's authoritative lifecycle, the exact dependency chain that introduced `picomatch`, a labelled reachability analysis, and the evidence that the local audit gate is currently green.

Out of scope and **not performed**: dependency or lockfile changes, `overrides` additions, CI/workflow edits, audit suppression, production deployment, P01/AI-9/Codex runtime gate changes, GitLab synchronisation, secret access, and any paid service.

## Verified environment

- Windows, repository root `C:\DevProjects\Devobs`.
- Python `3.12.10` (used for the milestone ledger check).
- Node.js `v26.13.1`; npm `11.20.0`.
- `npm` is invoked as `npm.cmd` on this machine because the PowerShell execution policy blocks `npm.ps1`.

## Verification record

All commands were run from the repository root unless a working directory is stated. Outputs below are verbatim final lines.

### 1. Dependency audit gate

```console
$ cd apps/ai-intelligence-console
$ npm.cmd audit --audit-level=high
found 0 vulnerabilities
EXIT=0
```

- **Timestamp (UTC):** `2026-11-18T20:39:02Z`
- This is the same command CI runs ([`.github/workflows/ci.yml` lines 258–261](../../.github/workflows/ci.yml)). It was **not** suppressed, filtered, retried with a weaker level, or replaced.
- **VERIFIED:** at the recorded timestamp the audit reports zero vulnerabilities for the committed lockfile. This is an observation of a point in time, not a permanent guarantee.

### 2. Milestone ledger integrity

```console
$ python scripts/milestone_ledger.py --summary
{"gate_statuses": {"ai9-detection-quality": "BLOCKED", "codex-agent-runtime-acceptance": "OPEN",
"p01-managed-saas": "BLOCKED"}, "latest_pr": 701, "merged_milestones": 291,
"open_gates": 3, "repository": "hamedonassar95/Devobs"}
EXIT=0
```

- **VERIFIED:** the ledger validates and remains at 291 merged milestones with 3 open gates. This change does not add or promote a milestone.

### 3. Checks deliberately skipped

- `npm test`, `npm run lint`, and `npm run build` in `apps/ai-intelligence-console` were **NOT RUN** locally: `node_modules` is not installed, and installing it (`npm ci`) was explicitly excluded from this task. They are not reported as passing.
- CI still runs them for console changes because [`.github/workflows/ci.yml` lines 262–268](../../.github/workflows/ci.yml) select the full console job whenever any path under `apps/ai-intelligence-console/` changes — including the README edited here. Their result must be read from the actual CI run.

## Advisory record

| Attribute | Value | Label |
|---|---|---|
| Summary (current) | "Withdrawn Advisory: picomatch vulnerable to ReDoS through single-branch repeated extglobs" | VERIFIED |
| Published | 2026-10-19T18:32:12Z | VERIFIED |
| GitHub-reviewed | 2026-11-17T15:56:42Z | VERIFIED |
| **Withdrawn** | **2026-11-18T15:38:56Z** | VERIFIED |
| Last updated | 2026-11-18T15:38:58Z | VERIFIED |
| Severity while active | High — CVSS v4 `8.7`, CVSS v3.1 `7.5` | VERIFIED |
| Weakness | CWE-1333 (Inefficient Regular Expression Complexity) | VERIFIED |
| EPSS | 0.335% (27th percentile) | VERIFIED |
| Vulnerable range | `<= 4.0.7` | VERIFIED |
| `first_patched_version` | `null` (none published) | VERIFIED |
| Impact vector | Availability only: `VC:N/VI:N/VA:H` | VERIFIED |
| Original claim | `analyzeRepeatedExtglob` in `lib/parse.js` skips single-branch repeated extglobs such as `+(*)` or `+(*a)`, allowing exponential backtracking that blocks the Node.js event loop | VERIFIED (as the published claim; not independently reproduced here) |

### Withdrawal basis

The advisory directs readers to [micromatch/picomatch#235, comment 6315749381](https://github.com/micromatch/picomatch/pull/235#issuecomment-6315749381). The maintainer (`jonschlinkert`, member, 2026-10-21T12:20:20Z) states:

> "I might disable PRs permanently due to the volume of AI generated fake vulnerabilities. How many times do I have to explain that globs are regular expressions. The general star height problem, which has not been solved, describes why we cannot predict all patterns like this. It's not a vulnerability, it's nonsense."
>
> Recommendation: "1. Don't use that pattern. 2. Don't let untrusted users define regular expressions"

**UNVERIFIED:** the precise internal GitHub rationale for withdrawal is not published beyond this linked comment. The authoritative fact is the advisory's own `withdrawn_at` field, not the maintainer's opinion.

### Sibling advisories (still active — checked in the same query)

| Advisory | Severity | Affected range | First patched | Applies to `4.0.7`? |
|---|---|---|---|---|
| [GHSA-c2c7-rcm5-vvqj](https://github.com/advisories/GHSA-c2c7-rcm5-vvqj) / CVE-2026-33671 — ReDoS via extglob quantifiers | High | `>=4.0.0, <4.0.4` | `4.0.4` | **No** |
| [GHSA-3v7f-55p6-f55p](https://github.com/advisories/GHSA-3v7f-55p6-f55p) / CVE-2026-33672 — POSIX character-class method injection | Medium | `>=4.0.0, <4.0.4` | `4.0.4` | **No** |

**VERIFIED:** both active advisories are fixed in `4.0.4`, and this repository resolves `picomatch@4.0.7`. **VERIFIED:** the npm registry `dist-tags.latest` for `picomatch` is `4.0.7`, so no newer release exists to upgrade to.

This matters for one specific reason: **downgrading or pinning `picomatch` below `4.0.4` to "respond" to this withdrawn advisory would introduce two live vulnerabilities.** Inaction is the correct outcome here.

## Dependency chain

Derived from `apps/ai-intelligence-console/package-lock.json` (`lockfileVersion` 3, 385 packages). **VERIFIED** by parsing the lockfile; the lockfile was not modified.

```
<root> devobs-ai-intelligence-console
  └─ vite@8.3.8                        declared in "dependencies" (package.json line 29) — not devDependencies
       ├─ optionalDependencies: picomatch ^4.0.7 ─┐
       └─ dependencies: tinyglobby ^0.2.17        │
            └─ tinyglobby@0.2.17                  │
                 ├─ dependencies: fdir ^6.5.0     │
                 │    └─ fdir@6.5.0               │
                 │         └─ optionalDependencies: picomatch ^3 || ^4 ─┤
                 └─ optionalDependencies: picomatch ^4.0.4 ────────────┘
                                                                        ▼
                                        node_modules/picomatch@4.0.7  (single hoisted instance)
```

- resolved: `https://registry.npmjs.org/picomatch/-/picomatch-4.0.7.tgz`
- integrity: `sha512-qcJu88Q2IWqJsDD529JKMdwGm/dvInW4HvQnRwiH9JtihJvzGOscDtHE3x1pBKeUOTysQ8kVmLnJ2kJu7yhcGA==`
- license: MIT; `engines.node >= 12`
- **VERIFIED:** exactly one `picomatch` entry exists in the tree; there is no nested duplicate under `fdir` or `tinyglobby`.
- **VERIFIED:** `vite` is declared in `dependencies`, not `devDependencies`, which is why the audit gate covers it.

## Reachability analysis

| Question | Finding | Label |
|---|---|---|
| Is `picomatch` reachable in a production start? | `server.ts` line 2 is a **top-level static ESM import**: `import { createServer as createViteServer } from 'vite'`. Vite's module graph is therefore evaluated in every mode, including `NODE_ENV=production`. | VERIFIED (source read) |
| Is Vite *used* in production? | **No.** `server.ts` lines 970–983: when `NODE_ENV === 'production'` the server mounts `express.static(dist)` plus an SPA fallback and never calls `createViteServer`. | VERIFIED (source read) |
| Is the vulnerable pattern path reachable? | `picomatch` compiles glob patterns. In Vite/`tinyglobby` usage those are developer- or build-controlled include/exclude patterns, not HTTP request input. No sink was found that forwards a user-supplied glob to `picomatch`. | ASSUMED — based on a targeted search, not an exhaustive data-flow trace |
| Is it exploitable in this application? | Exploitation requires an attacker to supply a crafted glob pattern. No such input surface was identified; impact while active was availability-only. | UNVERIFIED — no runtime instrumentation or reproduction was performed |

**ASSUMED:** the console's production deployment path serves only pre-built static assets and static API routes, so `picomatch` executes (if at all) at module-load time rather than per request. Not proven by tracing.

## Why withdrawal is not a source-code fix

The advisory outcome changed; the code did not.

- No `picomatch` code was patched, vendored, shimmed, or overridden in this repository.
- No dependency version changed — the tree still resolves `picomatch@4.0.7`, unchanged since before this record.
- The audit is green because the advisory database stopped publishing `GHSA-fc5q-39xc-vjpf` as an active vulnerability, not because `analyzeRepeatedExtglob` changed.
- If the advisory is reinstated, or a new advisory is published against `4.0.7`, the gate would go red again with **no source change in this repository**.

This distinction is the whole point of the record: a withdrawn report must not be cited later as evidence that a defect was fixed.

## Rejected remediation options

| Option | Rejected because |
|---|---|
| `npm audit fix` | No-op; there is no fix to apply, and no version exists above `4.0.7`. |
| `npm audit fix --force` | Prohibited by `AGENTS.md` and this task. Would force incompatible downgrades; could drop `picomatch` below `4.0.4` and introduce CVE-2026-33671 / CVE-2026-33672. |
| Pin or downgrade `picomatch` via `overrides` | Would actively create two live vulnerabilities; `4.0.7` is already above every patched threshold. |
| Add an `npm audit` suppression, ignore list, or `--omit` flag | Prohibited. It would weaken a shared security gate to hide an advisory that is already withdrawn — pure downside. |
| Remove or relax the CI audit step | Prohibited; existing CI security checks are preserved unchanged. |
| Replace Vite, `tinyglobby`, or `fdir` | Disproportionate; the dependency is not vulnerable. |

## Evidence required to reopen this record

Reopen only if at least one of the following is observed, each with a fresh, cited source:

1. `GHSA-fc5q-39xc-vjpf` is reinstated (no longer carries `withdrawn_at`).
2. Any advisory is published affecting `picomatch@4.0.7` with a `first_patched_version` greater than `4.0.7`.
3. GitHub Dependabot raises a `picomatch` alert for this repository.
4. `npm audit --audit-level=high` in `apps/ai-intelligence-console` returns a non-zero exit.

A reinstatement would be a **security-gate change**, requiring its own reviewed branch, exact pinned versions, and a fresh CI run — never a silent `overrides` edit.

## Gate status (unchanged)

| Gate | Status | Changed by this record? |
|---|---|---|
| `p01-managed-saas` | BLOCKED / NO-GO | No |
| `ai9-detection-quality` | BLOCKED | No |
| `codex-agent-runtime-acceptance` | OPEN | No |

A withdrawn transitive-advisory report is not P01 hosted readiness, AI-9 evaluation evidence, or Codex runtime acceptance, and it does not authorise paid activation, deployment, or GitLab synchronisation.

## Sources

- GitHub Advisory (withdrawn): <https://github.com/advisories/GHSA-fc5q-39xc-vjpf>
- GitHub Advisory API record: <https://api.github.com/advisories/GHSA-fc5q-39xc-vjpf>
- npm registry metadata for `picomatch` (`dist-tags.latest = 4.0.7`): <https://registry.npmjs.org/picomatch>
- Withdrawal reference — maintainer comment: <https://github.com/micromatch/picomatch/pull/235#issuecomment-6315749381>
- CVE record: <https://nvd.nist.gov/vuln/detail/CVE-2026-112366>
- Vendor analysis: <https://www.vulncheck.com/advisories/picomatch-through-4.0.7-redos-via-single-branch-repeated-extglob-patterns>
- Active sibling advisories: <https://github.com/advisories/GHSA-c2c7-rcm5-vvqj>, <https://github.com/advisories/GHSA-3v7f-55p6-f55p>
- npm audit documentation: <https://docs.npmjs.com/cli/commands/npm-audit>
- CI gate: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) lines 258–268
- Dependency manifest: [`package.json`](../../apps/ai-intelligence-console/package.json) line 29
- Server entry point: [`server.ts`](../../apps/ai-intelligence-console/server.ts) lines 2, 970–983
