# Troubleshooting

- **HTTP 429 from platinumkaraoke.com:** the site rate-limits automated requests (`Retry-After: 60`). The fetcher waits and retries up to four times; if it still fails, wait several minutes and run the command again. Do not parallelise or lower the delay.
- **Empty reply from MediaFire:** seen once; the fetcher retries on connection errors.
- **`pip` or `uv` hangs while installing:** stalled twice during the M0 audit (cause not diagnosed) and worked later with `uv venv --python 3.12`. If it hangs, rerun with `UV_HTTP_TIMEOUT=30 uv pip install -v ...` to see where it stops.
- **`unexpected table structure: N vertical borders` (quarantine reason `extraction_failed`):** a document no longer has 4 cell borders per table (or 3 on the last table). Open the PDF; if the layout changed, a new parser profile is needed. The document stays quarantined and nothing from it is built.
- **`build` exits 2 and lists conflicts:** two releases print the same number with different text. Inspect both volumes; conflicting numbers are left out of the bundle until resolved.
- **Artist missing for many songs:** the source PDF overprints neighbouring artist text. This is intentional withholding, not a bug; see [catalog-ingestion.md](catalog-ingestion.md).
- **`unknown source 'x'; call ensure_source first`:** register the source (the CLI does this for the sources it imports from).
