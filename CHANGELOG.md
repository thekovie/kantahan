# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- M3 automatic updates: `kantahan-catalog publish`, `run` (cron entry point with a 14 day interval and a run lock), `audit`, `rollback`, `suspend`/`resume` and `withdraw`; versioned bundles plus a manifest with SHA-256 per model, safety gates, atomic swap (migration 0004, `catalog/display.yaml`). The app checks for a newer catalog on open and on demand, verifies every download, swaps it in one transaction, keeps the old catalog on any failure, and shows a notice when the catalog is paused. Documented in `docs/catalog-updates.md` and `docs/security.md`.
- Repository bootstrap: README, license, agent instructions, documentation skeleton.
- M0 source audit documents (see `docs/source-audit.md`).
- Logo, favicon, PWA and social images (`apps/web/public/brand/`) and design notes.
- M2 mobile songbook (`apps/web`): installable offline PWA with model picker, search by title, artist or song number, browse by letter, full-size number read-out, light and dark themes, About, Privacy and Rights pages, a synthetic demo catalog, 115 unit tests and 36 end-to-end tests (including offline reload and accessibility scans in both themes).
- CI workflow for the catalog pipeline and the web app.
- M1 catalog pipeline (`catalog/`): SQLite migrations, source discovery, polite fetcher, geometry-based PDF extractor, validator, importer, local bundle builder and the `kantahan-catalog` CLI, with 140 tests.
