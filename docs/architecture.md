# Architecture

> **Status: planned, not implemented.** Nothing below exists in code yet. This describes the target design from the project brief; it will be updated to match the codebase as milestones land.

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
| Catalog pipeline: discover, fetch, extract, normalize, validate, publish | Python, SQLite, PDF extraction | M1, M3 |
| Web app: model selector, search, offline, silent sync | React, TypeScript, Vite, Tailwind, service worker, IndexedDB | M2, M3 |
| Contact endpoint for rights inquiries | small server-side SMTP relay | M5 |
| Deployment | Docker Compose on a VPS behind an existing reverse proxy | M5 |

## Principles

- Static delivery; no permanently running search server. Search runs in the browser.
- Model-specific song entries: a song is never assumed available on a machine because it appears in another model's catalog.
- Never publish uncertain data: failed or suspicious imports are quarantined and the previous catalog stays live.
- Song numbers are strings and keep leading zeros.

See [catalog-ingestion.md](catalog-ingestion.md) for the extraction findings that shape the pipeline.
