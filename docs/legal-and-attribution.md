# Legal and attribution

> **This is project documentation, not legal advice.** A disclaimer does not replace authorization.

## Independence

Kantahan is an independent project. It is not affiliated with, endorsed by, or sponsored by Platinum Karaoke or Vismay International Corporation. "Platinum", "Reyna" and related names and marks belong to their owners and are used only to identify the machines whose song lists the app indexes.

## Scope of what the project distributes

Never: karaoke audio, music videos, instrumentals, full lyrics, or the source PDFs.
Planned: per-model song number, title and artist metadata, credited to the source (see the owner decision below).

## Owner decision (2026-10-23)

The project owner decided **not to request permission** from Platinum Karaoke or Vismay and to **credit the source** instead: the app and docs say where the song lists come from and link to the official archive pages. This is recorded here as a decision, not as a finding that no permission is needed. Credit is not a license, no license or reuse statement was found on the source pages, and the terms of service were not reviewed. The owner accepts that risk and the project keeps the takedown path below so a rights holder can ask for a correction or removal and get a fast response.

## Rights status (as of 2026-10-23)

| Item | Status |
|---|---|
| Permission from Platinum Karaoke / Vismay to extract and redistribute song metadata | Not requested (owner decision above) |
| License or reuse statement on the source pages inspected | None found |
| Terms of service of platinumkaraoke.com, platinumkaraoke.ph | Not reviewed |
| MediaFire terms for automated retrieval of the hosted PDFs | Not reviewed |
| robots.txt | `platinumkaraoke.com` allows `/pages/` for all agents; `.ph` blocks only listed SEO bots |

## Attribution wording

Wherever catalog data is shown (About page, catalog info panel):

> Song lists are compiled from the official Platinum Karaoke song list updates (platinumkaraoke.com/pages/songlist-update). Kantahan is independent and not affiliated with Platinum Karaoke or Vismay International Corporation.

## Consequences for this repository

- The repository is public and holds code and documentation only. Source PDFs and extracted song data are **not committed** (enforced by `.gitignore`); the catalog is built on the machine that serves it.
- Whether and when to serve a real catalog publicly is the owner's call at deployment time. Development and tests use synthetic data.
- The crawler identifies itself, respects robots.txt, uses a very low request rate and backs off on HTTP 429. It does not bypass logins, rate limits or anti-bot systems.
- The Rights and Removal page and contact form (M5) must work before a real catalog goes public; until the form exists, the page lists the repository issue tracker.

## Planned for M5 (not implemented)

About page, independent-affiliation disclaimer, privacy notice, and a Rights and Removal page with a bot-resistant contact form. A developer-controlled process to withdraw releases or suspend the service, with no public shutdown endpoint.
