# Architecture

> **Status: the catalog pipeline is implemented locally (M1, `catalog/`); the web app, scheduling, publication, contact endpoint and deployment are planned.** Rows below say which is which.

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
| Scheduled runs, manifest, publication | Python, cron | M3, planned |
| Web app: model selector, search, offline, silent sync | React, TypeScript, Vite, Tailwind, service worker, IndexedDB | M2, M3 |
| Contact endpoint for rights inquiries | small server-side SMTP relay | M5 |
| Deployment | Docker Compose on a VPS behind an existing reverse proxy | M5 |

## Principles

- Static delivery; no permanently running search server. Search runs in the browser.
- Model-specific song entries: a song is never assumed available on a machine because it appears in another model's catalog.
- Never publish uncertain data: failed or suspicious imports are quarantined and the previous catalog stays live.
- Song numbers are strings and keep leading zeros.

See [catalog-ingestion.md](catalog-ingestion.md) for the extraction findings that shape the pipeline.
