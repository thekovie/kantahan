---
name: Kantahan
description: A songbook drawn as metro wayfinding. Each machine model is a coloured line; every song number is a plain, heavy station number.
colors:
  wall: "#f4f6f9"
  sign: "#ffffff"
  sign-2: "#e9eef4"
  rule: "#d3dbe5"
  rule-strong: "#66758a"
  ink: "#0b1b2b"
  ink-muted: "#44546a"
  error: "#b3261e"
  line-red: "#c8281c"
  line-blue: "#0057b8"
  line-teal: "#00786f"
  line-orange: "#b84a0c"
  line-green: "#4d7c0f"
  line-yellow: "#ffc20e"
  disc-yellow: "#ffc20e"
  night-wall: "#0e141b"
  night-sign: "#17202a"
  night-sign-2: "#212c39"
  night-rule: "#2a3643"
  night-rule-strong: "#7c8da1"
  night-ink: "#eef3f8"
  night-ink-muted: "#a6b5c6"
  night-error: "#ff9a93"
typography:
  wordmark:
    fontFamily: "Barlow Semi Condensed, Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "0.01em"
  song-number:
    fontFamily: "Barlow Semi Condensed, Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.02em"
    fontFeature: "tabular-nums"
  headline:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Atkinson Hyperlegible Next, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.5
rounded:
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  pill: "999px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
  tap: "3rem"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sign}"
    rounded: "{rounded.md}"
    padding: "0 1.5rem"
    height: "3.5rem"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 1.125rem"
    height: "3rem"
  search-field:
    backgroundColor: "{colors.sign}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 3.25rem"
    height: "3.5rem"
  model-chip:
    backgroundColor: "{colors.sign}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 1.125rem 0 0.875rem"
    height: "3rem"
  letter-key:
    backgroundColor: "{colors.sign}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    size: "3rem"
  letter-key-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sign}"
  line-sign:
    backgroundColor: "{colors.line-blue}"
    textColor: "{colors.sign}"
    rounded: "{rounded.md}"
    padding: "0.375rem 1rem 0.375rem 0.625rem"
    height: "3rem"
  song-row:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.5rem"
    height: "4.5rem"
  readout-sheet:
    backgroundColor: "{colors.sign}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "1.25rem 1.5rem 1.5rem"
---

# Design System: Kantahan

## Overview

**Creative North Star: "Metro Wayfinding"**

A songbook read like transit signage. Each karaoke machine model is a coloured line; the selected model is a flat bar of that colour pinned to the top of the list. Every song number is a plain, heavy station number at the right edge of a ruled row, and tapping a row opens it as a big read-out sign. Light is the first design (daylight, lit rooms); dark is a full matching version that follows the phone, for dim rooms.

The surface is calm and clean: cool off-white wall, white sign surfaces, ink text, hairline rules. Colour is reserved for the six lines and for the yellow of the logo disc. Chrome (brand, selected state, focus, primary button) is ink, so it never competes with a line colour. Depth is flat fills and rules.

**Key Characteristics:**
- Light by default, dark via `data-theme="dark"` following the phone.
- Ink is the brand: `--brand`, `--select` and `--focus` are ink in light and near-white in dark.
- One colour per model (a "line"), always paired with a written model name.
- Song numbers in Barlow Semi Condensed bold, tabular, the largest thing on any row.
- Every interactive target is at least 3rem (48px) tall; the primary button and search field are 3.5rem.
- Ruled lists, not boxed cards; flat fills; no gradients, no glow.

## Colors

A cool, near-monochrome ink-on-paper palette with six saturated line colours that appear only where a machine model is named.

### Primary
- **Signage Ink** (`ink`, #0b1b2b): Text, brand, selected state, focus ring, primary button fill. In dark it becomes `night-ink` (#eef3f8) and the on-brand text flips to ink.

### Secondary (the six lines)
Each is paired with a text colour that passes AA; the pair is set once by a `hue-*` class and read as `--hue` / `--on-hue`. The catalog's data names map to line colours: magenta is red, violet is blue, aqua is teal, orange is orange, lime is green, yellow is yellow. The data names stay in the manifest; they are drawn as line colours in CSS only.
- **Line Red** (`line-red`, #c8281c, white text; dark #e8685b with ink text).
- **Line Blue** (`line-blue`, #0057b8, white text; dark #7db3ff).
- **Line Teal** (`line-teal`, #00786f, white text; dark #3dd6c8).
- **Line Orange** (`line-orange`, #b84a0c, white text; dark #ffa35c).
- **Line Green** (`line-green`, #4d7c0f, white text; dark #a3e04a).
- **Line Yellow** (`line-yellow`, #ffc20e, ink text; dark #ffd23f). Also the logo disc (`disc-yellow`).

### Neutral
- **Cool Wall** (`wall`, #f4f6f9): page background. Dark `night-wall` #0e141b.
- **Sign White** (`sign`, #ffffff): header, inputs, chips, sheets. Dark `night-sign` #17202a.
- **Sign Tint** (`sign-2`, #e9eef4): hover fill. Dark `night-sign-2` #212c39.
- **Hairline** (`rule`, #d3dbe5): row rules, header and footer borders. Dark `night-rule` #2a3643.
- **Strong Rule** (`rule-strong`, #66758a): borders of every control (2px). Dark `night-rule-strong` #7c8da1.
- **Muted Ink** (`ink-muted`, #44546a): artist, status, hints. Dark `night-ink-muted` #a6b5c6.
- **Error** (`error`, #b3261e): invalid borders and messages. Dark `night-error` #ff9a93.

Dark tokens live under `:root[data-theme="dark"]` in `apps/web/src/index.css`; every text/background pair is contrast-tested in `src/theme.contrast.test.ts`.

### Named Rules
**The Ink Chrome Rule.** Brand, selection, focus and the primary button are ink, never a line colour. Line colours mean "this machine model" and nothing else.
**The Name Beside Colour Rule.** A line colour is never the only identifier; the model name is always written out beside it.

## Typography

**Display Font:** Barlow Semi Condensed 700 (self-hosted via Fontsource; fallback Atkinson Hyperlegible Next, system-ui)
**Body Font:** Atkinson Hyperlegible Next 400/600/700 (self-hosted; fallback system-ui, -apple-system, "Segoe UI", sans-serif)

**Character:** Atkinson is chosen for legibility at phone distance in dim rooms; the condensed Barlow is reserved for what is read and keyed: the wordmark and every number.

### Hierarchy
- **Song number** (700, 2rem default, 2.25rem on desktop rows, up to 9rem in the read-out, line-height 1, tabular, +0.02em): the single heaviest element of a row. The read-out size is computed from digit count so any length fits the sheet.
- **Wordmark** (Barlow 700, 1.75rem, +0.01em): header brand.
- **Line name** (Barlow 700, 1.5rem, 1.1): line sign title; the badge initial is 1.25rem.
- **Headline** (700, 1.5rem, 1.2): read-out song title; prose h1 is Barlow 2.25rem/1.1.
- **Title** (600, 1.0625rem, 1.3): song title in a row.
- **Body** (400, 1rem, 1.5): prose, capped at 65ch.
- **Label** (600, 0.9375rem): artists, status, hints, footer, line detail. Headings h1-h3 are forced to 700.

### Named Rules
**The Station Number Rule.** Song numbers always use the display face, tabular figures and weight 700; they are never styled as decoration, glowing or segmented.

## Layout

Single centered column, mobile first: `max-width` 42rem, widening to 56rem at 48rem and 64rem at 64rem; the header and footer follow the same widths. At 48rem the song list becomes two columns (2.5rem column gap). Vertical rhythm is 0.75rem between stacked controls, 1rem page padding, rows 4.5rem tall (5rem on desktop). Horizontal strips (model chips, alphabet) scroll with proximity snap and bleed to the screen edge. Safe-area insets are honoured in the header and footer. Order on first viewport: header, line sign, model chips (only when more than one model), search, alphabet strip, ruled rows. Motion is limited to a 220ms sheet entrance and 260ms number entrance (cubic-bezier(0.16, 1, 0.3, 1)), all removed under `prefers-reduced-motion`.

## Elevation & Depth

Flat. Depth comes from fills (wall, sign, sign tint), hairline rules and 2px control borders. The one shadow is the header menu popover (`0 10px 28px rgb(11 27 43 / 0.2)`); the read-out sheet separates from the page with a scrim (`rgb(11 27 43 / 0.55)`, 0.65 black in dark). The sticky line sign carries a `0 0 0 0.5rem` wall-coloured spread that masks rows scrolling under its rounded corners; it is a mask, not a shadow.

### Named Rules
**The Flat Sign Rule.** No gradients, glows or card shadows. A sign is a flat fill with a hairline or 2px border.

## Shapes

Soft but sober: 0.5rem for small keys and rows, 0.75rem for controls and the line sign, 1rem for sheets and state panels, full pill for chips, badges and the round line badge. Rows are ruled with a bottom hairline, not boxed. Focus is a 3px ink outline, 3px offset (inputs: 2px, no offset, plus an ink border).

## Components

### Buttons
- **Primary:** ink fill, on-brand text, 0.75rem radius, 3.5rem tall, weight 700; hover brightens (filter 1.08), active darkens (0.94).
- **Quiet:** transparent, 2px strong-rule border, 3rem tall, 0.9375rem; hover fills sign tint.
- **Icon button:** 3rem square minimum, 0.75rem radius, hover sign tint.

### Chips (model chooser)
White pill, 2px strong-rule border, a 1rem line-colour dot ringed by a 1px strong rule. Selected: fills with the line colour and on-hue text, dot hidden.

### Cards / Containers
There are no card-per-row lists. Containers are the read-out sheet (white, 1px strong rule, 1rem radius) and state panels (1px rule, 1rem radius, centered).

### Inputs / Fields
White fill, 2px strong-rule border, 0.75rem radius, 3.5rem tall, 1.125rem text for search; labels weight 700; hints muted. Invalid: error border plus error message text. Search has a leading icon and a 3rem clear target.

### Navigation
Slim white header with a hairline bottom: round logo (2.25rem) plus Barlow wordmark, a demo badge (pill, 1.5px currentColor border) and a menu popover of 3rem links. Footer links are 3rem tall, ink, weight 600. Alphabet keys are 3rem squares; selected is ink.

### Line Sign (signature)
The selected model as a metro line header: full-width sticky bar (top 0) in the model's line colour, a round badge (2rem) inverted to on-hue with the model initial, model name in Barlow 700, coverage right-aligned. A `--top` variant is square-cornered, static, for the read-out sheet header.

### Song Row and Read-out
Title and artist left, number right, 4.5rem tall, hover sign tint. Tapping opens a native dialog sheet (92vw, max 40rem) showing the line sign on top, a very large number, title, artist, meta and a block primary button.

### Logo
A dynamic mic on a yellow disc (#ffc20e). The ball head is also a magnifying lens (white fill, ink ring, ink grille dots); handle in ink with red, yellow, teal stripes. Assets live in `apps/web/public/brand` (logo.svg, favicons, icons, maskable, og).

## Do's and Don'ts

### Do:
- **Do** keep light as the default and dark as a full second design that follows the phone.
- **Do** set a model's colour only through the `hue-*` class (`--hue`, `--on-hue`) and read those two variables everywhere.
- **Do** keep every target at least 3rem tall and every text/background pair at AA.
- **Do** use rules, fills and spacing for structure; keep lists ruled.
- **Do** render song numbers via the shared number token with the display face, tabular figures, weight 700.

### Don't:
- **Don't** use a line colour for brand, selection or focus.
- **Don't** reintroduce the scoreboard look: segmented/LED numerals, neon, glow, pink-purple.
- **Don't** put gradients or card shadows on surfaces, or box each row in a card.
- **Don't** rely on colour alone to tell models apart.
- **Don't** add display faces beyond Barlow Semi Condensed, or use it for running text.
