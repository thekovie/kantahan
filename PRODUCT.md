# Product

<!-- impeccable:product-schema 1 -->

> Written without an interview round: the owner said to proceed, so every fact comes from the implementation brief and decisions made in this repository. Inferred facts are marked *(inferred)*.

## Platform

web

## Stack

React, TypeScript, Vite, Tailwind CSS, a service worker and IndexedDB (specified in the implementation brief, so the stack was not offered as a choice). Installable PWA, mobile first. Deployed as static files on the owner's VPS.

## Users

People singing at home or at a party on a Platinum Karaoke machine in the Philippines *(inferred from the catalog sources and the Filipino catalog)*: a mix of ages, from teenagers to grandparents, often holding a phone in a dim, noisy room, one hand busy with a microphone. They know a song (title or artist) or have its number written down, and need the **song number to key into the machine's remote**. Often offline or on poor mobile data.

## Product Purpose

Kantahan is a digital songbook that replaces the printed song-list binder. Pick your machine model, search by title, artist or song number, read the number, key it in. Strictly a songbook: no queueing, accounts, sharing, playback, full lyrics, payments or social features. Success is: a person finds the right number in a few seconds without help, on any phone, with no signal.

## Positioning

**Direction (owner, 2026-10-24):** Kantahan is for local Philippine karaoke machines in general. Platinum Karaoke is the only source today; more local machines are planned and the app says so ("coming soon") on About, Privacy, Rights and in the footer, without naming brands or dates. New machines are added only from their official song lists, each as its own model.

The song number is per machine model. A neighbouring songbook app that ignores the model shows numbers that are wrong on the user's machine; Kantahan keeps model-specific numbering and never claims a song exists on a machine because it exists on another. It works fully offline and updates its catalog quietly in the background.

## Operating Context

Songs and numbers come from the official Platinum Karaoke song-list updates, extracted by the catalog pipeline in this repository (`catalog/`). Lists are incremental volumes, so coverage is "songs from the volumes we have", and the app must say so. Numbers are strings with leading zeros (for example `00589`). Today only the Reyna family has verified data (Vol 62 to 76, 3,186 songs, built locally); other families arrive in a later milestone. Real catalog data is built where it is served and is not committed to this public repository; development and tests use clearly synthetic data.

## Capabilities and Constraints

- Search by title, artist or number; partial, case- and accent-insensitive, basic typo tolerance.
- Model selector with a remembered choice, plus an **All machines** view (added 2026-10-24 at the owner's request; it is also what a first visit opens on): every machine's songs in one searchable list. The data is never merged. In this view identical entries (same song, same number) show once and name every machine that has them; the same song under different numbers, or a number used for different songs, stay separate rows. Offline search; catalog version info.
- Catalog updates (manual check, silent background sync) arrive in M3; M2 loads the catalog and stores it locally.
- Pages: About, Privacy, Rights and Removal (the contact form is M5; until then the page points to the repository issue tracker).
- Not in scope: queueing, sharing, QR codes, accounts, multiplayer, streaming, lyrics, payments, social.
- Terminology: "song number" (not "code"), "model" (the machine), "songbook". The official brand name "Platinum" appears only as a factual credit, never in branding.
- Undecided: font choice, other model families' names and colors, deployment domain.

## Brand Commitments

- Name **Kantahan** (Tagalog, a place or time to sing together); independent, not affiliated with Platinum Karaoke or Vismay International Corporation, and it must say so.
- Logo: a dynamic microphone whose ball head doubles as a magnifying lens, on a yellow disc, with the handle banded in three line colours (`apps/web/public/brand/`). It must not resemble the owner's own website (a blue rounded tile with a white K and a yellow dot), which an earlier version did.
- Visual direction "Metro Wayfinding" (docs/decisions/0006-wayfinding-ui.md): calm and clean, light first with dark following the phone, one coloured "line" per machine model, heavy plain song numbers. The owner rejected the earlier pink-purple palette and the LED scoreboard numbers, so neither returns. The first brief still asks for a colourful, not boring app: colour does jobs (model line, selection, state), it does not fill the screen.
- Source credit wherever catalog data is shown (wording in docs/legal-and-attribution.md).
- No co-author or tool attribution in commits or PRs (process rule).

## Evidence on Hand

- A real Reyna bundle exists only on the owner's machine (`catalog/work/releases/reyna.json`). Nothing else about users, usage or demand exists: no analytics, no interviews, no testimonials. Do not invent any.
- Brand assets: logo SVG/PNG set and social image in `apps/web/public/brand/`.

## Product Principles

1. **The number is the product.** Every screen is judged by how fast a person can read the right number.
2. **Honest coverage.** Say which model and which volumes are shown; never imply a complete catalog; credit the source.
3. **Works with no signal and no patience.** Instant first paint, search that does not wait for the network, updates that never interrupt.
4. **Anyone, not just phone natives.** Large type, large targets, plain words, no hidden gestures.
5. **Joyful but not busy.** Colour and playfulness live in the brand and the number; the working surface stays calm and fast.

## Accessibility & Inclusion

WCAG 2.2 AA (4.5:1 text, 3:1 large text and UI parts), touch targets of at least 48 px, body text of at least 16 px, light and dark themes, reduced motion respected, dynamic type to 200% without loss. Filipino and English content; names may include diacritics. Colour is never the only carrier of meaning (model families have a name as well as a hue).
