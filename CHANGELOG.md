# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Repository bootstrap: README, license, agent instructions, documentation skeleton.
- M0 source audit documents (see `docs/source-audit.md`).
- Logo, favicon, PWA and social images (`apps/web/public/brand/`) and design notes.
- M2 mobile songbook (`apps/web`): installable offline PWA with model picker, search by title, artist or song number, browse by letter, full-size number read-out, light and dark themes, About, Privacy and Rights pages, a synthetic demo catalog, 115 unit tests and 36 end-to-end tests (including offline reload and accessibility scans in both themes).
- CI workflow for the catalog pipeline and the web app.
- M1 catalog pipeline (`catalog/`): SQLite migrations, source discovery, polite fetcher, geometry-based PDF extractor, validator, importer, local bundle builder and the `kantahan-catalog` CLI, with 140 tests.
