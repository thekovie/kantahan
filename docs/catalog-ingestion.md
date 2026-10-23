# Catalog ingestion

Status: **discover, fetch, extract, validate, import and local build are implemented (M1). Scheduled runs, publication and client sync are planned (M3).** Findings below were measured on 2026-10-23 against the 43 documents in the "REYNA SERIES" section of Source A. Source documents and extracted data stay on the developer machine under `catalog/work/` (gitignored).

## Pipeline (`catalog/src/kantahan_catalog/`)

| Stage | Module | Command | Behavior |
|---|---|---|---|
| Discover | `discover.py` | `discover` | Reads Source A's page, finds `songlist-update-data.js`, parses its array literal **as data** (a small scanner, never executed); reads B and C as HTML tables. Records exact URLs; reports added, removed and changed links against the previous run |
| Fetch | `fetch.py` | `fetch` | Allowlisted hosts only (checked after every redirect), robots.txt honored on the Platinum hosts, 3 s gap between requests, backoff on HTTP 429 using `Retry-After`, strict `https` URL check (no credentials, default port, no parser-confusing characters), robots.txt also checked on redirect targets, 50 MB and 300 s caps per response, `%PDF-` check, atomic write. Files are stored by MediaFire file key. `--refresh` downloads again even if the file exists |
| Extract | `extract.py` | (inside `import`) | Geometry-based, see below |
| Validate | `validate.py` | (inside `import`) | Rules below. Any error quarantines the document |
| Import | `importer.py` | `import` | Hashes the file; identical bytes are never re-imported; classifies the page-1 header; creates a `mapped` or `held` release. A newer document for the same file key (or link) **supersedes** the older release, which stays as history and is never built. `--retry-quarantined` evaluates quarantined documents again after an extractor fix |
| Build | `build.py` | `build --model reyna` | Local bundle from `mapped` releases only |

Run order: `migrate` (done automatically by `import`), `discover`, `fetch`, `import`, `stats`, `build`.

## Extraction

The audited PDFs draw up to three tables per page. Each row is `Title | icon | number | artist`, with per-row vertical cell borders. The extractor:

1. Collects vertical border segments (thin rectangles and lines) from every page and clusters them into a **per-document template** of 4 borders per table. A last table with only 3 borders reuses the artist cell width of the others, provided that stays on the page. Any other count, or more than 40 pages, raises an extraction error and the document is quarantined.
2. Reads words in PDF stream order (`use_text_flow`), which keeps overprinted words apart.
3. Takes number-like tokens inside number cells as rows. Title words are those in the cell to the left, artist words those in the cell to the right, assigned to the nearest row (within 0.9 of a row pitch). Wrapped lines are joined top to bottom.
4. Counts 5-digit tokens outside any number cell as `stray_tokens` (a coverage check). Numbers are ASCII digits only (`fullmatch`).

### Measured results (43 documents)

| Check | Result |
|---|---|
| Documents extracted | 43 of 43, no errors |
| Rows | 12,489 |
| Rows vs an independent count of 5-digit tokens in the PDF text (PDFKit, taken during the M0 audit) | 40 of 43 documents match exactly; Vol 72, 81 and 94 each have one fewer row, which is the single stray token outside the tables that the extractor excludes (the `12345` page furniture in Vol 72 and 94) |
| Malformed numbers, duplicate numbers within a document, empty titles | 0 |
| Rows with an empty artist cell | 13 |
| Rows with possibly overprinted artist text (artist uncertain) | 1,267 (10.1%), none in Vol 100 to 106 |
| Rows with possibly overprinted title text | 167 (1.3%), all in volumes that are not Reyna evidence except 6 rows in Vol 70, 71 |
| Hand-checked sample | 36 rows from Vol 62, 95 and 108 (three layout generations), compared with the rendered pages: number, title and artist correct on every row that is not flagged; one flagged row confirmed garbled |

The sample is small. It supports "the extractor reads the audited layouts correctly", not a precise error rate. M3 should add a larger hand-checked set before relying on automatic publication.

### The overprint defect

In many older volumes the artist text of one row overflows onto the next row and the two are drawn on top of each other (for example "Nathan" over "Mabuhay"). Which row an overflowing word belongs to cannot be recovered from geometry or stream order; a dynamic-programming split was tried and was worse than nearest-row assignment. The extractor therefore looks at **every pair of words in a column**, including words assigned to different rows, and treats any overlap as suspect for both rows and both of their neighbours. Artist overlaps set `overprint`, title overlaps set `title_overprint`.

The importer stores the raw text. The builder keeps number and title but **withholds the artist** (`u = 1`) for `overprint` rows, and **leaves out** `title_overprint` rows entirely. For the Reyna bundle that is **519 of 3,180 songs (16.3%) without an artist** and 6 rows left out. This is deliberately conservative: neighbours of an overlap are suspect even when they are fine. A reviewed override list is the way to recover them and is a possible later step.

## Validation rules (implemented)

Errors quarantine the whole document, so nothing uncertain is built:

- number is not 5 digits (leading zeros allowed)
- empty title
- the same number twice in one document with different text
- more than 5% of rows without an artist
- more than one number-like token outside every table when that is over 1% of the rows or over 3 tokens (rows may have been missed; a single token is audited page furniture and tolerated)
- more than 2% fewer rows than the previous parse of the same link
- no rows at all, or an extraction error

Warnings are recorded but do not block: identical duplicate number (imported once), a few missing artists, overprinted artists or titles, a single stray token, and numbers far from the volume's main block (more than 450 from the median).

## Model mapping (implemented)

A release is `mapped` only when the page-1 header says "For Reyna" (see [model-compatibility.md](model-compatibility.md)); everything else is `held` and never built. On the real data: **14 releases mapped** (Vol 62 to 76, 3,216 rows), **29 held** (9,273 rows), 0 quarantined; the 14 mapped releases build to **3,180 songs**. Sources B and C add 77 links to the same 43 documents and no new documents.

## Build rules (implemented)

- Only `mapped`, **not superseded** releases of the requested model. Rows with an overprinted title are left out.
- A number listed by several releases with the same text collapses to one entry (30 such re-listings in the Reyna data).
- A number listed with different text is a **conflict**: excluded, and the build is marked `building` instead of `validated` (exit code 2). The Reyna data has none.
- Output is deterministic (sorted keys). Every build is written to an immutable `<model>.v<N>.json` whose SHA-256 is recorded in `catalog_version_model`. The stable `<model>.json` is replaced atomically **only by a validated build**, so a partial build never overwrites a good bundle.

## Not done yet

Scheduled 14-day runs and monthly audit, publication, manifest and gzip, client sync (M3). Other model families (M4). A larger hand-checked accuracy set. Source D product-page compatibility text (blocked by HTTP 429 in the audit).
