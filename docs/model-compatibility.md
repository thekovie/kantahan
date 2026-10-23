# Model compatibility

Which song-list volumes belong to which machine. **Only evidenced mappings are recorded; everything else is "unknown".** The app must not claim a song is available on a machine because it appears in another Platinum catalog. Audit date: 2026-10-23. Background: [source-audit.md](source-audit.md) section 5.

## Model families named by Source A

MAJOR/ALPHA/CELLO/X3/PIANO XL HDD, FLUTE/PIANO V1.5/PIANO XL SD/PK10, KS-100 MINIBOX / KS-10 MINI SD, REYNA SERIES, T-X SERIES, KS-40 / KBOX-2 / KBOX-3, KS-5 / JUNIOR LITE / KS-10 / JUNIOR 2, BMB / X2 / X1 / HDD, HERMOSA / N20 NANO PLUS, HOME 40 / NANO OLD, BRAVO, P-SERIES.

## Reyna variants (Source D product names)

Reyna, Reyna 2, Reyna 3C, Reyna SE (grouped as "Reyna /2/3C/SE") and Reyna 3 / Reyna 4 (grouped as "Reyna 3/4") are sold with **separate song volumes** for Vol 100, 101, 102, 103, 105 and 108. They are different song lists. Whether earlier volumes differ between the groups is **unknown**.

## Evidence table: Source A "REYNA SERIES" documents

| Volumes | Self-declared on page 1 | Mapping to a Reyna variant | Status |
|---|---|---|---|
| 62 to 76 | "For Reyna" (Vol 66 "For Reyna DVD") | Reyna family; variant (2/3C/SE vs 3/4) not stated | Family evidenced, variant **unknown** |
| 77 to 81 | "T-X-R-BMB Series" | Not stated | **Unknown** |
| 82 to 94 | "Volume N" only | Not stated | **Unknown** |
| 95 | "SD SERIES" | Not stated | **Unknown** |
| 96 to 108 | "T-X Series" (+ "K-Box Series V. N") | T-X and K-Box, not Reyna | **Not Reyna evidence** |

## What the importer did with the evidence (M1, run locally on 2026-10-23)

Page-1 headers were classified automatically. 14 releases (Vol 62 to 76) are `mapped` to the single `reyna` model (3,216 rows); 29 are `held` (9,273 rows) and are never built. Mapped releases do not say which Reyna variant they target, so the model is "Reyna (variant not specified)".

## Rules for the importer

- A document is associated with a model only through an explicit evidence row (`release_model.evidence`), never through the section it was found in.
- Unknown mappings are imported as quarantined or held back; they are not shown in the app.
- Song numbers keep their per-model meaning: the same number in two model families is two different entries.

## Open questions (need owner or vendor input)

1. Which published volumes map to Reyna 2/3C/SE and which to Reyna 3/4?
2. ~~What do the Source D product descriptions say?~~ Read on 2026-10-23 (fetched slowly, one page every 45 s, five pages, no rate limiting): the pages only list "Featured Songs" and a price (PHP 595 to 750). They name no compatible models beyond the product title, and say nothing about song numbering. **For Vol 100 and Vol 108 the Reyna /2/3C/SE, Reyna 3/4 and T-X Series pages list identical featured songs**, and the Vol 108 featured songs are in the free Vol 108 PDF. That suggests the three families carry the same songs for those volumes, but not that they share song numbers. The mapping rules are unchanged.
3. Is the T-X-R-BMB generation (Vol 77 to 81) usable on Reyna machines?
