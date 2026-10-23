# Handoff

Last updated: **2026-10-23**

## Current milestone

**M3, automatic updates: built and verified locally on branch `m3-updates` (PR pending).** M0, M1 and M2 are merged to `main`. Nothing is hosted yet: serving `work/publish/` and the cron entry come with M5. Next: M4 other models.

## Completed

- **M0** source audit ([docs/source-audit.md](docs/source-audit.md)), repo, docs skeleton, logo and icon set.
- **M1** catalog pipeline in `catalog/` (Python 3.12, SQLite, pdfplumber): migrations, discovery, polite fetcher, geometry-based PDF extractor with an overlap rule, validator, importer, local bundle builder ([docs/catalog-ingestion.md](docs/catalog-ingestion.md)).
- **M2** offline songbook PWA in `apps/web` (React 19, TypeScript, Vite, Tailwind 4, idb, MiniSearch): model picker, search, browse by letter, full-size read-out, light and dark themes, fake demo catalog ([DESIGN.md](DESIGN.md), [ADR 0003](docs/decisions/0003-m2-ui-direction.md)).
- **M3** automatic updates ([docs/catalog-updates.md](docs/catalog-updates.md), [docs/security.md](docs/security.md)):
  - server: `publish` (immutable `v<N>` folders, self-check, gates for conflicts and drops over 2%, atomic manifest swap, pruning), `run` (discover, fetch new, import, publish; 14 day due check; run lock; `import_run` records), `audit` (re-hash every document), `rollback`, `suspend`/`resume`, `withdraw`; migration 0004; `catalog/display.yaml` names and colours each model
  - client: on-open check when the last one is over 12 h old and a "Check for updates" button; only changed saved models are downloaded; SHA-256, schema, model and count are verified; manifest and bundles are committed in one IndexedDB transaction; any failure keeps the old catalog; the search index is swapped without losing the search box; a paused catalog shows its notice; rollbacks are followed
  - tests: catalog 176 (96% coverage), web 146 unit (98%) and 44 Playwright (update while searching, corrupt download, pause and resume, axe)
  - reviewed by independent security and code reviewers; accepted findings fixed (version-folder collision, withdraw purges old versions, no service-worker caching of the catalog, size limits, single-flight checks, partial runs, manifest lock so `suspend` works during a run)
  - real data: `publish` on the local database produced `v1` with 3,186 Reyna songs (local only)

## Results on real data (local run, 2026-10-23)

- Discovery reproduced the audit: 393 links on A (Reyna 43), B (42), C (35).
- 43 of 43 documents extracted: 12,489 rows; 40 of 43 match an independent token count exactly, the other three are one row short because of one stray token each.
- Import: 14 releases **mapped** to `reyna` (Vol 62 to 76, 3,216 rows), 29 **held** (9,273 rows, headers say T-X, SD, or name no family), 0 quarantined. B and C added 77 links to the same 43 documents.
- Build: `reyna` bundle validated, **3,186 songs**, 0 conflicts, 30 identical re-listings collapsed, **0 artists withheld**, 0 rows left out. A stream-order overlap rule resolves the overprinted rows (878 rows changed vs plain nearest-row assignment; the first version of this build withheld 519 artists). 12 rows in held volumes remain flagged as uncertain titles.
- Hand check: 36 rows across three layout generations were correct (done before the overlap rule). After the rule, changed rows were read for plausibility only; recovered words are hidden overflow text that the rendered page does not show.

## Open questions and decisions

1. **Rights: decided by the owner (2026-10-23).** No permission request; credit the source (attribution text in [docs/legal-and-attribution.md](docs/legal-and-attribution.md)). This is a decision, not a legal finding; the takedown path (Rights and Removal page, contact form in M5) stays. Real catalog data still stays out of the public repo.
2. **Reyna variant (partly answered).** Source D pages were fetched slowly and read. For Vol 100 and Vol 108 the Reyna /2/3C/SE, Reyna 3/4 and T-X pages list identical featured songs, but say nothing about song numbering or compatibility. Mapping rules are unchanged: only "For Reyna" headers (Vol 62 to 76) map to the `reyna` model.
3. **Coverage:** only Vol 62 to 76 are evidence for Reyna; Vol 77 to 108 are listed under Reyna on Source A but their headers say T-X-R-BMB, SD, T-X/K-Box or nothing. The base catalog before Vol 62 and Vol 107 are not in the archives. Whether the Vol 77 to 108 numbering also works on Reyna machines is unknown.
4. **Accuracy evidence is small** (36 rows hand-checked). Enlarge before M3 automation.

## Outstanding tasks

- Optional: read the Platinum/Vismay terms and `agents.md` to know what is being accepted.

## Next recommended steps

1. Review and merge the M3 PR; check CI.
2. **M4** other Platinum models: only where header evidence ties a volume to a model (see [docs/model-compatibility.md](docs/model-compatibility.md)); add each model to `display.yaml` with a hue.
3. **M5** production: serve `work/publish/` as `/catalog/` behind the reverse proxy (cache headers: `manifest.json` short, `v*/` immutable), cron entries from [docs/catalog-updates.md](docs/catalog-updates.md), Docker, contact form, e-mail alerts, backup and restore drills, legal pages.

## Key paths

| Path | What |
|---|---|
| `catalog/src/kantahan_catalog/` | pipeline modules (`extract.py` is the core) |
| `catalog/src/kantahan_catalog/migrations/` | schema |
| `catalog/tests/` | tests; `pdfgen.py` makes synthetic PDFs |
| `catalog/sources.yaml`, `catalog/discovered-reyna-source-a.json` | source registry and audited document hashes |
| `catalog/work/` | **local only, gitignored**: database, PDFs, bundles |
| `apps/web/src/` | app: `lib/` (search, catalog, storage, loader), `hooks/`, `components/`, `pages/`, `index.css` (tokens and components) |
| `apps/web/public/catalog/` | **fake** demo catalog (committed on purpose) |
| `apps/web/public/catalog-local/` | **local only, gitignored**: real bundle copied by `npm run catalog:local` |
| `apps/web/public/brand/` | logo and icons |
| `apps/web/e2e/` | Playwright tests; `screenshots.spec.ts` only with `SCREENSHOTS=1` |
| `PRODUCT.md`, `DESIGN.md`, `.impeccable/surfaces/` | product record, design system, direction contract |
| `docs/` | all documentation |

## Commands

```bash
cd catalog
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/python -m pytest && .venv/bin/ruff check . && .venv/bin/mypy src
.venv/bin/kantahan-catalog discover && .venv/bin/kantahan-catalog fetch && .venv/bin/kantahan-catalog import
.venv/bin/kantahan-catalog stats && .venv/bin/kantahan-catalog build --model reyna
```

```bash
cd apps/web
npm ci && npm run dev                 # demo catalog on http://localhost:5173
npm run typecheck && npm test && npm run build && npx playwright test
npm run catalog:local && VITE_CATALOG_BASE=/catalog-local npm run dev   # real catalog, local only
```

Details: [docs/setup-development.md](docs/setup-development.md).

## Known issues

- A device that loaded the demo catalog (`demo-1`) switches to a real catalog through the normal update path only if both are served from the same URL; for development clear site data when changing catalogs.
- `audit` finds files replaced behind a link but only by hash; the monthly cron entry is documented, not installed.
- Search is capped at 80 results; very short queries show the first 80 in rank order, with a prompt to type more.
- Playwright is run with Chrome only; Firefox and Safari are untested.
- 12 rows in held volumes have uncertain titles and are left out of any build.
- `import_run` table is created but unused until M3.
- The 43 audited PDFs and the local database exist only on the developer machine (`catalog/work/`); recreate with the commands above.
- Package installs stalled twice during the M0 session (cause not diagnosed).

## Important decisions

- Public repo: **no PDFs or song data committed** (`.gitignore`). Local-only ingestion until rights are resolved.
- A release is tied to a model only by page-1 header evidence, never by the section it was listed under.
- Song numbers are text; entries are never merged across numbers or models.
- Uncertain data is not built: documents with errors are quarantined, conflicting numbers are excluded and block `validated`, uncertain artists are withheld.
- Commits and PRs carry no co-author or tool attribution.

## Recent changes

- 2026-10-23: M1 catalog pipeline, tests and docs (branch `m1-database`).
- 2026-10-23: M0 audit, logo and icon set.
