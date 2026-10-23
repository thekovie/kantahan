# Architecture

> **Status: the catalog pipeline (M1, `catalog/`) and the songbook web app (M2, `apps/web`) are implemented; automatic updates, publication, the contact endpoint and deployment are planned.** Rows below say which is which.

## Overview

```
official PDFs --> catalog pipeline (Python + SQLite) --> versioned bundles + manifest --> static hosting
                                                                                             |
                                                       PWA (React) <-- background sync <-----+
                                                       IndexedDB + in-memory search
```

## Components

| Component | Tech | Milestone |
|---|---|---|
| Catalog pipeline: discover, fetch, extract, validate, import, local build | Python, SQLite, pdfplumber | **M1, done locally** ([catalog-ingestion.md](catalog-ingestion.md)) |
| Scheduled runs, manifest, publication, rollback, suspend | Python, SQLite, cron | **M3, done locally** ([catalog-updates.md](catalog-updates.md)) |
| Web app: model selector, search, offline use | React, TypeScript, Vite, Tailwind, service worker, IndexedDB, MiniSearch | **M2, done** (update check on open and on demand: M3) |
| Contact endpoint for rights inquiries | small server-side SMTP relay | M5 |
| Deployment | Docker Compose on a VPS behind an existing reverse proxy | M5 |

## Principles

- Static delivery; no permanently running search server. Search runs in the browser.
- Model-specific song entries: a song is never assumed available on a machine because it appears in another model's catalog.
- Never publish uncertain data: failed or suspicious imports are quarantined and the previous catalog stays live.
- Song numbers are strings and keep leading zeros.

## Web app (`apps/web`)

- **Catalog loading** (`src/lib/loader.ts`): a saved copy in IndexedDB is used first; the network is asked when there is none, and every download is verified against the manifest SHA-256. Updates (`src/lib/sync.ts`) replace the manifest and saved bundles in one transaction. The manifest (`catalog/manifest.json`) lists models, each with a bundle URL; bundles are parsed and validated (`src/lib/catalog.ts`) before use, and failures are reported as offline, network or invalid.
- **Search** (`src/lib/search.ts`): an in-memory MiniSearch index per model. All-digit input is a number search (exact, leading-zero-equivalent, prefix); other input searches title and artist (prefix beats fuzzy; fuzzy only for terms of four letters or more). Results are capped at 80 and ranked deterministically. Songs of other models are never searched.
- **Offline**: vite-plugin-pwa precaches the shell (about 400 KiB) and serves `/catalog*` stale-while-revalidate; the e2e suite reloads the app offline.
- **Preferences** (theme, model) live in `localStorage`, always behind try/catch. No analytics, no third-party requests; fonts are self-hosted.
- **Catalog source for development**: `public/catalog/` holds a synthetic demo catalog (made-up songs, flagged by `manifest.synthetic` and a "Demo" pill). The real local bundle is served from the gitignored `public/catalog-local/` (`npm run catalog:local`, `VITE_CATALOG_BASE=/catalog-local`).

See [catalog-ingestion.md](catalog-ingestion.md) for the extraction findings that shape the pipeline.
