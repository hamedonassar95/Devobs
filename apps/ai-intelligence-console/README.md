# DevOps AI Intelligence Console

This is the preserved React/TypeScript prototype from the former `DevObs-ai-Intelligence-` repository. It now lives inside the canonical Devobs repository at `apps/ai-intelligence-console/`. The source repository and its history remain available at GitHub; the imported source revision is recorded in `CONSOLIDATION.md`. The original MIT license is in this directory.

## Current status

- This is a prototype, not a production monitoring or deployment service. Dashboard server, incident, metric, and deployment records are synthetic examples in `src/data/mockServerData.ts`.
- The dashboard and its buttons do not control real servers, perform real deployments, or roll back production releases.
- GitHub workflows, issues, pull requests, and run history in the console are local sample/simulated UI; the app does not call GitHub's API to manage them.
- The static GitHub Pages site does not publish this app. The app's local Express server binds to `127.0.0.1` by default.
- Firebase, Google Workspace, and Gemini integrations are disabled by default. Do not put OAuth client secrets, access tokens, Firebase private credentials, or real customer/server data in this repository.
- Firestore rules deny all access. The prototype must not be connected to a customer or production database.
- Google Workspace code includes broad OAuth scopes and has not been approved for live use. Keep it disabled.
- Gemini models and responses shown without a key are prototype fallbacks, not verified model output.
- Gemini API calls can incur charges. Leave `GEMINI_API_KEY` blank unless a maintainer intentionally configures and reviews a separate test environment.

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
