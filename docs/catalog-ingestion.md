# Catalog ingestion

> M4 update (2026-10-24): the extractor now also reads the older two-table layouts and tables with merged artist cells, volumes are mapped to machine groups by a separate `map` step, and `import --reimport` re-extracts documents after an extractor fix. See the section "Older layouts and M4 results" at the end.

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
| Rows still flagged as uncertain after the overlap rule below | 12 of 12,489 (0.1%): uncertain titles in Vol 77, 88 and 91, none in a Reyna release |
| Rows changed by the overlap rule compared with plain nearest-row assignment | 878 (7.0%); no document left unresolved except those 12 rows |
| Hand-checked sample | 36 rows from Vol 62, 95 and 108 (three layout generations) compared with the rendered pages, checked **before** the overlap rule was added; after it, a sample of changed rows was read for plausibility but not compared against the page images (the recovered words are the text layer's hidden overflow lines, which the page does not show) |

The sample is small. It supports "the extractor reads the audited layouts correctly", not a precise error rate. M3 should add a larger hand-checked set before relying on automatic publication.

### The overprint defect and the overlap rule

In many older volumes the text of one row overflows into the next row and the two are drawn on top of each other (for example "Nathan" over "Mabuhay"); a long title or artist can wrap onto a third or fourth line that is covered by the next row. Plain nearest-row assignment puts the overflowing words in the wrong row or drops them.

`_assign_cell` in `extract.py` resolves this with three facts about the documents:

1. Two words that overlap cannot be in the same cell (wrapped lines never overlap; line pitch is larger than glyph height).
2. The PDF writes cells row by row, so of two overlapping words the **one written first belongs to the row above** the nearest row boundary and the later one to the row below. The overlap must sit close to a boundary (within 0.6 of a row pitch) or it is left unresolved.
3. Words on the same text line that do not overlap horizontally belong to the same cell, so a word that only partly overlaps travels with its line.

Anything still ambiguous (an overlap that cannot be placed at a boundary, or words still overlapping inside one row) is **unresolved**: the row and its neighbours are flagged (`overprint` for artist, `title_overprint` for title). Flagged artists are withheld from bundles and flagged titles leave the row out.

How this was chosen: a dynamic-programming split of the word stream into rows was tried first and was worse than nearest-row assignment (it shifted words between rows). The stream-order rule fixed the known bad rows ("Anak Dalita" now reads "Mabuhay Singers", "Best Song Ever" reads "One Direction", "Dati" reads "Sam Conception & Tippy Dos") and also recovered wrapped title lines that nearest-row assignment had lost ("Would I Lie To" now "Would I Lie To You"). For the Reyna bundle the effect is **519 artists withheld before, 0 after**.

Known limits: the rule assumes the PDF writes cells row by row (true for every audited document; a different generation could break it, which would show up as unresolved rows or odd text); some recovered text is still cut off in the source itself (for example "Ariana Grande Ft. Nathan", where the PDF has no "Sykes"); and a mid-word wrap leaves one lowercase letter on the next line, which is glued back on (a standalone "x" is kept as a separator).

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

A release is `mapped` to Reyna only when its page-1 header says "For Reyna", and to another machine group when the publisher's page lists it there (M4; see [model-compatibility.md](model-compatibility.md)); a release with no evidence is `held` and never built. On the real data: **14 releases mapped** (Vol 62 to 76, 3,216 rows), **29 held** (9,273 rows), 0 quarantined; the 14 mapped releases build to **3,180 songs**. Sources B and C add 77 links to the same 43 documents and no new documents.

## Build rules (implemented)

- Only `mapped`, **not superseded** releases of the requested model. Rows with an overprinted title are left out.
- A number listed by several releases with the same text collapses to one entry (30 such re-listings in the Reyna data).
- A number listed with different text is a **conflict**: excluded, and the build is marked `building` instead of `validated` (exit code 2). The Reyna data has none.
- Output is deterministic (sorted keys). Every build is written to an immutable `<model>.v<N>.json` whose SHA-256 is recorded in `catalog_version_model`. The stable `<model>.json` is replaced atomically **only by a validated build**, so a partial build never overwrites a good bundle.

## Not done yet

Scheduled 14-day runs and monthly audit, publication, manifest and gzip, client sync (M3). Other model families (M4). A larger hand-checked accuracy set. Source D product-page compatibility text (blocked by HTTP 429 in the audit).


## Older layouts and M4 results

**Readers.** Documents are first read through their cell borders (the Reyna-era layout, unchanged). When that leaves song codes outside every table that the validator would reject (more than 3, or more than 1 and over 1% of rows), or finds no usable table structure, the document is read by where its 5-digit codes sit instead. The code column of each table is measured on each page, because pages of one document are laid out with different offsets (some alternate between two, book style). A table's cut is the strongest per-line vote for where the widest gap on a text line ends, and a page with too little to measure borrows from the nearest page on the same side of the spread. Whichever reading leaves fewer stray codes wins, with the border reading preferred on ties.

**Merged artist cells.** Some layouts ("5x5 Featured Artists") draw one artist cell across five rows. A tall rectangle in the artist column gives its text to every row it covers.

**Safety checks.** All 43 Reyna-section documents, and every other document read through borders, extract identically with the new code (compared row by row). The older layouts were checked against rendered pages. A bundle never changes when a document is re-imported with the same hash unless `--reimport` is used on purpose; `--reimport` replaces a document inside one transaction, keeps every section's link to a shared file and any `withdrawn_at`, checks the new rows against the old count, and keeps the old import if the new reading is rejected. Run `map` afterwards.

**Reviewed exceptions.** `catalog/reviewed.yaml` lists files a person checked on the rendered page where the source legitimately leaves artists blank. It names files and reasons only.

**Results (local run, 2026-10-24).** 363 files fetched (815 MB, 0 failures), 295 distinct documents, 292 releases imported, 3 documents quarantined (see [model-compatibility.md](model-compatibility.md)), about 62,000 rows in mapped releases, 12 bundles published.

**Zone edges.** Table zones in the border-free reader do not overlap: a one-letter title word ("I") sitting at the cut used to be read as part of the previous table's artist (found in review; 488 stored rows in older documents had stray text such as "Twenty One I Pilots", all corrected).

**Scheduled runs.** `run` and `audit` cover every machine group the publisher lists (`--section all`); a section that is not in `mapping.py` yet is reported with a warning and its volumes simply wait, without blocking the others.
