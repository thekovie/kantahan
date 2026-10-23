# Contributing

Kantahan is early-stage. Read [HANDOFF.md](HANDOFF.md) first; it lists what exists and what is next.

## Ground rules

- Keep the scope: a songbook only. No queueing, accounts, playback, lyrics, payments or social features.
- Do not invent data. Song numbers, download URLs and model mappings must come from audited sources, and docs must separate verified evidence from assumptions.
- Do not commit source PDFs or extracted song data. Rights are unresolved (see [docs/legal-and-attribution.md](docs/legal-and-attribution.md)).
- Do not imply affiliation with Platinum Karaoke or Vismay International Corporation.
- Song numbers are strings. Never strip leading zeros, never merge entries across models.

## Workflow

1. Branch from `main` (`m1-database`, `fix-search-ranking`, ...).
2. Write the test first, then the code. Target 80%+ coverage.
3. Conventional commits: `<type>: <description>` with type one of `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`. No co-author trailers or tool attribution.
4. Open a PR with a summary and a test plan. Keep docs in sync with the code in the same PR, and update `HANDOFF.md` for meaningful changes.

## Reporting rights concerns

Rights holders who want a catalog entry corrected or removed: see the Rights and Removal page once the app ships (planned, M5). Until then, open a GitHub issue.
