# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Disk safety: the scheduled `run` refuses to download when less than 1 GB is free (`--min-free-mb`), cron job logs rotate past 5 MB, and the deployment guide has a measured disk budget with the one unbounded item (Docker build cache) called out.
- **All machines** view: one search over every machine's songs. Rows are never merged across machines; each row names its machine, so the same number on two machines shows as two labelled rows. The sign, the chip and the read-out follow the song's machine, and a machine that cannot be loaded is named while the others still show. See [ADR 0007](docs/decisions/0007-all-machines-view.md).

### Changed
- UI reroll, "Metro Wayfinding" ([ADR 0006](docs/decisions/0006-wayfinding-ui.md)): the pink-purple theme and the LED scoreboard numbers are gone. Calm light-first look (dark follows the phone), a coloured line sign for the selected machine, ruled song rows with a heavy plain number at the end, a new number sheet, new palette, Barlow Semi Condensed for the wordmark and numbers (Fredoka and DSEG7 removed), a new logo, a dynamic microphone that is also a magnifying lens (the old K tile looked like the owner's website), icons and share image. Behaviour, copy and data are unchanged.

### Added
- M5 production readiness: a private contact form on the Rights and removal page and the contact service behind it (honeypot, per-address and overall rate limits, Origin and content checks, header-injection safe mail, nothing stored or logged); Docker Compose deployment (nginx web image with a strict Content-Security-Policy and per-path caching, contact image, on-demand ingest job; non-root, read-only, no capabilities); `backup` and `restore` commands; a cron wrapper that reports only failures; a deployment smoke test with a real-browser policy check; CI jobs for the contact service, the deployment and weekly dependency audits; first-visit speed-ups (inline boot script with a CSP hash, early manifest download, lazy text pages, 2 KB wordmark font). Lighthouse on the production images: mobile 91-92 performance and 100 elsewhere, desktop 100. Documented in `docs/deployment.md`, `docs/configuration.md`, `docs/security.md` and ADR 0005.
- M4 other Platinum machine groups: 12 models (one per publisher section, migration 0005), a `map` step joining each volume to every group that lists it (Reyna still needs its own header), an extractor that also reads the older two-table layouts and merged artist cells, `import --reimport`, `catalog/reviewed.yaml`, coverage wording for monthly lists, conflict handling (same title with different artist keeps the song; up to 5% title conflicts are left out and counted), and the "N song numbers are left out" note in the app. Decision in `docs/decisions/0004-machine-group-models.md`.
- M3 automatic updates: `kantahan-catalog publish`, `run` (cron entry point with a 14 day interval and a run lock), `audit`, `rollback`, `suspend`/`resume` and `withdraw`; versioned bundles plus a manifest with SHA-256 per model, safety gates, atomic swap (migration 0004, `catalog/display.yaml`). The app checks for a newer catalog on open and on demand, verifies every download, swaps it in one transaction, keeps the old catalog on any failure, and shows a notice when the catalog is paused. Documented in `docs/catalog-updates.md` and `docs/security.md`.
- Repository bootstrap: README, license, agent instructions, documentation skeleton.
- M0 source audit documents (see `docs/source-audit.md`).
- Logo, favicon, PWA and social images (`apps/web/public/brand/`) and design notes.
- M2 mobile songbook (`apps/web`): installable offline PWA with model picker, search by title, artist or song number, browse by letter, full-size number read-out, light and dark themes, About, Privacy and Rights pages, a synthetic demo catalog, 115 unit tests and 36 end-to-end tests (including offline reload and accessibility scans in both themes).
- CI workflow for the catalog pipeline and the web app.
- M1 catalog pipeline (`catalog/`): SQLite migrations, source discovery, polite fetcher, geometry-based PDF extractor, validator, importer, local bundle builder and the `kantahan-catalog` CLI, with 140 tests.
