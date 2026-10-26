# 0010: Merged rows in the all-machines view

Status: accepted, 2026-10-26. Amends [0007](0007-all-machines-view.md).

## Context

ADR 0007 made the all-machines view show every machine's entry as its own row and never merge. On the real catalog that is about 78,000 rows for about 16,500 distinct songs, and a typical song is listed on 6 machines, so a search for a title or a number showed the same song up to nine times. The owner asked to eliminate or lessen the duplicates.

Measured on the published catalog (read-only): rows with the same song and the same number on several machines collapse from 78,141 to about 18,000 (77% fewer), and 93% of songs use one number on every machine. A number used on several machines is the same song on all of them in 11,233 of 13,376 cases and different songs in 2,143, so merging by number alone would be wrong. Looser title matching ("feat.", "the", brackets) adds only 2% and risks wrong merges.

## Decision

- **A row is merged only when title, artist and number are all the same** (compared after folding case, accents, apostrophes and punctuation). A withheld artist matches only another withheld artist with the same title and number.
- **Nothing is dropped.** A merged row names every machine that has it. The same song under different numbers stays separate rows (one per number), and the same number for different songs stays separate rows, each with its own machines. Leading zeros are part of the number.
- **Display only.** The published bundles, the manifest and the database stay strictly per machine. `src/lib/merge.ts` builds the list in the browser from the per-machine bundles.
- **The row** shows the number at the end, and under the artist a few line-colour dots and the first two machine names, then "and N more". Screen readers get the full list. Opening the row shows a number sheet with an ink sign ("For N machines") and every machine by name. A merged row has no volume (volumes differ by machine); a row with one machine keeps today's sheet.
- **The repository rule** "never deduplicate across models" now reads: the data is never merged; only this view groups identical song and number, and never drops a machine.

## Consequences

- On the real catalog, 78,141 entries show as 17,984 rows; "ordinary people" shows 3 rows (3 numbers) instead of about a dozen. A search by number returns one row.
- The merge takes under 100 ms on a desktop and the index build about 125 ms, so the first load of the all view is not noticeably slower.
- A row's count of machines is not a claim that the song exists only there: songs missing from a machine's published lists are simply not shown for it (see data-review.md).
