# DevOps AI Intelligence Console

This is the preserved React/TypeScript prototype from the former `DevObs-ai-Intelligence-` repository. It now lives inside the canonical Devobs repository at `apps/ai-intelligence-console/`. The source repository and its history remain available at GitHub; the imported source revision is recorded in `CONSOLIDATION.md`. The original MIT license is in this directory.

## Current status

- This is a prototype, not a production monitoring or deployment service. Dashboard server, incident, metric, and deployment records are synthetic examples in `src/data/mockServerData.ts`.
- The dashboard and its buttons do not control real servers, perform real deployments, or roll back production releases.
- GitHub workflows, issues, pull requests, and run history in the console are local sample/simulated UI; the app does not call GitHub's API to manage them.
- The static GitHub Pages site does not publish this app. The app's local Express server binds to `127.0.0.1` by default.
- Firebase and Google Workspace integrations are disabled by default. Public Gemini prototype routes are closed with a fixed 503 response even if a key is present. Do not put OAuth client secrets, access tokens, Firebase private credentials, or real customer/server data in this repository.
- Firestore rules deny all access. The prototype must not be connected to a customer or production database.
- Google Workspace code includes broad OAuth scopes and has not been approved for live use. Keep it disabled.
- Incident diagnosis uses the optional protected Devobs proxy described in [the integration guide](docs/DEVOBS_DIAGNOSTICS_INTEGRATION.md). It is disabled by default and requires an explicit reviewed request; missing configuration never fabricates a diagnosis. Other AI/media and GitHub text-generation routes are closed before body parsing, so they return neither paid results nor fabricated local successes.
- Optional [Devobs read-only sign-in](docs/DEVOBS_OIDC_LOGIN.md) uses the official Keycloak adapter with PKCE S256. It is disabled by default, independent of Google/Firebase, and does not grant diagnosis or change the dashboard's sample data.
- `GEMINI_API_KEY` does not activate the closed prototype routes. The server constructs no Gemini client; legacy handlers remain reference code behind the closed route guard. Re-enabling inference requires reviewed identity, tenant authorization, data policy and cost controls, not a key or budget boolean alone.
- No live Gemini request is part of CI or this prototype's release checks. The new real-server tests explicitly forbid provider network traffic.

## Withdrawn dependency advisory (picomatch)

The `picomatch` ReDoS report `GHSA-fc5q-39xc-vjpf` / `CVE-2026-112366` was **withdrawn upstream on 2026-11-18T15:38:56Z**; it was published 2026-10-19 and affected `<= 4.0.7` with no patched version. Our tree resolves `picomatch@4.0.7` once, through `vite@8.3.8` and `vite → tinyglobby → fdir`.

At `2026-11-18T20:39:02Z` the gate command in this directory returned `found 0 vulnerabilities` with exit code `0`. **No dependency, lockfile, CI gate, or source file was changed to achieve that** — the advisory database simply stopped publishing the report. Withdrawal is not a source-code fix, and this note must not be cited as evidence that a defect was repaired.

Two sibling advisories remain active and are fixed in `4.0.4` (`CVE-2026-33671`, `CVE-2026-33672`). Because this app already resolves `4.0.7`, it is outside both ranges — do **not** downgrade, pin below `4.0.4`, add an `overrides` entry, suppress the audit, or run `npm audit fix --force`; each would create or conceal a real vulnerability.

Full evidence, reachability analysis, and reopen conditions: [`docs/security/PICOMATCH_GHSA_FC5Q_39XC_VJPF.md`](../../docs/security/PICOMATCH_GHSA_FC5Q_39XC_VJPF.md). This does not change the P01 **NO-GO**, AI-9 **BLOCKED**, or Codex runtime **OPEN** gates.

On this Windows machine the audit must be run as `npm.cmd` — PowerShell's execution policy blocks `npm.ps1`.

## Advisory-only controls (demo safety)

The **Restart**, **Redeploy**, and **Rollback** controls are now explicit **preview-only** actions. Clicking them displays a non-executing demo message: it does **not** mark a server healthy, change deployment status, fabricate a successful restart/rollback incident, call a cloud API, or trigger a CI deployment. The console shows an always-visible Arabic `DEMO ONLY` banner on every tab, not just Overview.

The separate server and incident editing forms remain **local prototype records** (or optional disabled-by-default Firebase data functions), not infrastructure commands. Their confirmation toasts say so; adding a deployment record is not an actual deploy. No new authorization, provider or inference capability was added. The existing protected, manual diagnostics proxy remains separate and disabled unless independently configured; this change neither enables nor invokes it.

Run the focused no-network regression check with the existing console tooling:

```sh
node --import tsx --test tests/demoActionPreview.test.mjs
npm test
npm run lint
npm run build
```

The focused test exercises all three immutable preview outcomes; it does not constitute browser E2E, a real-server action test, or P01 hosted acceptance. Do not represent the mock records as measured production telemetry. A future real-operation controller must be separately designed with scoped identity, independent authorization, auditable human confirmation, and the still-blocked production gates.

## AI-7 local snapshot integration (optional, read-only)

The **Overview → AI-7** panel can retrieve **real computed aggregates** from the existing [Devobs AI-7 engine](../../docs/AI_LOCAL_DASHBOARD.md) running on the same computer. This is not live production monitoring: AI-7 analyzes a **local event-store snapshot** and its recommendations remain advisory, uncalibrated and human-reviewed.

**Explicit local activation (two terminals, synthetic data only):**

Terminal 1, from the repository root, prepare an existing **synthetic** JSONL event store using the documented AI-1 ingestion workflow and start the existing AI-7 server:

```sh
node scripts/ai_intelligence/dashboard_server.mjs --store /path/to/synthetic-events.jsonl --port 8765
```

Terminal 2, from `apps/ai-intelligence-console`:

```sh
DEVOBS_AI7_LOCAL_READONLY_ENABLED=true npm run dev
```

Open `http://127.0.0.1:3000` on the **same machine**, navigate to Overview and press **قراءة المحرك المحلي**. This manually requests `GET /api/local-ai7/summary` from the console server, which reads only the fixed `http://127.0.0.1:8765/api/v1/intelligence` endpoint and returns a strict allowlist of summary counters and seven stage statuses. The bridge cannot accept an alternate address, does not expose raw incidents, recommendation texts or events, does not poll automatically, and does not send credentials or trigger any write operation.

**AI-4 recommendation review:** The same manually refreshed snapshot now includes **up to five** evidence-bound, non-executing recommendation cards from the existing AI-4 engine. Each card shows its fixed known runbook cause, `POSSIBLE` classification, uncalibrated `low` or `medium` heuristic signal, source-approved evidence markers, a fixed read-only check and an explicit **human review required** notice. Only known cause and marker values are accepted; upstream free-form titles, raw logs, paths, secrets and instructions are never forwarded to React. Invalid, inconsistent or automatically executable recommendation metadata fails the whole response closed rather than silently approving it.

An optional **I have read this** checkbox records only temporary in-page acknowledgement. It does **not** persist an approval, create a ticket, issue an API call, grant credentials, change a service, authorize production or replace a scoped human change approval. The checkboxes reset on every manual refresh. The full AI-7 recommendation count can exceed the five displayed cards; the UI explicitly shows both counts.

The server endpoint is **disabled by default**. It refuses public/non-loopback binds and unexpected Host/Origin headers, rejects redirects and malformed/oversized JSON, imposes a short timeout, and returns a fixed failure message instead of invented results when unavailable. Do **not** expose either local server via a tunnel, proxy, external hostname, hosting platform or a shared-network interface. There is no hosted identity or tenant authorization in this local integration. Changing `HOST` away from `127.0.0.1` disables the bridge even with the flag enabled.

Focused verification:

```sh
npm test
npm run lint
npm run build
```

`tests/localAi7Bridge.test.mjs` includes an integration check against the actual existing AI-7 `buildDashboardSnapshot` contract and negative cases for a disabled bridge, foreign origins/hosts, malformed data, redirects and oversized responses. It uses an in-process fake fetch rather than connecting to any external service. The controls in [P01](../../docs/P01_ACTIVATION_READINESS.md) remain **NO-GO** and no AI-9 acceptance or commercial service is claimed.

## Run the local prototype

Requirements: Node.js 24 (recommended) or 22.12+ and npm.

From the Devobs repository root:

```sh
cd apps/ai-intelligence-console
npm ci
npm run dev
```

Open <http://127.0.0.1:3000>. The app starts without external credentials and uses synthetic/local data. To stop it, press `Ctrl+C`.

Checks:

```sh
npm test
npm audit --audit-level=high
npm run lint
npm run build
```

## Repository workflow

Make changes in this directory while working from the Devobs monorepo. Use the repository's existing branch and Pull Request process; do not run `git init`, replace the `origin` remote, or push this subdirectory as a separate repository. The former standalone workflows and cross-repository dispatch are not active in this monorepo. The root Devobs CI runs this app's checks when files under this directory change.

The UI and service code is retained for future development. Keep external integrations and deployment credentials out of CI until they have a reviewed, least-privilege design and a dedicated non-production environment.
