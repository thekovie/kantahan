# Handoff

Last updated: **2026-10-26**

## Current milestone

**M0 to M5 are all merged to `main`; the project is feature-complete and verified locally.** M5 (production readiness) landed in PR #5. The full stack (web, contact, ingest) builds as Docker images and passes a smoke test, but **nothing is hosted yet**: deploying needs a VPS, a domain, a reverse proxy and an SMTP account, which are the owner's to provide ([docs/deployment.md](docs/deployment.md)). The project is feature-complete against the brief.

## Completed

- **Data review (2026-10-26)**, [docs/data-review.md](docs/data-review.md): parser fixes (column headers read into titles, `v.NN` marks, tightly spaced title lines read as colliding cells, whole documents quarantined for a few odd rows) and the T-Series HDD machine ([ADR 0009](docs/decisions/0009-t-series-hdd.md)). Rebuilt locally from the same 363 documents: 78,141 to 79,029 songs, 0 documents quarantined. **To publish it on the server:** `kc import --reimport --section all`, `kc map`, `kc publish --allow-drop` (see docs/deployment.md, "After an update that changes how documents are read"). Songs that exist only on a machine's built-in base catalog (for example Sinatra's "My Way") are not in any published list and cannot be added from official sources.

- **M0** source audit, repo, logo. **M1** catalog pipeline. **M2** offline songbook PWA ([DESIGN.md](DESIGN.md)). **M3** versioned publishing and verified automatic updates ([docs/catalog-updates.md](docs/catalog-updates.md)). **M4** twelve machine-group models ([docs/model-compatibility.md](docs/model-compatibility.md), [ADR 0004](docs/decisions/0004-machine-group-models.md)).
- **M5** ([ADR 0005](docs/decisions/0005-production-deployment.md), [docs/security.md](docs/security.md)):
  - **contact service** (`server/contact`, FastAPI): validated JSON, honeypot, per-address (5/h) and overall (60/h) limits, Origin and content-type checks, header-injection safe mail, destination address and SMTP credentials only in the environment, nothing stored or logged about visitors; 46 tests
  - **contact form** on the Rights and removal page (messages per field, clear rate-limit/outage/offline states, keyboard and screen-reader friendly, axe-clean in both themes); the Privacy page states exactly what is collected
  - **deployment** (`deploy/`): web image (nginx: strict CSP with a hashed inline boot script, HSTS, per-path caching, `/api` proxy, request limit), contact image, on-demand ingest image; non-root, read-only filesystems, no capabilities; compose file, `.env.example`, Traefik example; cron wrapper (`scripts/cron-job.sh`)
  - **backup and restore** commands (SQLite online backup, checksums, safe extraction, private files); restore carries takedowns over (withdrawals, event log, publication counter, pause), refuses version folders that may hold withdrawn songs and never replaces a served folder; drilled in tests and in the Docker smoke test
  - **smoke test** (`deploy/test/smoke.sh`, in CI): more than 40 checks on the real images with synthetic data, including a real browser under the policy
  - **performance**: inline boot script (theme + early manifest download on a first visit), lazy text pages, 2 KB wordmark font subset; Lighthouse on the production images: mobile 91-92 performance and 100 elsewhere, desktop 100 everywhere
  - an independent security review found no critical issue and one high (restore could undo a takedown); that and the medium findings are fixed (see the `fix:` commits)
  - CI: contact job, deployment job, weekly dependency audit (`npm audit`, `pip-audit`: clean)
  - tests: catalog 237 (95%), contact 64 (98%), web 178 unit (98%) and 58 Playwright; smoke test 45 checks

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

1. Review and merge the M5 PR; check CI (the deployment job builds three images and takes several minutes).
2. **Deploy** when ready: follow [docs/deployment.md](docs/deployment.md) (needs a VPS, domain, reverse proxy, SMTP account). Do the "before a real catalog goes public" checklist first: try the form, try `suspend`, take one backup and one restore.
3. Optional data work: the 3 quarantined HDD documents (2015 Oct and Nov have 3 and 4 digit numbers; 2021 March lists one number twice), a hand check of more rows from the older layouts (only rendered-page spot checks so far), and the open Reyna questions below.
4. Not planned but possible: a third-party bot challenge if the form is abused, an alerting service instead of cron mail, automatic base-image rebuilds, a hand check of more rows from the older layouts.

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
- `audit` finds files replaced behind a link but only by hash (about 800 MB of downloads); the cron entries are documented, not installed anywhere.
- Search is capped at 80 results; very short queries show the first 80 in rank order, with a prompt to type more.
- Title conflicts (a number with different titles in different volumes) are left out per model: T-X 205, Flute/Piano 183, P-Series 13, HDD 5, KS-100 2, Home 40 1. Whether the machines really share numbering across volumes is the publisher's statement, not verified.
- Playwright is run with Chrome only; Firefox and Safari are untested.
- 12 rows in held volumes have uncertain titles and are left out of any build.
- **Not tested against real infrastructure:** the stack is verified with Docker locally and a throwaway SMTP sink. A real reverse proxy (does it append `X-Forwarded-For`?), a real SMTP provider and a real domain are first exercised at deployment; the checklist in docs/deployment.md covers them.
- Contact rate-limit counts are per process and reset on restart; base images are rebuilt by hand; alerts depend on cron mail on the host.
- The first catalog build on a server downloads about 800 MB and takes roughly an hour.
- The 43 audited PDFs and the local database exist only on the developer machine (`catalog/work/`); recreate with the commands above.
- Package installs stalled twice during the M0 session (cause not diagnosed).

## Important decisions

- Public repo: **no PDFs or song data committed** (`.gitignore`). Local-only ingestion until rights are resolved.
- A release is tied to a model only through a `release_model` evidence row: the page-1 header for Reyna (strict), or "listed under <section> on the publisher's page" for the other machine groups ([ADR 0004](docs/decisions/0004-machine-group-models.md)).
- Song numbers are text; entries are never merged across numbers or models.
- Uncertain data is not built: documents with errors are quarantined, conflicting numbers are excluded and block `validated`, uncertain artists are withheld.
- Commits and PRs carry no co-author or tool attribution.

## Recent changes

- 2026-10-23: M1 catalog pipeline, tests and docs (branch `m1-database`).
- 2026-10-23: M0 audit, logo and icon set.
