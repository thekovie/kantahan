# 0002: Brand identity: K with mic, "Videoke Night" palette

Status: Accepted (2026-10-23)

## Context

The app needs an independent, colorful identity (not boring), a logo and icon set, and no resemblance to Platinum Karaoke or Vismay marks. The mark must work as a PWA icon, favicon (16 px) and maskable icon.

## Decision

Three SVG concepts were drawn and compared at 256 down to 16 px on light and dark backgrounds: (A) a number ticket with a hash sign, (B) a K whose arm ends in a mic head, (C) a speech bubble with a music note. The owner chose **B**. Palette: Mic Magenta, Stage Indigo, Sunbeam Yellow, Aqua Glow, Lime Pop, Fiesta Blush (see [design.md](../design.md)).

Alternatives: A reads as a hashtag at small sizes; C is weak below 32 px and less distinctive.

## Consequences

- Assets live in `apps/web/public/brand/` and are the single source for icons and the social image.
- Contrast of every text and background pair is verified when the UI is built (M2); the white-on-magenta pair of the logo itself is decorative.
- The wordmark is deferred until the display font is chosen.
