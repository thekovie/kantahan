# Design and brand

> **Status: brand identity and the app UI are done (the UI was rerolled on 2026-10-24).** This page records the decisions; the shipped design system is described in [DESIGN.md](../DESIGN.md) and the direction in [ADR 0006](decisions/0006-wayfinding-ui.md).

## Direction: "Metro Wayfinding"

Calm, clean and readable. The look is clean wayfinding signage: each machine model is a coloured **line**, and the **song number** is a heavy plain figure at the end of every ruled row. Light is the first design and dark follows the phone. Colour does jobs (the model line, selection, state) instead of filling the screen. Decision and alternatives: [ADR 0006](decisions/0006-wayfinding-ui.md). The earlier "Videoke Night" look is superseded.

## Brand tokens (AA contrast of every text and background pair is asserted in `apps/web/src/theme.contrast.test.ts`)

| Token | Light | Dark | Use |
|---|---|---|---|
| Wall (`--bg`) | `#F4F6F9` | `#0E141B` | page |
| Sign (`--surface`) | `#FFFFFF` | `#17202A` | fields, chips, sheets |
| Ink (`--text`) | `#0B1B2B` | `#EEF3F8` | text, selection fill |
| Sign ink (`--brand`) | `#0B1B2B` | `#EEF3F8` | logo badge, primary button, focus ring |
| Line red / blue / teal / orange / green / yellow | `#C8281C` `#0057B8` `#00786F` `#B84A0C` `#00794F` `#FFC20E` | `#FF7A6E` `#7DB3FF` `#3DD6C8` `#FFA35C` `#55D68F` `#FFD23F` | one per machine model |

The catalog names a model's colour magenta, violet, aqua, orange, lime or yellow. Those names are data, so they stay; CSS draws them as the six line colours above.

Color is never the only carrier of meaning: the selected model is a line sign with its **name written out**, and model chips carry the name too.

## Logo

A handheld dynamic microphone whose round ball head is also a magnifying lens (songs are found by searching), on a yellow disc that stays visible on light and dark headers. The handle is banded in three line colours (red, yellow, teal). It replaces the earlier "K with mic" tile ([ADR 0002](decisions/0002-brand-identity.md)), which looked too much like the owner's own website. It carries no letter K, so the wordmark does the naming. See [ADR 0006](decisions/0006-wayfinding-ui.md).

| File (`apps/web/public/brand/`) | Use |
|---|---|
| `logo.svg` | master mark |
| `favicon.svg`, `favicon-32.png`, `favicon-16.png` | browser tab (heavier strokes, no grille lines, for small sizes) |
| `icon-192.png`, `icon-512.png` | PWA icons |
| `maskable.svg`, `maskable-512.png` | PWA maskable icon, content inside the central safe zone |
| `apple-touch-icon.png` | iOS home screen (180 px, full bleed) |
| `mask-icon.svg` | monochrome mark for pinned tabs |
| `og.png` | 1200x630 social preview |

The PNGs were rendered from the SVGs with headless Chrome. Usage rules: keep clear space of at least a quarter of the tile width, do not recolor or rotate the mark, and never combine it with Platinum Karaoke or Vismay names or marks.

## UI constraints (all met in M2)

- Mobile first; touch targets at least 48 px with 8 px gaps; body text at least 16 px.
- AA contrast (4.5:1 text, 3:1 large text and UI parts) in light and dark.
- Respect `prefers-reduced-motion`; animate transform and opacity only.
- Fonts self-hosted (offline PWA, no third-party requests); display face for brand and numbers with tabular figures, plain legible face for body. Atkinson Hyperlegible Next (body) and Barlow Semi Condensed Bold (wordmark and song numbers), both under the SIL OFL (Barlow's licence is in `apps/web/src/assets/fonts/`).
- A standalone outlined wordmark SVG is still deferred; the app sets the wordmark in Barlow Semi Condensed.
