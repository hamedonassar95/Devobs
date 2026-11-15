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
