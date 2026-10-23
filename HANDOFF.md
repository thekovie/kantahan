# Handoff

Last updated: **2026-10-23**

## Current milestone

**M0, Source Audit: audit documents written; waiting on owner decisions before M1.** No application code exists.

## Completed

- Project named **Kantahan** ([ADR 0001](docs/decisions/0001-project-name.md)); public repo `thekovie/kantahan`.
- Documentation skeleton; unimplemented docs carry "planned, not implemented" banners.
- Source audit of Sources A to F, Reyna-first: [docs/source-audit.md](docs/source-audit.md), [docs/catalog-sources.md](docs/catalog-sources.md), [docs/model-compatibility.md](docs/model-compatibility.md), [docs/catalog-ingestion.md](docs/catalog-ingestion.md).
- Brand identity: logo concept B (K with mic) chosen by the owner; SVG and PNG icon set, maskable icon and social image in `apps/web/public/brand/` ([docs/design.md](docs/design.md), [ADR 0002](docs/decisions/0002-brand-identity.md)). Standalone wordmark deferred until the display font is chosen.
- Machine-readable registries: [catalog/sources.yaml](catalog/sources.yaml), [catalog/discovered-reyna-source-a.json](catalog/discovered-reyna-source-a.json) (43 documents: URL, size, SHA-256, header classification; no song data).

## Key findings (details in the audit)

- Source A builds its lists in the browser from `songlist-update-data.js`; parse it statically, never execute it.
- All 43 Reyna-section links return PDFs with a text layer (no OCR). Layout is a 3-column grid of Title | 5-digit number | Artist; reading-order text interleaves columns, so extraction must use word coordinates. **No parser exists and no accuracy is claimed.**
- Lists are **incremental** ("Additional List"). No full base catalog is published; Vol 97 and 107 are absent.
- **Source A's "REYNA SERIES" section is not reliable evidence of Reyna compatibility.** Only Vol 62 to 76 say "For Reyna"; Vol 96 to 108 say "T-X Series"/"K-Box".
- Source D sells separate "Reyna /2/3C/SE", "Reyna 3/4" and "T-X" volumes (Vol 100, 101, 102, 103, 105, 108), so Reyna variants differ.
- B and C contain no Reyna documents that A lacks.
- No license or reuse statement found; ToS not reviewed.

## Blockers and dependencies

1. **Rights (blocker for any public catalog):** permission or documented legal basis needed. Nothing derived from the PDFs is committed or published.
2. **Model mapping:** which volumes map to Reyna 2/3C/SE vs Reyna 3/4 is unknown. Source D product pages returned HTTP 429, so their descriptions are unread.
3. **Coverage:** content before Vol 62 and Vol 107 is not available in the archives.

## Outstanding tasks (M0)

- Retry Source D product pages slowly (one request per minute) and record compatibility text.
- Review Platinum/Vismay terms of service, the site's `agents.md`, and MediaFire terms for automated retrieval.
- Draft a permission request to Platinum Karaoke / Vismay.

## Known issues

- The audit environment's `pip`/`uv` installs stalled when fetching packages, so `pdfplumber` was never tested. Confirm package access at the start of M1.
- Audit helper scripts were run from a scratch folder and are not in the repo; the method is described in the audit doc.

## Next recommended steps

1. Owner reviews [docs/source-audit.md](docs/source-audit.md) and answers section 9 (permission request, M1 locally, coverage messaging).
2. M1: SQLite schema and migrations, importer, extractor spike (pdfplumber vs pdfminer vs PyMuPDF) with synthetic fixtures and hand-checked rows from Vol 62 to 76.
3. M2 UI starts only after M1; run the design skills first (see the plan).

## Key paths

| Path | What |
|---|---|
| `docs/` | all documentation; start at `docs/source-audit.md` |
| `catalog/sources.yaml` | approved source registry |
| `catalog/discovered-reyna-source-a.json` | discovered Reyna documents with hashes |
| `.github/copilot-instructions.md`, `CLAUDE.md` | agent pointers |

## Commands

None yet. There is nothing to build, test or run. The repository currently contains documentation and two data registries.

## Testing status

No tests exist. Policy: tests first, 80%+ coverage (see [docs/testing.md](docs/testing.md)).

## Important decisions

- Repository is public: **no PDFs or song data are ever committed** (`.gitignore` blocks `*.pdf`).
- Code and docs MIT licensed; the license does not cover third-party catalogs.
- Commits and PRs carry no co-author or tool attribution.
- Scope stays a songbook only.

## Recent changes

- 2026-10-23: repo created, documentation skeleton and M0 audit added; logo and icon set added.
