# 0006: Interface direction reroll, Metro Wayfinding

Status: accepted, 2026-10-24. Supersedes [0003](0003-m2-ui-direction.md).

## Context

The owner rejected the "Videoke Night" look: the pink-purple theme and the LED, scoreboard-style song numbers. Their answers for the replacement were: calm and clean, bold plain song numbers, light first with dark following the phone. The earlier brief ("colorful, not boring") still applies, so colour stays, but it now does jobs instead of filling the screen.

The design skills were run again. The direction roll assigned a jeepney signboard; the owner chose the skills' own pick, Metro Wayfinding, from a decision page that also offered a dense catalog grid, the category standard and two declined worlds (star atlas, botanical folio).

## Decision

- **World:** clean wayfinding signage. Each machine model is a coloured "line"; the selected one is drawn as a line sign (round badge with the initial, the name, the volumes covered) above the search. The model's name is always text, so colour is never the only cue.
- **Song number:** heavy plain figures (Barlow Semi Condensed Bold, tabular) at the end of each ruled row, and very large in the read-out sheet. No tile, no glow. Leading zeros stay. Screen readers still hear separate digits.
- **Palette:** cool off-white wall `#F4F6F9`, white signs, ink `#0B1B2B`, sign ink as the brand colour (buttons, focus; near white in dark), six line colours (red, blue, teal, orange, green, yellow) each with a text colour that passes AA. The brand is deliberately not blue: the first rebuild used a blue tile with a white K and a yellow dot, and the owner pointed out it looked like their own website. Dark is a blue-black wall with lighter line colours. The catalog's hue names (magenta, violet, aqua, orange, lime, yellow) are part of the data contract, so they are unchanged and only mapped to these colours in CSS.
- **Theme:** light is the default and the first design; dark follows the phone's setting and is a full matching version. The manual toggle is kept.
- **Type:** Atkinson Hyperlegible Next for reading, Barlow Semi Condensed Bold for the wordmark and the numbers (self-hosted, SIL OFL, licence in `apps/web/src/assets/fonts/`). Fredoka and DSEG7 are removed.
- **Brand:** a new logo, suggested by the owner: a handheld dynamic microphone whose round ball head doubles as a magnifying lens (search), on a yellow disc that reads on both light and dark headers, with the handle banded in three line colours (red, yellow, teal). It replaces the K-with-mic tile, which resembled the owner's site (an ink badge was tried first and nearly vanished on the dark header). Icons, maskable icon, favicon, pinned-tab icon and the share image were regenerated.
- **Layout:** ruled rows instead of boxed cards; two columns from 48rem. The line sign stays pinned at the top while the list scrolls, so the machine is never lost; the selected model chip is filled with the line colour.
- **Not changed:** every behaviour, all copy and legal wording, the data contract and the CSP.

## Consequences

- `theme.contrast.test.ts` now checks the new tokens in both themes (text pairs 4.5:1, interface parts 3:1, text on each line colour 4.5:1).
- Some tests changed with the look: the default theme is light, the number's class is `num--large`.
- The yellow line colour on a light page is below 3:1 against the page, which is fine only because the text on it is checked and the name is always written out.
- The old direction stays in git history (ADR 0003 describes it).
