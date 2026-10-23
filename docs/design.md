# Design and brand

> **Status: brand identity done; the app UI is planned (milestone M2) and not built.** This page records decisions so far and the constraints the UI must meet.

## Direction: "Videoke Night"

Colorful, playful, readable. The hero element of the UI is the **song number**: large tabular digits on a chunky badge, keyed by model family; titles and artists stay quiet around it. Light and dark themes are both colorful. The look draws on the project brief (large touch targets, readable typography, accessible contrast, no unnecessary animation) and was checked against the UI/UX design guidance used for this project.

## Brand tokens (draft; AA contrast of every text pair is verified at M2)

| Token | Hex | Use |
|---|---|---|
| Mic Magenta | `#E6007E` | primary brand, logo tile |
| Stage Indigo | `#1B1038` | dark base, text on light |
| Sunbeam Yellow | `#FFC93C` | mic head, highlights |
| Aqua Glow | `#16C7E0` | accent |
| Lime Pop | `#8BD72A` | accent |
| Fiesta Blush | `#FFF0F7` | light base |

Color is never the only carrier of meaning: model families get a hue **and** their name.

## Logo

Concept B, "K with mic": a white K on a magenta rounded tile whose upper arm ends in a yellow mic head. It stays recognizable at 16 px. Chosen from three concepts (number ticket, K with mic, speech bubble with note); see [ADR 0002](decisions/0002-brand-identity.md).

| File (`apps/web/public/brand/`) | Use |
|---|---|
| `logo.svg` | master mark |
| `favicon.svg`, `favicon-32.png`, `favicon-16.png` | browser tab (slightly heavier strokes for small sizes) |
| `icon-192.png`, `icon-512.png` | PWA icons |
| `maskable.svg`, `maskable-512.png` | PWA maskable icon, content inside the central safe zone |
| `apple-touch-icon.png` | iOS home screen (180 px, full bleed) |
| `mask-icon.svg` | monochrome mark for pinned tabs |
| `og.png` | 1200x630 social preview |

The PNGs were rendered from the SVGs with headless Chrome. Usage rules: keep clear space of at least a quarter of the tile width, do not recolor or rotate the mark, and never combine it with Platinum Karaoke or Vismay names or marks.

## UI constraints for M2

- Mobile first; touch targets at least 48 px with 8 px gaps; body text at least 16 px.
- AA contrast (4.5:1 text, 3:1 large text and UI parts) in light and dark.
- Respect `prefers-reduced-motion`; animate transform and opacity only.
- Fonts self-hosted (offline PWA, no third-party requests); display face for brand and numbers with tabular figures, plain legible face for body. Final choice at M2.
- Standalone wordmark SVG is deferred until the display font is chosen, so the lettering can be outlined.
