# AI Intelligence consolidation record

The prototype was imported from `hamedonassar95/DevObs-ai-Intelligence-` into the canonical `hamedonassar95/Devobs` repository at `apps/ai-intelligence-console/`.

- Source main at import: `61e4297545c60ebcda77a4c1a1f793c7e9a20347`.
- Devobs base used for the import: `ef417487da1ad25e9d74e571102e7d5da3c96295`.
- The merge keeps the source repository as a second Git parent, preserving its commit history. The source repository itself is not modified or deleted.
- The complete app source, its npm lockfile and tests, and its MIT license are preserved under this directory.

## Preserved areas

- Server, incident, deployment, and metrics dashboard UI.
- GitHub CI/CD console UI and incident/reporting flows.
- Gemini assistant and media studio UI/server routes.
- Google Drive, Gmail, Docs, Sheets, Slides, Calendar, Chat, Tasks, Keep, and Forms UI/service code.
- Three.js server-room visualization, cyber-defense game, mock data, and app tests.

Preserving the code does not mean the integrations are live or production-ready. See the app README for exact limits and safe local operation.

## Deliberately inactive in the monorepo

The old nested CI, deploy-placeholder, and repository-dispatch workflow files were removed from the working tree. GitHub Actions only discovers workflows under the root `.github/workflows/`; the nested files were never active there. The deploy workflow only printed messages, while cross-repository dispatch was for coordinating two repositories. Devobs is now the single repository, so the root pinned CI runs the app checks when this directory changes. The dispatcher source and its tests remain for review, but no credential or dispatch action is wired into the monorepo.

The old bundled Firebase client configuration was removed. Firebase setup is disabled by default, automatic writes of mock seed data were removed, and Firestore rules now deny all access. Broad Google OAuth scopes and Gemini requests also remain disabled by default. No customer account, real infrastructure, cloud project, model endpoint, or production service was connected during import.
