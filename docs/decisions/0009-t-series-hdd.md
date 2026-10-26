# 0009: T-Series HDD is its own machine

Status: accepted, 2026-10-26. Amends [0004](0004-machine-group-models.md).

## Context

ADR 0004 made each machine group the publisher names on its song list page one model. The publisher lists several product lines inside its "T-X SERIES" section. The data review ([data-review.md](../data-review.md)) found that two documents, Volumes 58 and 60, say "For T-Series, HDD" in their own page header, while Volumes 63 to 76 say "T-Series DVD". Their numbers overlap (15700 to 15904): 205 numbers meant one song in the HDD volumes and another in the DVD volumes. With everything in one model those numbers conflicted and were left out of the catalog (about 410 songs).

## Decision

- A new model, **T-Series HDD**, holds documents listed under T-X SERIES whose own header says "T-Series, HDD". It is decided by the document's header (`classify.py` records the family `t-series-hdd`), in the same spirit as the Reyna rule: what the document says about itself wins over where it is listed.
- `mapping.HEADER_SPLITS` records the rule. When a document under T-X SERIES has that header family, it joins `t-series-hdd` instead of `t-x`, and an earlier mapping to `t-x` is removed (the one place a mapping is replaced).
- Migration `0006_t_series_hdd` adds the model. Existing databases get the change by re-importing and mapping (`import --reimport --section all`, `map`), then publishing with `--allow-drop` because T-X shrinks by 3% (the publish gate allows 2%).
- The name comes from the documents' own header text. The hue is only a helper; the name is always shown.

## Consequences

- The 205 clashing numbers are no longer left out. T-Series HDD has 882 songs; T-X goes from 13,706 to 13,242 because the songs of the two HDD volumes now live in their own machine.
- A person with a T-Series HDD machine now has their own list. Whether the other T-X volumes (24 to 30, 77 to 81, 82 to 108) are right for one machine remains the publisher's statement (unchanged from ADR 0004).
- Other splits follow the same table: add the pair of section and header family to `HEADER_SPLITS`, a model, and a display entry.
