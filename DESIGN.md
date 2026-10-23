---
name: Kantahan
description: A songbook you can read in the dark. Videoke night in type, palette and one move, the LED song number.
colors:
  stage-indigo: "#1b1038"
  indigo-surface: "#261650"
  indigo-surface-2: "#33206b"
  indigo-line: "#4b3a83"
  indigo-line-strong: "#9a86d6"
  marquee-white: "#f8f3ff"
  lavender-mist: "#cdbff0"
  mic-magenta: "#c4006d"
  sunbeam-yellow: "#ffc93c"
  aqua-glow: "#3de0f5"
  tile-black: "#12091f"
  led-magenta: "#ff4fb0"
  led-violet: "#b79bff"
  led-aqua: "#3de0f5"
  led-orange: "#ff9f43"
  led-lime: "#a6f04a"
  led-yellow: "#ffd84d"
  fiesta-blush: "#fff0f7"
  blush-surface-2: "#ffe1ef"
  blush-line: "#e4c3d6"
  blush-line-strong: "#7a5c93"
  blush-text-muted: "#55447f"
  blush-focus-violet: "#5b21b6"
typography:
  wordmark:
    fontFamily: "Fredoka, Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    letterSpacing: "0.01em"
  title:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.2
  headline:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
  body:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  row-title:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.3
  label:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
  led-digits:
    fontFamily: "DSEG7, ui-monospace, monospace"
    fontSize: "1.625rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.06em"
rounded:
  sm: "6px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  sheet: "28px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  target: "48px"
components:
  header:
    backgroundColor: "{colors.mic-magenta}"
    textColor: "#ffffff"
    padding: "8px 8px 8px 16px"
  button-primary:
    backgroundColor: "{colors.mic-magenta}"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "0 24px"
    height: "56px"
  chip:
    backgroundColor: "{colors.indigo-surface}"
    textColor: "{colors.marquee-white}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "48px"
  chip-selected:
    backgroundColor: "{colors.led-magenta}"
    textColor: "{colors.stage-indigo}"
  search-field:
    backgroundColor: "{colors.indigo-surface}"
    textColor: "{colors.marquee-white}"
    rounded: "{rounded.lg}"
    height: "56px"
  letter:
    backgroundColor: "{colors.indigo-surface}"
    textColor: "{colors.marquee-white}"
    rounded: "{rounded.md}"
    size: "48px"
  letter-selected:
    backgroundColor: "{colors.sunbeam-yellow}"
    textColor: "{colors.stage-indigo}"
  song-row:
    backgroundColor: "{colors.indigo-surface}"
    textColor: "{colors.marquee-white}"
    rounded: "{rounded.lg}"
    height: "72px"
  led-tile:
    backgroundColor: "{colors.tile-black}"
    textColor: "{colors.led-magenta}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    typography: "{typography.led-digits}"
  readout:
    backgroundColor: "{colors.indigo-surface}"
    textColor: "{colors.marquee-white}"
    rounded: "{rounded.sheet}"
    padding: "24px"
---

# Design System: Kantahan

## Overview

**Creative North Star: "Videoke Night"**

A songbook you can read in the dark. Videoke night is taken only as palette, type, density and one move: the LED song number. The ground is Stage Indigo, the shell is Mic Magenta, and the number is the product, so every result is led by a seven-segment numeral on a dark tile while the rest of the screen stays calm and complete. Dark is the default because people use it in a dim room; the light theme, Fiesta Blush, keeps the same hues darkened for contrast.

Density is phone-first and thumb-sized: 48px minimum targets, one column at rest, two result columns on wide screens. No texture, no ornament, no decorative imagery. Colour always has a job: shell, selection, focus, or the model family a number belongs to.

**Key Characteristics:**
- Dark default, light Fiesta Blush alternative, switched by `data-theme="light"` on the root.
- Song numbers in DSEG7 on a tile that is dark in both themes, with unlit "ghost" segments behind the lit digits.
- Colour carries meaning: magenta shell, yellow selection, aqua focus, family hue per machine model.
- Hyperlegible body face, rounded wordmark face, digit face reserved for numbers.
- A "Demo" pill in the header marks the synthetic catalog.

## Colors

A deep indigo night with one hot magenta shell and a small set of LED hues that identify machine models.

### Primary
- **Mic Magenta** (#c4006d): the header bar, primary buttons (white text), accent-color and text selection. Same value in both themes.

### Secondary
- **Sunbeam Yellow** (#ffc93c): the selected letter on the alphabet rail and the caret, with Stage Indigo text. In light theme the selection inverts to Stage Indigo with Sunbeam text (#ffd84d).
- **Aqua Glow** (#3de0f5): the focus ring in dark theme (3px, 3px offset). Light theme uses Blush Focus Violet (#5b21b6).

### Tertiary (model family hues)
- **LED Magenta** (#ff4fb0), **LED Aqua** (#3de0f5), **LED Lime** (#a6f04a): the hues in use for model families; **LED Violet** (#b79bff), **LED Yellow** (#ffd84d) and **LED Orange** (#ff9f43) are defined and ready. A hue colours the number digits, the model chip when selected, the read-out border, and the short rule under the index heading.

### Neutral
- **Stage Indigo** (#1b1038): page ground. **Indigo Surface** (#261650) and **Indigo Surface 2** (#33206b): rows, fields, hover. **Indigo Line** (#4b3a83) hairlines; **Indigo Line Strong** (#9a86d6) control borders.
- **Marquee White** (#f8f3ff) text; **Lavender Mist** (#cdbff0) secondary text.
- **Tile Black** (#12091f): the LED tile, in both themes.
- Light: **Fiesta Blush** (#fff0f7) ground, white surfaces, **Blush Surface 2** (#ffe1ef), **Blush Line** (#e4c3d6), **Blush Line Strong** (#7a5c93), **Blush Text Muted** (#55447f), text Stage Indigo.

### Named Rules
**The Number Carries Colour Rule.** Hue is spent on song numbers and the model that owns them. Chrome stays indigo, magenta or neutral.
**The Contrast Pair Rule.** Every text and background pair is checked in `theme.contrast.test.ts`; change a token and its test together.

## Typography

**Display Font:** Fredoka (wordmark only; self-hosted variable, with Atkinson fallback)
**Body Font:** Atkinson Hyperlegible Next (400, 600, 700; with system-ui fallback)
**Digit Font:** DSEG7 Classic Bold (song numbers only)

**Character:** A rounded, friendly wordmark over a hyperlegible humanist sans, with a seven-segment display face that appears only where a number is read.

### Hierarchy
- **Wordmark** (Fredoka 600, 1.5rem): the header brand.
- **Title** (600, 1.5rem, 1.2): the read-out song title.
- **Headline** (600, 1.25rem): index heading, state headings, prose h2. Prose h1 is 1.875rem / 1.15.
- **Body** (400, 1rem, 1.5): default; prose capped at 65ch.
- **Row title** (600, 1.0625rem, 1.3) over **artist** (400, 0.9375rem, Lavender Mist).
- **Label** (600-700, 0.8125-0.9375rem): chips, buttons, badge, status line.
- **LED digits** (DSEG7 700, 1.625rem in rows, 2rem at 64rem+, up to 11rem in the read-out, letter-spacing 0.06em).

### Named Rules
**The Digits Only Rule.** DSEG7 is for song numbers. Never set words in it.
**The Leading Zero Rule.** Numbers are strings; render every digit given.

## Layout

A single centred column: 42rem by default, 56rem from 48rem with results in two columns, 64rem from 64rem with 2rem row tokens and 5rem rows. Header bar, main and footer share the same max width. Side padding is 1rem; the model chips and letter rail scroll horizontally with snap and bleed to the screen edge. Rhythm is 0.5rem between rows, 0.75rem to 1.25rem between blocks. Safe-area insets are respected at the top and bottom. Read-out dialog: `min(92vw, 44rem)`, max height 92dvh.

## Elevation & Depth

Flat and tonal: depth comes from surface steps (ground, surface, surface 2) and 2px borders, not shadows. The only shadow is the open menu panel (`box-shadow: 0 12px 28px rgb(10 4 24 / 0.35)`). The read-out sits over a scrim (`rgb(10 4 24 / 0.7)` dark, `rgb(27 16 56 / 0.6)` light).

### Named Rules
**The Flat Rows Rule.** Rows, chips and fields have no shadow at rest or on hover; hover shifts to Surface 2.

## Shapes

Generously rounded and thumb-friendly. Radii: pills (999px) for chips and badge; 12px for LED tiles, letters and menu links; 14-16px for rows, fields, buttons; 20px for the large LED tile and state panels; 28px for the read-out sheet. Controls use 2px Line Strong borders. Focus uses a 3px ring with 3px offset.

## Components

### Header and menu
Magenta bar with the K logo (36px, 9.6px radius), Fredoka wordmark, "Demo" pill (1.5px outline, bold) and a menu button. Menu panel: Surface, 2px Line Strong border, 16px radius, 48px links; hover and current page use Surface 2. Icon buttons are 48px with a translucent white hover.

### Model chips
48px pills in a scroll rail. Unselected: Surface, Line Strong border, a small dot in the family hue. Selected: filled with the family hue, Stage Indigo text, dot hidden.

### Search field
56px, 16px radius, 2px Line Strong border, 1.125rem text, left icon, 48px clear button.

### Letter rail
48px squares with 14px radius. Selected letter is Sunbeam Yellow with Stage Indigo text.

### Song row
Grid of LED tile then title above artist; Surface, 16px radius, min 72px (80px wide). Press scales to 0.985.

### LED number token (signature)
Tile Black tile, DSEG7 digits in the family hue, unlit segments drawn as 13% opacity generated content. Digits light up on open with a 260ms staggered fade.

### Read-out dialog
Native dialog; Surface, 28px radius, 2px border in the family hue. The number fills the width: size is `min(11rem, (100cqw - 2.5rem) / (digits * 0.9 + 0.3))` via container query units. A full-width magenta button closes it. Entry 200ms ease-out; all motion is removed under reduced motion.

### States and buttons
Primary button is magenta, 56px, 16px radius, bold white text. State panels are Surface cards with a centred heading and muted copy; loading uses pulsing Surface skeleton rows.

## Do's and Don'ts

### Do:
- **Do** keep every target at least 48px and every text pair AA.
- **Do** show the model, coverage and source near the results.
- **Do** underline links inside running text.
- **Do** give each machine model family one LED hue and use it consistently across chip, digits and read-out border.
- **Do** keep the LED tile dark in both themes.

### Don't:
- **Don't** use DSEG7 or the LED tile for anything but song numbers.
- **Don't** add shadows to rows, chips or fields.
- **Don't** put gradient text, glass, coloured side stripes, textures or emoji icons on any surface.
- **Don't** use a one-colour accent: selection, focus and shell each have their own hue.
- **Don't** animate layout properties; use opacity and transform, and honour reduced motion.
