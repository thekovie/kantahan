# Agent instructions

Authoritative docs live in the repo; read them instead of relying on this file:

1. [HANDOFF.md](HANDOFF.md): current milestone, next steps, commands
2. [README.md](README.md): scope and doc index
3. [docs/](docs/): architecture, audit, ingestion, legal

Rules specific to this repo:

- Scope is a songbook only. Do not add queueing, accounts, playback, lyrics or social features.
- Never invent song numbers, download URLs or model mappings. Separate verified evidence from assumptions in docs.
- Never commit source PDFs or extracted catalog data to the public repo (owner decision; see docs/legal-and-attribution.md). `.gitignore` enforces `*.pdf` and catalog work dirs. Credit the source wherever catalog data is shown.
- Song numbers are strings (keep leading zeros). Never deduplicate across models.
- Do not imply affiliation with Platinum Karaoke or Vismay International Corporation.
- Commit messages and PR text carry no co-author trailers or tool attribution.
- Update HANDOFF.md at the end of every meaningful session.
