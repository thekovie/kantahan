# 0003: M2 interface direction

Status: accepted, 2026-10-23

## Context

The brief asks for a mobile-first songbook that is colorful and not boring, readable across a room, accessible, and quiet in motion. The owner asked for the UI/UX skills to be consulted. The app is a task tool (Operate mode), so expression has to live in a few precise details, not in decoration.

## Decision

- **One memorable thing: the LED number token.** The song number is the product. It is set in a seven-segment face (DSEG7) in the model's hue on a dark tile, with faint unlit segments behind the digits and leading zeros kept. Everything else stays calm.
- **Index structure from the printed songbook**: browse by letter with a strip of 48 px tabs, plus search. Search is the primary path; the letter strip is the book-index alternative.
- **Full-size read-out**: tapping a row opens a native `<dialog>` where the number fills the dialog width (container query units), readable from across a room.
- **Palette "Videoke Night"** (see [design.md](../design.md)): Stage Indigo ground in dark, Fiesta Blush in light, Mic Magenta header, Sunbeam Yellow for the selected letter, Aqua focus ring. Each model family keeps one hue and always its name; color is never the only signal.
- **Type**: Atkinson Hyperlegible Next for body, Fredoka for the wordmark, DSEG7 for numbers only. All self-hosted (offline, no third-party requests).
- **Refused**: eyebrow labels, gradient text, glass effects, colored side borders, emoji icons, decorative motion. The only authored motion is the digit light-up on the read-out, off under reduced motion.
- **Demo flag**: the synthetic catalog is marked by a "Demo" pill in the header, which does not shift the layout.

## Process and evidence

PRODUCT.md written; a design-direction seed and surface brief (`.impeccable/surfaces/`) fixed the direction before building; two screenshot rounds (mobile and desktop, both themes, three models); an independent finish review found six material issues and one regression, all fixed (eyebrow label, read-out scale, desktop composition, other-model captures, chip alignment, hue in the shell, desktop read-out size, wrapped meta line, layout shift). Mechanical detector clean; axe clean in both themes; Lighthouse mobile accessibility 100.

## Consequences

Number tokens depend on DSEG7 being present; if the font fails to load the digits fall back to a monospace face and remain readable. Desktop uses a wider two-column list rather than a different layout.
