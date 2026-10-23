<p align="center"><img src="apps/web/public/brand/icon-192.png" alt="Kantahan logo" width="96" height="96"></p>

# Kantahan

Offline-first digital karaoke songbook. Pick your machine model, then search by song title, artist, or song number.

> **Status: early development (M2 done).** The catalog pipeline (`catalog/`) and the offline songbook app (`apps/web`) exist and run locally; the app ships with a clearly fake demo catalog, and no real catalog data is published. See [HANDOFF.md](HANDOFF.md) for exactly what exists and what is next.

Kantahan is an independent project. It is **not affiliated with, endorsed by, or sponsored by** Platinum Karaoke or Vismay International Corporation. See [docs/legal-and-attribution.md](docs/legal-and-attribution.md).

## Scope

A songbook only: search, model selection, offline use, automatic catalog updates. No queueing, accounts, playback, lyrics, or social features.

## Planned architecture

- `apps/web`: React + TypeScript + Vite + Tailwind PWA, IndexedDB for local catalogs, in-browser search (implemented, M2; automatic updates are M3)
- `catalog`: Python + SQLite pipeline that discovers, fetches, extracts, validates and builds catalog bundles (implemented locally in M1; scheduling and publishing are M3)
- `deploy`: Docker Compose for a self-hosted VPS (planned, M5)

Details: [docs/architecture.md](docs/architecture.md).

## Documentation

| Doc | Purpose |
|---|---|
| [HANDOFF.md](HANDOFF.md) | Current state, next steps, commands. Start here when resuming. |
| [docs/source-audit.md](docs/source-audit.md) | M0 findings: what was verified vs assumed, blockers |
| [docs/catalog-sources.md](docs/catalog-sources.md) | Source registry and discovered document links |
| [docs/model-compatibility.md](docs/model-compatibility.md) | Model family and volume mapping, with evidence |
| [docs/catalog-ingestion.md](docs/catalog-ingestion.md) | Extraction approach and validation rules |
| [docs/legal-and-attribution.md](docs/legal-and-attribution.md) | Rights status and disclaimers |
| [docs/design.md](docs/design.md) | Brand, logo and UI constraints |
| [docs/decisions/](docs/decisions/README.md) | Architecture decision records |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |

## Catalog data

This repository contains **code and documentation only**. Source PDFs and extracted song data are not committed or redistributed while reuse rights are unresolved.

## License

Code and documentation: [MIT](LICENSE). The license does not cover third-party catalogs or trademarks.
