---
version: 1
slug: "apps-web-src-app-tsx"
primary_target: "apps/web/src/App.tsx"
related_targets: []
---

## Scope and visitor mode

Operate. The single working screen of the Kantahan PWA (Home: model, search, results, songbook index), plus three static pages (About, Privacy, Rights and Removal) that share its shell.

## Audience, job, task, constraints

People singing on a Platinum Karaoke machine, phone in one hand and microphone in the other, in a dim room, often offline. Job: find the song number and read it. Frequency: dozens of lookups per evening. Constraints: model-specific numbering, numbers are strings with leading zeros, honest coverage (volumes we have), credit the source, no queueing or accounts, AA contrast, 48 px targets, reduced motion. Real catalog data is local only; development uses synthetic data.

## Direction contract

THESIS: A songbook you can read in the dark. The number is the product, so every result is led by a large LED-style number token and the rest of the screen is calm and complete. Refuses the category default of a grey search box over a plain list and a one-colour accent.

OWN-WORLD: Videoke night, taken only as type, palette, density and one move. Stage Indigo ground with Mic Magenta, Sunbeam Yellow, Aqua Glow and Lime Pop doing real jobs (shell, selection, number tokens by model family, state). Seven-segment numerals (DSEG) for song numbers only, a hyperlegible humanist sans for everything else, a rounded display face for the wordmark. Light theme is Fiesta Blush with the same hues darkened for contrast. No textures, no ornament.

STORY: The visitor understands in a second that this is a songbook for their machine (the model is always visible), finds the number by typing a title, artist or number or by walking the alphabet rail, and believes it because the model, coverage and source are stated. They key the number into the remote; tapping a result opens the number at full size to read from across the room.

FIRST VIEWPORT (390 x 844): top bar with the K logo, wordmark and a menu for About, Privacy and Rights. Below it a model chooser (chips, active one filled in its family hue) and a 56 px search field with a clear button. The results area shows the songbook index when the query is empty: a letter rail down the right edge (A to Z and #), the current letter's songs as rows (number token left, title above artist), and a quiet line naming model, volume coverage and source. Typing replaces the index with ranked results. Primary action is the search field; the number tokens carry the colour.

FORM: Printed-songbook index with an alphabet rail, fused with the brief's required primary screen (model, large search, results). Position 4 of 7 grounded structures, dealt as the lead. Seed key 88caebab.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Signature move

The LED number token: every result's song number set in seven-segment numerals on a solid tile in the model family's hue, with leading zeros kept. Tapping a result opens a large "read-out" sheet with the number at monumental size.

## Unresolved decisions

Final family hues for models other than Reyna; wordmark outlining; whether the read-out sheet needs a copy button (probably not: the remote is keyed by hand).
