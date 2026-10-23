# Catalog sources

Registry of the sources inspected during M0. Machine-readable versions: [`catalog/sources.yaml`](../catalog/sources.yaml) (sources) and [`catalog/discovered-reyna-source-a.json`](../catalog/discovered-reyna-source-a.json) (the 43 discovered Reyna-section documents with sizes, SHA-256 and header classification). Findings and blockers: [source-audit.md](source-audit.md).

All checks were made on **2026-10-23**, read-only, with an identifying User-Agent and 1.5 to 4 second spacing between requests.

## Source registry

| ID | URL | Priority | Access | What it is |
|---|---|---|---|---|
| A | `platinumkaraoke.com/pages/songlist-update` | P0 | OK (200) | Primary archive. Lists are injected by JavaScript from `songlist-update-data.js` |
| B | `platinumkaraoke.com/pages/songlist-update-old` | P0 | OK (200) | Older snapshot, static HTML tables |
| C | `platinumkaraoke.ph/updates/Songlist Update.html` | P1 | OK (200) | Legacy Philippine archive, static HTML |
| D | `platinumkaraoke.com/collections/song-lists` | P1 | Collection OK; product pages **429** | Product listing. Reyna 2/3C/SE, Reyna 3/4 and T-X volumes are sold as separate products |
| E | `platinumkaraoke.com/pages/song-update` | P2 | OK (200) | Product listing for update bundles, not a catalog |
| F | `platinumkaraoke.com/pages/faq` | P2 | OK (200) | Update procedures (Cello USB update, firmware) |

## Hosting of the documents

All document links on A, B and C point to **MediaFire** (`mediafire.com/file/...` or `file_premium/...`), except two older files on `cdn.shopify.com`. A plain GET follows a 302 to a `download*.mediafire.com` URL and returns `application/pdf`. No login or challenge was encountered. MediaFire returns no `ETag` or `Last-Modified` for these downloads (not observed in the headers read), so change detection must rely on content hashes and on diffing the discovered link lists.

## Source A sections (from the page's data script)

| Section | Links | Structure |
|---|---|---|
| MAJOR/ALPHA/CELLO/X3/PIANO XL HDD | 143 | by year and month, 2015 to 2026 |
| FLUTE/PIANO V1.5/PIANO XL SD/PK10 | 32 | by volume |
| KS-100 MINIBOX / KS-10 MINI SD | 18 | by volume |
| **REYNA SERIES** | **43** | by volume, 62 to 108 |
| T-X SERIES | 47 | by volume |
| KS-40 / KBOX-2 / KBOX-3 | 31 | by volume |
| KS-5 / JUNIOR LITE / KS-10 / JUNIOR 2 | 26 | by volume |
| BMB / X2 / X1 / HDD | 25 | by year and month, 2018 to 2020 |
| HERMOSA / N20 NANO PLUS | 6 | by volume |
| HOME 40 / NANO OLD | 7 | by volume |
| BRAVO | 6 | by volume |
| P-SERIES | 9 | by volume |

Only the Reyna section has been verified link by link so far. The other sections are inventoried, not verified (milestone M4).

## Reyna section: discovered volumes (Source A)

43 links; all 43 returned a PDF. Volumes **97 and 107 are not listed** in A, B or C. B lists 42 (no Vol 108); C lists 35 (Vol 62 to 98). Every link on B and C is also on A, so B and C contribute **no unique Reyna documents**. The full per-document table (URL, size, SHA-256, pages, header text) is in the JSON file above.

## Provenance rules for the pipeline

- Record the exact URL found on the source page; never construct URLs from volume numbers.
- Record source page, discovery date, document SHA-256 and size for every document.
- Treat B and C as cross-checks. Canonical document identity is the MediaFire file id plus content hash.
