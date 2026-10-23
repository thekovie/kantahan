# Handoff

Last updated: **2026-10-23**

## Current milestone

**M1, Database and importer: implemented and run locally on the real Reyna-section documents. Local only: nothing derived from the PDFs is committed or published.** Waiting on the owner for review and for the rights and model-mapping questions below before M2.

## Completed

- **M0** source audit ([docs/source-audit.md](docs/source-audit.md)), repo, docs skeleton, logo and icon set.
- **M1** catalog pipeline in `catalog/` (Python 3.12, SQLite, pdfplumber):
  - numbered migrations with down scripts, seed of 12 model families and the `reyna` model ([docs/database-schema.md](docs/database-schema.md))
  - discovery of Source A (static parse of its data script), B and C; link diff
  - polite fetcher: host allowlist (re-checked after redirects), robots.txt, 3 s spacing, 429 backoff, size cap, atomic writes
  - geometry-based PDF extractor with per-document table template ([docs/catalog-ingestion.md](docs/catalog-ingestion.md))
  - validator (quarantine on errors), importer (hash dedupe, mapped/held releases, canonical song linking), local bundle builder (conflicts, uncertain artists withheld)
  - CLI `kantahan-catalog` (`migrate`, `discover`, `fetch`, `import`, `stats`, `build`)
  - 138 tests, 98% coverage, ruff and mypy --strict clean ([docs/testing.md](docs/testing.md))
  - an independent code review found 15 issues; the accepted ones are fixed (duplicate-row crash, row-drop baseline after quarantine, superseded documents, partial builds overwriting the stable bundle, uncertain titles, stray tokens, URL strictness, fullwidth digits, page cap, slow-response cap, header negation, CLI input handling); see [docs/catalog-ingestion.md](docs/catalog-ingestion.md)

## Results on real data (local run, 2026-10-23)

- Discovery reproduced the audit: 393 links on A (Reyna 43), B (42), C (35).
- 43 of 43 documents extracted: 12,489 rows; 40 of 43 match an independent token count exactly, the other three are one row short because of one stray token each.
- Import: 14 releases **mapped** to `reyna` (Vol 62 to 76, 3,216 rows), 29 **held** (9,273 rows, headers say T-X, SD, or name no family), 0 quarantined. B and C added 77 links to the same 43 documents.
- Build: `reyna` bundle validated, **3,180 songs**, 0 conflicts, 30 identical re-listings collapsed, **519 artists withheld (16.3%)** and 6 rows left out (uncertain title) because the source PDFs overprint neighbouring text. The rule is deliberately conservative: both neighbours of any overlap are suspect.
- Hand check: 36 rows across three layout generations were correct where not flagged. The stricter overlap rule was added after that check and has no new hand check.

## Open questions and blockers

1. **Rights (blocks any public catalog):** no license found, terms not reviewed, no permission requested. Nothing is published; `catalog/work/` is gitignored.
2. **Reyna variant:** which volumes belong to Reyna 2/3C/SE vs Reyna 3/4 is unknown. Source D product pages returned HTTP 429 in M0 and are still unread.
3. **Coverage:** only Vol 62 to 76 are evidence for Reyna; Vol 77 to 108 are listed under Reyna on Source A but their headers say T-X-R-BMB, SD, T-X/K-Box or nothing. The base catalog before Vol 62 and Vol 107 are not in the archives.
4. **Artists withheld (16.3% of Reyna songs):** needs either a reviewed override list, a smarter overlap rule, or acceptance. The row can still be found by number and title. No Vol 100 to 106 document is affected, so newer volumes are clean.
5. **Accuracy evidence is small** (36 rows hand-checked). Enlarge before M3 automation.

## Outstanding tasks

- Retry Source D product pages slowly and record compatibility text.
- Review Platinum/Vismay terms, `agents.md`, MediaFire terms; draft a permission request.
- Decide on artist overrides.

## Next recommended steps

1. Owner reviews the M1 PR and answers the questions above.
2. **M2** mobile songbook: run `impeccable init`/`shape` and the other design skills first, then build `apps/web` against a **synthetic** seed bundle (the real bundle must stay local). Bundle format is in [docs/database-schema.md](docs/database-schema.md).
3. M3 updates (scheduler, manifest, publication gate on rights).

## Key paths

| Path | What |
|---|---|
| `catalog/src/kantahan_catalog/` | pipeline modules (`extract.py` is the core) |
| `catalog/src/kantahan_catalog/migrations/` | schema |
| `catalog/tests/` | tests; `pdfgen.py` makes synthetic PDFs |
| `catalog/sources.yaml`, `catalog/discovered-reyna-source-a.json` | source registry and audited document hashes |
| `catalog/work/` | **local only, gitignored**: database, PDFs, bundles |
| `apps/web/public/brand/` | logo and icons |
| `docs/` | all documentation |

## Commands

```bash
cd catalog
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/python -m pytest && .venv/bin/ruff check . && .venv/bin/mypy src
.venv/bin/kantahan-catalog discover && .venv/bin/kantahan-catalog fetch && .venv/bin/kantahan-catalog import
.venv/bin/kantahan-catalog stats && .venv/bin/kantahan-catalog build --model reyna
```

Details: [docs/setup-development.md](docs/setup-development.md).

## Known issues

- Overprinted artist text in older volumes (see above).
- `import_run` table is created but unused until M3.
- The 43 audited PDFs and the local database exist only on the developer machine (`catalog/work/`); recreate with the commands above.
- Package installs stalled twice during the M0 session (cause not diagnosed).

## Important decisions

- Public repo: **no PDFs or song data committed** (`.gitignore`). Local-only ingestion until rights are resolved.
- A release is tied to a model only by page-1 header evidence, never by the section it was listed under.
- Song numbers are text; entries are never merged across numbers or models.
- Uncertain data is not built: documents with errors are quarantined, conflicting numbers are excluded and block `validated`, uncertain artists are withheld.
- Commits and PRs carry no co-author or tool attribution.

## Recent changes

- 2026-10-23: M1 catalog pipeline, tests and docs (branch `m1-database`).
- 2026-10-23: M0 audit, logo and icon set.
