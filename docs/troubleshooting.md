# Troubleshooting

- **HTTP 429 from platinumkaraoke.com:** the site rate-limits automated requests (`Retry-After: 60`). The fetcher waits and retries up to four times; if it still fails, wait several minutes and run the command again. Do not parallelise or lower the delay.
- **Empty reply from MediaFire:** seen once; the fetcher retries on connection errors.
- **`pip` or `uv` hangs while installing:** stalled twice during the M0 audit (cause not diagnosed) and worked later with `uv venv --python 3.12`. If it hangs, rerun with `UV_HTTP_TIMEOUT=30 uv pip install -v ...` to see where it stops.
- **`unexpected table structure: N vertical borders` (quarantine reason `extraction_failed`):** a document no longer has 4 cell borders per table (or 3 on the last table). Open the PDF; if the layout changed, a new parser profile is needed. The document stays quarantined and nothing from it is built.
- **`build` exits 2 and lists conflicts:** two releases print the same number with different text. Inspect both volumes; conflicting numbers are left out of the bundle until resolved.
- **Artist missing or title row left out of a bundle:** the extractor could not place overlapping text from the source PDF (`overprint` / `title_overprint` flags). This is intentional, not a bug; see [catalog-ingestion.md](catalog-ingestion.md). Many unresolved rows in a new document usually mean its layout writes cells in a different order.
- **The Rights and removal form says the message could not be sent:** `docker compose logs contact` shows `contact failed: <ErrorType>` (for example `SMTPAuthenticationError`, `TimeoutError`, `gaierror`). Check `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, user and password in `deploy/.env`, then `docker compose up -d contact`. No message text or credentials appear in logs.
- **The form answers 403:** `ALLOWED_ORIGINS` does not match the address in the browser exactly (scheme, host, port; no trailing slash).
- **Everyone is told "too many messages":** the reverse proxy is not forwarding `X-Forwarded-For`, so all visitors look like one address. Fix the proxy ([deployment.md](deployment.md)); raising `RATE_PER_IP_HOUR` only hides it.
- **The contact service will not start:** the log names the missing or wrong variable (`SettingsError`).
- **The site shows "The songs did not load" after a fresh install:** no catalog has been published yet. Run `docker compose run --rm ingest run --manual`, then reload.
- **`run` exits 1 with "partial":** some source links did not download; the rest was published. Look for `FAILED` lines in `/var/log/kantahan/ingest-run.log`. It is retried the next day.
- **`run` exits 2:** a safety gate refused to publish (too many conflicting numbers, or a big drop in songs). The live catalog is unchanged. Read the message; `--allow-drop` is for intentional removals only.
- **Browser console shows a Content-Security-Policy error after you changed the app:** a new script, style source or font came from somewhere the policy forbids. Keep resources on the site, or widen the policy deliberately in `deploy/web/security-headers.conf` and run the smoke test.
- **`docker compose` says a bind path for `/backups` is missing or not writable:** create `deploy/backups` (or set `BACKUP_DIR`) and give it to uid 10001: `sudo chown 10001:10001 deploy/backups`. If Docker created it, it belongs to root and the job cannot write to it.
- **`restore` says "checksum mismatch":** the backup folder is damaged or incomplete; use an older one.
- **`unknown source') 'x'; call ensure_source first`:** register the source (the CLI does this for the sources it imports from).
