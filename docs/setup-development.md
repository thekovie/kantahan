# Development setup

Implemented for the catalog pipeline (`catalog/`). The web app (`apps/web`) does not exist yet (M2).

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
.venv/bin/kantahan-catalog fetch           # download the REYNA SERIES documents (polite; ~3 s apart)
.venv/bin/kantahan-catalog import          # extract, validate, import
.venv/bin/kantahan-catalog import --from b c   # record B and C links (no new documents expected)
.venv/bin/kantahan-catalog stats
.venv/bin/kantahan-catalog build --model reyna
```

Options: `--work DIR` (default `work`), `--sources FILE` (default `sources.yaml`), `--section NAME` and `--from a b c` (case-insensitive) on `fetch`/`import`; `fetch --refresh` downloads even when the file exists; `import --retry-quarantined` evaluates quarantined documents again after an extractor fix. `migrate --down N` reverts migrations. `build` exits 0 when validated, 2 when conflicts block validation, 1 on error.

Fetching downloads about 49 MB the first time. The site rate-limits automated requests, so do not lower the delay or run fetches in parallel.
