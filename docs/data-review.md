# Data review (2026-10-26)

> **Status: done once, repeatable.** Written after the owner noticed a missing song ("My Way" by Sinatra) and asked for a review of the parser. Numbers are measured on the real documents (363 files, 1,047 pages) and on the published catalog (v1). No catalog data is stored here, only counts and the kinds of defects.

## What was checked, and how

| Check | Method |
|---|---|
| Is anything lost while reading the PDFs? | Ran the extractor over all 363 files and counted number-like tokens that landed outside every table ("stray" tokens). |
| Is a song missing from the sources? | Searched the text of all 363 files (and the published catalog) for the title and artist. |
| Which songs are left out on purpose? | Classified every number that two volumes list with different titles ("conflicts"). |
| Which documents are held back? | Read the quarantine records and re-read those documents. |
| Is text read into the wrong cell? | Compared every published row with a fresh re-import of the same documents, and checked artists against the same song on other machines. |

## Findings

| # | Finding | Size before | Fix |
|---|---|---|---|
| 1 | Nothing is lost while reading: all files read, 81,615 rows, 19 stray tokens (one page-furniture token per document). | none | none needed |
| 2 | **"My Way" by Sinatra is not in any published list.** The sources are incremental update lists; the base catalog on the machine was never published (see [source-audit.md](source-audit.md), section 4). | n/a | Not fixable with official sources. The app says earlier songs are not included. Owner decision: no unofficial sources. |
| 3 | **Column headers read as part of a title or artist** ("Song Title Jail House Rock", "Popularized By: Don Moen"). The header sits 0.8 to 0.9 of a row above the first row of a table, and again at the start of each regional section, inside the reach that assigns words to rows. These songs also sorted under S when browsing. | 406 titles, 34 artists | `extract.py` drops header words that sit away from every row. A validator rule now blocks a document where more than two rows start with header text. |
| 4 | **Version marks in titles** ("How To Love v.86", "Never v.87 Bed"): the publisher marks songs a volume carries over. A conflict with the unmarked spelling dropped the number. | 212 titles, 183 numbers dropped (Flute/Piano) | `normalize.strip_version_marks` removes the lowercase `v.NN` mark when reading titles. |
| 5 | **Tightly spaced lines of one title were treated as two cells printed on top of each other.** Lines of a wrapped title overlap by about 16% of a word; real collisions overlap by about 80%. The threshold was 5%, so the first line of such a title was given to the row above. | 1,802 titles cut short, 100 with a neighbour's words, 1,695 artists wrong, 451 artists withheld | Threshold raised to 35% (`OVERLAP_FRACTION`). After the fix 430 withheld artists are known (375 confirmed by the same song on other machines) and 21 stay withheld. |
| 6 | **Whole documents quarantined for a few odd rows**: HDD 2015 October (4 numbers of 4 digits), 2015 November (8 numbers of 3 to 4 digits), 2021 March (one number printed twice with different songs). | 275 songs held back | A few odd rows (at most 20 and 10%) are set aside and reported (`SET ASIDE` lines, never padded or guessed); the rest of the document imports. Many odd rows still quarantine the document. |
| 7 | **T-X mixes two products.** Volumes 58 and 60 say "For T-Series, HDD"; Volumes 63 to 76 say "T-Series DVD". Their numbers overlap (15700 to 15904), so 205 numbers conflicted and were left out. | 205 numbers (about 410 songs) | New machine **T-Series HDD** for documents whose own header says so ([ADR 0009](decisions/0009-t-series-hdd.md)). |

## Result

Rebuilt from the same 363 documents (local run, nothing deployed):

| Machine | Songs before | Songs after | Numbers left out before to after |
|---|---|---|---|
| Reyna | 3,186 | 3,186 | 0 to 0 |
| T-X | 13,706 | 13,242 | 205 to 0 |
| T-Series HDD (new) | none | 882 | none |
| Flute / Piano / Piano XL SD / PK10 | 8,821 | 9,004 | 183 to 0 |
| Major / Alpha / Cello / X3 / Piano XL HDD | 12,875 | 13,140 | 5 to 0 |
| KS-40 / KBOX | 11,341 | 11,341 | 0 to 0 |
| BMB / X2 / X1 / HDD | 2,159 | 2,159 | 0 to 0 |
| KS-100 / KS-10 Mini SD | 4,837 | 4,837 | 2 to 2 |
| KS-5 / Junior | 10,265 | 10,265 | 0 to 0 |
| Hermosa / N20 Nano Plus | 3,319 | 3,322 | 0 to 0 |
| Home 40 / Nano Old | 3,342 | 3,342 | 1 to 1 |
| Bravo | 1,785 | 1,785 | 0 to 0 |
| P-Series | 2,505 | 2,524 | 13 to 3 |
| **Total** | **78,141** | **79,029** | |

- Titles starting with column header text: 406 to 0. Titles with a version mark: 212 to 0. Documents in quarantine: 3 to 0.
- Of the songs present both before and after, 75,135 are identical; 434 differ only by the removed header text or version mark; 1,902 titles were repaired (every one either gained the words that had been cut off, or lost words that belonged to a neighbour; none changed to a different song).

## What is still not perfect

- **Songs only on the machine's base catalog are not in the app** (finding 2). This is a source limit, not a bug.
- **Six numbers are still left out** because two volumes spell the title differently (a subtitle, or a title cut at a line break): P-Series 11550, 11560 and 15074, KS-100 41403 and 41452, Home 40 15482. Leaving them out is the safe choice.
- **Long artist names that wrap over three lines are sometimes cut or run together** ("Rita Ora ft. Cardi B, Bebe Rexha Charli", "Maroon & 5 ft Cardi"). This was already true before; it is now rarer because fewer artists are withheld. Reporting a wrong entry goes through the Rights and removal form.
- **Numbers that are not five digits** in the 2015 HDD lists (12 rows) are set aside, not guessed.

## Repeating the review

Run the extractor over all documents and compare against the published catalog: counts per machine, rows that start with column header text or end with a `v.NN` mark, numbers left out and why, quarantined documents, and artist agreement with the same song on other machines. The steps used here are in this file; the code is in `catalog/` (`extract.py`, `validate.py`, `normalize.py`, `mapping.py`) with tests in `catalog/tests/`.
