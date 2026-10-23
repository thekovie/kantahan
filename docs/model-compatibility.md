# Model compatibility

> **Rule since M4 (owner decision 2026-10-24, [ADR 0004](decisions/0004-machine-group-models.md)):** each Source A section is a model, and a volume belongs to every section that lists it, recorded as "listed under ... on the publisher's page". **Reyna is the exception** and keeps the header rule below.

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

## Machine groups (M4, run locally on 2026-10-24)

All 393 Source A links were fetched and imported (363 files; 295 distinct documents by hash, because the same file is often linked from several sections). 12 models, one per publisher section:

| Model (publisher section) | Releases | Songs in bundle | Left out as conflicting | Notes |
|---|---|---|---|---|
| Reyna | 14 | 3,186 | 0 | header rule, Vol 62 to 76 only |
| T-X | 47 | 13,706 | 205 | Vol 24 to 108 |
| Flute / Piano V1.5 / Piano XL SD / PK10 | 32 | 8,821 | 183 | Vol 24 to 108 (shares files with T-X) |
| Major / Alpha / Cello / X3 / Piano XL HDD | 140 | 12,875 | 5 | monthly lists, 2015 to 2026 |
| KS-40 / KBOX-2 / KBOX-3 | 31 | 11,341 | 0 | Vol 2 to 35 |
| KS-5 / Junior Lite / KS-10 / Junior 2 | 26 | 10,265 | 0 | Vol 2 to 35 |
| KS-100 Minibox / KS-10 Mini SD | 18 | 4,837 | 2 | Vol 18 to 35 |
| BMB / X2 / X1 / HDD | 25 | 2,159 | 0 | monthly lists, Dec 2018 to Dec 2020 |
| Hermosa / N20 Nano Plus | 6 | 3,319 | 0 | Vol 2 to 9 |
| Home 40 / Nano Old | 7 | 3,342 | 1 | Vol 61 to 77 |
| P-Series | 9 | 2,505 | 13 | Vol 53 to 78 |
| Bravo | 6 | 1,785 | 0 | Vol 4 to 9 |

Observations:

- The same file is listed under several groups (for example "T-X Series V.106 / K-Box V.33" under Reyna, T-X, Flute/Piano and KS-40). Under the Reyna decision it joins T-X, Flute/Piano and KS-40, but not Reyna.
- Most headers name no machine. Headers that do: "For Reyna" (Vol 62 to 76), "For P-Series" (Vol 69 to 76), "T-X Series", "SD Series", "KS-Series", "K-Box Series".
- **Conflicts.** With many volumes per model, a song number sometimes means different songs (T-X Vol 60 and Vol 65 at 15858) or has revised wording ("Muli v.86" and "Muli"). Such numbers are left out of the bundle, and a model publishes only if they are at most 5% of its numbers (the app shows the count). A number with the same title but different artist text keeps the song and withholds the artist.
- **Not imported (3 documents):** HDD "2015 October" and "2015 November" (song numbers of only 3 or 4 digits in the source) and HDD "2021 March" (one number listed twice with different text). They stay quarantined.
- **Blank artists.** The "Kid Songs" tables (Bravo Vol 8, P-Series Vol 73) leave the artist cell empty in the source; they are accepted through `catalog/reviewed.yaml`, which names each file a person checked.
- **Not evidence of machine compatibility:** nothing here says which individual machine in a group can use a list.

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
