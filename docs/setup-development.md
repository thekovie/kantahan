# Development setup

Covers the catalog pipeline (`catalog/`, Python) and the web app (`apps/web`, Node).

## Prerequisites

- Python **3.12** and [uv](https://docs.astral.sh/uv/). The suite was developed and passes on 3.12.
- macOS or Linux. No system PDF tools are needed.

## Install

```bash
cd catalog
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

## Checks

```bash
cd catalog
.venv/bin/python -m pytest          # 140 tests, coverage report
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy src                  # strict
```

## Run the pipeline locally

All output goes to `catalog/work/` (gitignored: the database, downloaded PDFs and built bundles). Nothing in it may be committed or published.

```bash
cd catalog
.venv/bin/kantahan-catalog discover        # read the approved index pages (A, B, C)
.venv/bin/kantahan-catalog fetch           # download the REYNA SERIES documents (polite; ~3 s apart); `--section all` fetches every machine group (about 800 MB)
.venv/bin/kantahan-catalog import          # extract, validate, import
.venv/bin/kantahan-catalog import --from b c   # record B and C links (no new documents expected)
.venv/bin/kantahan-catalog map                 # join volumes to the machine groups that list them (run after import)
.venv/bin/kantahan-catalog stats
.venv/bin/kantahan-catalog build --model reyna
```

Options: `--work DIR` (default `work`), `--sources FILE` (default `sources.yaml`), `--section NAME` and `--from a b c` (case-insensitive) on `fetch`/`import`; `fetch --refresh` downloads even when the file exists; `import --retry-quarantined` evaluates quarantined documents again after an extractor fix. `migrate --down N` reverts migrations. `build` exits 0 when validated, 2 when conflicts block validation, 1 on error.

Publishing and scheduled runs (M3), all under `catalog/work/`:

```bash
.venv/bin/kantahan-catalog publish                 # build every model in display.yaml, publish vN
.venv/bin/kantahan-catalog run --manual            # discover, fetch, import, publish now
.venv/bin/kantahan-catalog audit                   # re-hash every document, report changes
.venv/bin/kantahan-catalog rollback v1             # point the live manifest at an older version
.venv/bin/kantahan-catalog suspend --notice "Paused while a request is reviewed."
.venv/bin/kantahan-catalog resume
.venv/bin/kantahan-catalog withdraw --release "Volume 64"
```

`--out DIR` changes the publish folder, `--display FILE` the display file. See [catalog-updates.md](catalog-updates.md).

Fetching downloads about 49 MB the first time. The site rate-limits automated requests, so do not lower the delay or run fetches in parallel.

## Web app

Needs Node 22 and an installed Google Chrome (the end-to-end tests use it).

```bash
cd apps/web
npm ci
npm run catalog:synthetic        # (re)generate the fake demo catalog in public/catalog (already committed)
npm run dev                      # http://localhost:5173, demo catalog
npm run typecheck && npm test    # types, 115 unit tests with coverage thresholds
npm run build                    # tsc + production build with the service worker
npx playwright test              # end-to-end suite (builds and serves on port 4173)
```

To browse the real catalog built by the pipeline (stays on your machine, gitignored):

```bash
cd apps/web
npm run catalog:local            # copies the catalog published by `kantahan-catalog publish` to public/catalog-local
VITE_CATALOG_BASE=/catalog-local npm run dev
```

`public/catalog-local/` must never be committed or deployed.

### Trying it on a phone

- **Android, full PWA (install, offline, updates):** connect by USB, open `chrome://inspect/#devices` in desktop Chrome, add port forwarding `4173 -> localhost:4173`, run `npm run build && npm run preview`, then open `http://localhost:4173` on the phone. The phone treats `localhost` as a secure page, so the service worker and install work.
- **Any phone on the same Wi-Fi, quick look:** `npm run build && npm run preview -- --host`, then open `http://<your computer's address>:4173`. Over plain http browsers do not run the service worker (no install, no offline) but search, themes and catalog updates work; downloads are still checksum-verified by the built-in SHA-256.
- **iPhone, full PWA:** needs https, for example a tunnel to port 4173.
- To test an update: build a newer catalog (`kantahan-catalog publish` or `npm run catalog:synthetic` with a changed generator), serve it, and tap "Check for updates".
