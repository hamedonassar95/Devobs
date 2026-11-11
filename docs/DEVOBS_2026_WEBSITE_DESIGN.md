# Devobs 2026 public website redesign — review only

- Scope: `index.html` static marketing landing page, Arabic RTL, responsive CSS, accessible links and navigation.
- Source design reference: [Tabler](https://github.com/tabler/tabler) — free/open-source Bootstrap-based dashboard UI kit, MIT license, with dark mode and RTL support. Reviewed 2026-11-03.
- Design treatment: **Original, dependency-free HTML/CSS** inspired by dashboard layouts and token-driven dark colors. This change does **not** vendor Tabler source, fonts, icons, Bootstrap, charts, commercial assets, or CDN dependencies. No license notice is required for the independently authored layout; if Tabler code/assets are copied later, retain relevant MIT license attribution.
- Why dependency-free: existing `tests/test_check_site.py` forbids `<script>`, `<link>`, and `<img>` on the public landing page, and `scripts/stage_site.py` stages a static `index.html`.
- Contents: hero, simulated control-room visualization explicitly labeled `DESIGN PREVIEW` (not telemetry), original services and contact areas, capability explanation and Android/Windows download placeholders.

## Native release availability — verified scope
- GitHub `v1.0.0` Release inspected via connected GitHub API on 2026-11-03: **zero attached assets**.
- No Devobs repository APK, EXE, MSI or MSIX approved public release was verified.
- Therefore **no binary links are enabled**. Windows and Android cards explicitly say that no signed, validated installer is available.
- The GitHub Releases link navigates to the release index, not to an installer.
- Do not substitute the separate `phone-repair-assistant-v2` mobile/desktop source or packages as Devobs binaries.

## Release requirements (separate work, not authorized in this change)
1. Identify the product use case and dedicated Windows/Android client codebases.
2. Build on an approved reproducible runner; verify install on authorized test devices; sign for distribution.
3. Publish a versioned immutable binary, SHA-256, source commit and release notes.
4. Independently verify the download URL, checksum and signature before editing the public site to link it.
5. Review privacy, authentication, licensing, CI, release approvals, and cost constraints.
6. Owner approves deployment and user-facing distribution separately.

## Verification
- Run `python3 scripts/check_site.py`.
- Run `python3 -m unittest tests.test_check_site tests.test_2026_download_center -v` (or equivalent discovery command).
- Run ordinary repository CI (Python/Node, code/security and Pages staging).
- Check the layout visually at desktop and narrow mobile sizes, keyboard access, and Arabic RTL.

**NO production authorization:** This branch does not enable API, AI inference, hosted SaaS, billable providers, cross-repo downloads, secrets, new CI workflows, or production deployment. Preserve human review of the exact commit.
