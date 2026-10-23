# Legal and attribution

> **This is project documentation, not legal advice.** A disclaimer does not replace authorization.

## Independence

Kantahan is an independent project. It is not affiliated with, endorsed by, or sponsored by Platinum Karaoke or Vismay International Corporation. "Platinum", "Reyna" and related names and marks belong to their owners and are used only to identify the machines whose song lists the app indexes.

## Scope of what the project distributes

Never: karaoke audio, music videos, instrumentals, full lyrics, or the source PDFs.
Planned: per-model song number, title and artist metadata, if and only if the rights below are resolved.

## Rights status (as of 2026-10-23)

| Item | Status |
|---|---|
| Permission from Platinum Karaoke / Vismay to extract and redistribute song metadata | **Not requested, not granted** |
| License or reuse statement on the source pages inspected | **None found** |
| Terms of service of platinumkaraoke.com, platinumkaraoke.ph | **Not reviewed** |
| MediaFire terms for automated retrieval of the hosted PDFs | **Not reviewed** |
| robots.txt | `platinumkaraoke.com` allows `/pages/` for all agents; `.ph` blocks only listed SEO bots |

## Consequences for this repository

- Source PDFs and extracted song data are not committed (enforced by `.gitignore`).
- No catalog bundle is published publicly until permission is obtained or a documented legal basis exists.
- The crawler identifies itself, respects robots.txt, uses a very low request rate and backs off on HTTP 429. It does not bypass logins, rate limits or anti-bot systems.

## Planned for M5 (not implemented)

About page, independent-affiliation disclaimer, privacy notice, and a Rights and Removal page with a bot-resistant contact form. A developer-controlled process to withdraw releases or suspend the service, with no public shutdown endpoint.
