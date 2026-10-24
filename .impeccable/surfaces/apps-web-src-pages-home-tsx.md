---
version: 1
slug: "apps-web-src-pages-home-tsx"
primary_target: "apps/web/src/pages/Home.tsx"
related_targets: []
---

# Surface brief: Kantahan songbook (whole app UI, replacement)

Mode: Operate. Replaces the "Videoke Night" look (pink-purple, LED scoreboard numbers); the owner rejected both. Owner answers: calm and clean; bold plain song numbers; light first, dark follows the phone.

Job: someone holding a phone in a living room finds the right song number in seconds and keys it into the machine. Success is reading the number.

Kept untouched: all behaviour, copy, legal wording, data contract (model hue names stay magenta/violet/aqua/orange/lime/yellow in the manifest; they are remapped to new line colours in CSS only).

Open decisions: none. Logo is redone in the new palette (owner default).

## Direction contract

THESIS: A songbook as metro wayfinding. Each machine model is a coloured "line"; every song number is a plain, heavy station number. It refuses the scoreboard, the dark-neon karaoke look and the card-per-row list.

OWN-WORLD: Light-first signage. Cool off-white wall (#F4F6F9), white sign surfaces, ink #0B1B2B, signage blue #0057B8 as brand, six line colours (red, blue, teal, orange, green, yellow) each paired with a text colour that passes AA. Dark is a deep blue-black wall (#0E141B) with lighter line colours. Atkinson Hyperlegible Next for reading; Barlow Semi Condensed bold for the wordmark and every song number. Flat fills, hairline rules, no glow, no gradients, no card shadows.

STORY: Pick the machine (line), type a title, artist or number, scan a ruled list, read the number at the right edge of the row, tap for the big read-out sign.

FIRST VIEWPORT: Slim white header with the wordmark and menu. Below it the line bar: a flat full-width bar in the selected model's colour with a round line badge and the model name and coverage. Under it the model chips (when more than one), then a tall search field, then the alphabet strip. Rows are ruled, not boxed: title and artist left, the song number right, heavy, tabular, about 2rem.

FORM: Metro Wayfinding, the owner-chosen pick card (not the dice roll), seed key baead816.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
