# Source audit (M0)

Date of audit: **2026-10-23**. Scope: Reyna-first feasibility of discovering, extracting and publishing song numbers from official Platinum Karaoke song-list archives.

Evidence labels used below: **VERIFIED** (observed directly during this audit), **INFERRED** (derived from verified data, not confirmed at row level), **UNVERIFIED** (not checked), **BLOCKER** (needs a decision or permission before it can be relied on).

Method: read-only requests with an identifying User-Agent, 1.5 to 4 s spacing, no login, no bypass of rate limits. 43 Reyna-section PDFs were downloaded to a local scratch folder for inspection and are **not** stored in this repository. Per-document facts: [`catalog/discovered-reyna-source-a.json`](../catalog/discovered-reyna-source-a.json).

## Summary

| Question | Answer |
|---|---|
| Can we discover document links automatically? | **Yes (VERIFIED).** Source A exposes every link in a public data script; B and C are static HTML. |
| Are the PDFs machine-readable without OCR? | **Yes (VERIFIED)** for all 43 Reyna-section PDFs: each has a text layer with 5-digit song numbers. |
| Can title, number and artist be paired reliably? | **Not yet proven.** Layout is a 3-column grid; naive reading-order text interleaves columns. Geometry-based extraction is required (see below). |
| Are the lists full catalogs or incremental? | **Incremental (VERIFIED).** Every file is titled "Additional List"/"New Songs"; song numbers continue from volume to volume. No full base catalog is published. |
| Does Source A's "REYNA SERIES" section mean "Reyna songs"? | **No (VERIFIED).** Only Vol 62 to 76 say "For Reyna". See model association. |
| Are reuse and redistribution rights resolved? | **No (BLOCKER).** No license found; Terms not yet reviewed. |

## 1. Discovery

- **VERIFIED:** Source A (`/pages/songlist-update`) returns an empty `<div id="songlist-update-root">`; the lists are built in the browser from `songlist-update-data.js` (`const songList=[{product, years|volumes}...]`). The array is plain data and can be parsed statically (never execute the script).
- **VERIFIED:** 12 product sections, 391 MediaFire links plus 2 on `cdn.shopify.com`. The Reyna section has 43 links, labelled Volume 62 to 108.
- **VERIFIED:** Labels are not uniform: `64-65` and `104~105` are single files covering two volumes. Volumes **97 and 107 are absent** from A, B and C.
- **VERIFIED:** Source B has 42 Reyna links, Source C has 35 (Vol 62 to 98). Every link on B and C also appears on A. B and C add **no unique Reyna documents**; B lacks Vol 108.
- **VERIFIED:** Page A also lists an HDD entry for "November 2026" although the audit date is 23 October 2026. Not checked; treat as an anomaly to watch (UNVERIFIED).

## 2. Link health

- **VERIFIED:** All 43 Reyna links resolve (302 to `download*.mediafire.com`) and return `application/pdf`; sizes range from 60 KB (Vol 101) to 8.7 MB (Vol 69).
- **VERIFIED:** No `ETag` or `Last-Modified` was present in the headers read. Change detection must use SHA-256 plus diffing the discovered link list. The MediaFire download host changes per request, so only the stable file id and content hash identify a document.
- **VERIFIED:** `platinumkaraoke.com` rate-limits (HTTP 429, `Retry-After: 60`): the collection page returned 429 on the fifth page request, 1.5 s apart, and product pages kept returning 429 on retries minutes later. One transient "empty reply" from MediaFire was also seen. The crawler needs backoff and a very low request rate.
- **UNVERIFIED:** Non-Reyna sections (about 350 links) were not link-checked.

## 3. PDF structure and extractability

Sample read: Vol 62, 64-65, 85, 95, 108 (text and a rendered page image each); header text and number statistics for all 43.

- **VERIFIED:** All 43 have a text layer; none needed OCR. Page counts: 1 to 6.
- **VERIFIED:** Layout is a designed brochure: three side-by-side tables per page, each row `Title | number | Artist`, plus images and ads on early pages. Artist cells use a small font and often wrap onto two or three lines.
- **VERIFIED:** Song numbers are **5 digits** in the main body. Vol 108 also contains numbers with **leading zeros** (`00589`, `03150`, `06155`, `03167`), so numbers must be stored as strings.
- **VERIFIED:** Several titles repeat with different numbers (for example "Hurting Each Other" at `00589`, `03150`, `06155` in Vol 108), so titles must never be deduplicated across numbers.
- **VERIFIED:** Naive PDFKit text (reading order) interleaves the three columns for Vol 62 (titles, numbers and artists from different rows mix). Vol 108 extracts closer to row order. Result: a reliable parser must use word coordinates and pair each number with the title to its left and the artist to its right in the same row band.
- **VERIFIED (tooling):** A first attempt at word reconstruction with macOS PDFKit character bounds produced fragmented words, so it is not a suitable basis. Installing `pdfplumber` in the audit environment stalled on package download; the extractor library choice (pdfplumber, pdfminer or PyMuPDF) is decided in M1 with a spike.
- **UNVERIFIED:** Row-level accuracy. No parser exists yet, so **no accuracy figure is claimed**. M1 must measure it against hand-checked rows from each layout generation.
- **INFERRED:** Number tokens far outside a volume's main range (Vols 62, 72, 73, 74, 77, 78, 82, 83, 84, 90, 95) are either older songs re-listed in the volume or extraction noise such as page furniture (`12345` appears in Vols 72 and 94). Row-level review is needed before trusting them.
- **INFERRED:** Five generations of layout/header exist (see section 5), so one parser profile per generation, validated on fixtures, is likely.

## 4. Base catalogs versus incremental updates

- **VERIFIED:** File names and page headers say "Additional List" or "New Songs". The main number block of Vol 62 starts at 15562; no volume has a main block below that in these archives (stray tokens below it are discussed in section 3).
- **VERIFIED:** Number ranges are contiguous from one volume to the next in Vol 62 to 78 (for example Vol 66 is 16038 to 16157, Vol 67 starts at 16158). Later runs: 79 to 90 and 91 to 106 are each contiguous, with jumps between runs (18999 to 26083 and 29999 to 38022) that coincide with header changes.
- **INFERRED:** About 240 numbers (41987 to 42227) fall between Vol 106 and the new numbers in Vol 108, consistent with Vol 107 being unpublished here. No number gap exists at Vol 97 (96 ends 40146, 98 starts 40147).
- **BLOCKER:** A complete Reyna catalog needs the base content that shipped before Vol 62 (numbers below 15562) and Vol 107. Neither is in Sources A to C. The app can only claim to cover songs from the volumes it has, and must say so.

## 5. Model association

What each Reyna-section document says about itself (header on page 1):

| Volumes | Header text | Count |
|---|---|---|
| 62 to 76 (incl. 64-65) | "For Reyna" (Vol 66: "For Reyna DVD") | 14 |
| 77 to 81 | "T-X-R-BMB Series" | 5 |
| 82 to 94 | "Volume N" only (no family named) | 13 |
| 95 | "SD SERIES" | 1 |
| 96 to 108 | "T-X Series" with "K-Box Series V. N" (Vol 108: "T-X series Vol. 108 / KBox Vol. 35") | 10 |

- **VERIFIED:** Source A files Vol 77 to 108 under Reyna, yet 29 of 43 documents do not call themselves Reyna lists. Section placement on the page is **not** evidence of machine compatibility.
- **VERIFIED:** Source D sells **separate products** named "Volume N Reyna /2/3C/SE", "Volume N - Reyna 3/4" and "Volume N T-X Series" for N = 100, 101, 102, 103, 105 and 108 (the collection page listing as fetched; other volumes may be sold elsewhere). This confirms the Reyna variants are distinct from each other and from T-X, and that the free PDFs on A do not clearly correspond to either Reyna variant for Vol 100 and later.
- **UNVERIFIED:** Product descriptions for those listings (HTTP 429). Do not map any file to a specific Reyna variant until read.
- **BLOCKER:** No public evidence links the post-76 PDFs to Reyna 2/3C/SE or to Reyna 3/4. Until resolved, only Vol 62 to 76 (headers say "For Reyna") are candidates for a Reyna catalog, and even those do not distinguish Reyna variants.

## 6. Rights and access policy

- **VERIFIED:** `platinumkaraoke.com/robots.txt` allows `/` and `/pages/` for all agents and disallows cart, checkout, account, admin and filter/sort crawl traps. It points agents to a separate `agents.md` aimed at shopping actions. `platinumkaraoke.ph/robots.txt` only blocks a short list of SEO bots.
- **VERIFIED:** The PDFs carry Platinum Karaoke branding and the `platinumkaraoke.ph` watermark. No license, reuse grant or "free to redistribute" statement was found on the pages inspected.
- **UNVERIFIED:** Platinum's and Vismay's terms of service, the `agents.md` document, MediaFire's terms for automated retrieval, and whether bulk song metadata extraction and redistribution is permitted.
- **BLOCKER:** Redistribution of catalog data derived from these PDFs requires permission (or a documented legal basis). Until then: do not commit PDFs or extracted data, do not publish a catalog publicly, keep ingestion for local development only. See [legal-and-attribution.md](legal-and-attribution.md).

## 7. Other sources

- **Source E** (`/pages/song-update`): VERIFIED to be a product listing (update bundles, prices). It is not a catalog and not reusable metadata.
- **Source F** (FAQ): VERIFIED to describe the Cello USB update steps and firmware updates; the HDD archive being organised by month and the FAQ's reference to monthly updates agree. No publication schedule, authentication or licensing terms were found in the text read (about 22 KB of page text, skimmed not exhaustively).
- **Source D** (collection): VERIFIED product names only. See model association.

## 8. Go / no-go for M1

| Item | Decision |
|---|---|
| Build the SQLite schema, importer and validators | **Go** |
| Parser for the "For Reyna" generation (Vol 62 to 76) | **Go**, with measured accuracy on fixtures |
| Parsers for T-X-R-BMB, unstated and T-X generations | **Conditional**: only after model mapping is resolved (these are not Reyna evidence) |
| Public publication of any catalog bundle | **No-go** until rights are resolved |
| Automatic discovery of new documents | **Go**, at a very low request rate with backoff |

## 9. Decisions needed from the owner

1. Contact Platinum Karaoke / Vismay to request permission and a statement on reuse, and to ask which published volumes map to Reyna 2/3C/SE and Reyna 3/4.
2. Confirm that M1 continues locally (no public data) while permission is pending.
3. Decide how to present partial coverage (volumes from 62 onward only) in the app.
