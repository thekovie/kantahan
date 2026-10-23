# Catalog ingestion

> **Status: design from M0 findings. The pipeline is not implemented yet (starts in M1).** Statements marked *verified* come from the audit; everything else is a plan.

## Inputs (verified)

- Source A links are read statically from `songlist-update-data.js`; B and C from HTML tables. Exact URLs only, never built from volume numbers.
- Documents are PDFs with a text layer (no OCR needed in the 43 Reyna-section files).
- Documents are incremental "Additional List" volumes, not full catalogs.

## Pipeline stages (planned)

1. **Discover**: fetch approved index pages, parse links, diff against the previous discovery. Removed links never delete songs; they raise a review flag.
2. **Fetch**: GET only new or changed links, at a very low rate with backoff on HTTP 429; record size and SHA-256. MediaFire gives no ETag/Last-Modified, so identity is file id plus content hash.
3. **Extract**: use word coordinates, not reading-order text. Find each 5-digit number token, pair it with the title cell to its left and the artist cell to its right within the same row band, and join wrapped artist lines. One parser profile per layout generation (see [model-compatibility.md](model-compatibility.md)).
4. **Normalize**: keep raw title and artist; add case-folded, accent-folded search forms. Numbers stay strings with leading zeros (`00589`).
5. **Validate**: see below. Failures quarantine the document; nothing uncertain is published.
6. **Build and publish** versioned per-model bundles (see [catalog-updates.md](catalog-updates.md), planned).

## Validation rules (planned)

- Song number matches the expected pattern (5 digits so far; leading zeros allowed) and is unique per model and release.
- Title is present; artist missing rate stays within a threshold.
- No unexpected duplicates: the same title with different numbers is **allowed** (verified in Vol 108).
- Row count per page and volume stays within tolerance of the previous parse of the same document.
- Number range sanity: tokens far outside a volume's main block (seen in several volumes) are flagged for review, not auto-accepted.
- Document header must map to a model through an evidence row.
- Large unexplained deletions or structure changes quarantine the release.

## Known parsing hazards (verified)

- Three-column tables per page; artist cells wrap over up to three lines in a smaller font.
- Images and ads on early pages interleave with text.
- Page furniture such as `12345` appears as a 5-digit token in some volumes.
- Layout and header text differ across generations (Vol 62 to 76, 77 to 81, 82 to 94, 95, 96 to 108).

## Open decisions for M1

- Extractor library (pdfplumber, pdfminer or PyMuPDF), chosen by a spike measured on hand-checked rows. Installing pdfplumber stalled in the audit environment; confirm package access first.
- Accuracy target and sampling method per generation. **No accuracy figure exists yet.**
