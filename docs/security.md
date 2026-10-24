# Security

> **Status: crawler limits (M1), update integrity (M3), and the contact endpoint, web headers and deployment controls (M5) are implemented.**

## Crawler (M1, `catalog/src/kantahan_catalog/fetch.py`)

Allowlist of approved hosts (checked again after every redirect), https only, no credentials or ports in URLs, robots.txt honored on the Platinum hosts, 3 s spacing, back-off on 429, 50 MB and 300 s caps per response, a page cap when parsing PDFs. Fetched script files are parsed as text and never executed.

## Update integrity (M3)

What the app trusts: the manifest and bundles from the owner's host, over HTTPS. What it checks anyway:

- Each bundle is accepted only if the SHA-256 of the **exact downloaded bytes** equals the manifest's `sha256`, and it parses as a schema 1 bundle for the same model with the announced song count. Anything else is discarded.
- Manifest and bundles are validated before use, including when read back from storage; a stored copy that no longer validates is deleted and fetched again.
- Sizes are enforced: a manifest over 1 MB, a bundle over 25 MB, or a bundle that is not exactly the announced `bytes` is refused (the announced `Content-Length` is checked before reading, the exact length after). The source link in the manifest must be an https address.
- Bundle paths in the manifest must be `name.json` or `folder/name.json` made of letters, digits and hyphens: no `..`, no absolute or external URLs.
- The service worker caches nothing under `/catalog`, so a stale manifest cannot hide a pause or rollback and withdrawn bundles are not kept in Cache Storage. On pages without SubtleCrypto the same checksum is computed by a built-in SHA-256.
- The new manifest and bundles are written in one IndexedDB transaction; a failure leaves the previous catalog untouched. A hostile or broken manifest can at worst make the app keep its saved catalog or show the pause notice (rendered as text, never HTML).
- Rollback is a feature: the app follows any version change, so the owner can undo a bad publish. The manifest is therefore as trusted as the host; protect the publish folder and the host's credentials.
- No operation that changes the catalog is exposed over the network. `publish`, `rollback`, `suspend`, `resume` and `withdraw` are commands run by the owner on the server.

Takedowns: `suspend` hides the catalog in every app at its next check; `withdraw` removes the release from all later builds and deletes every older version folder, and rollback refuses versions that predate a withdrawal. Songs already on a device are replaced at its next update, or hidden by the pause. Saved copies of a paused catalog stay on the device but are never shown.

Server-side: publishing builds in a staging folder, re-reads and hash-checks every file, and only then moves it into place and swaps `manifest.json` atomically; rollback re-checks the target version's hashes first; version arguments must match `v<number>`; SQL uses parameters; a lock file stops overlapping runs, and a short lock on the manifest orders pause, rollback and publish; a stale `.staging-*` folder from a crashed run is removed at the next publish; files are flushed to disk before the atomic rename.

## Contact endpoint (M5, `server/contact/`)

- **Input**: JSON only, at most 16 KiB; type must be one of three values; message 10 to 2,000 characters; name, e-mail and reference are single-line, length-capped and free of control characters; e-mail shape is checked. Errors are constant messages per field: nothing the visitor typed is echoed.
- **Mail**: built with Python's `EmailMessage`; no visitor text ever reaches a header except `Reply-To`, which has been validated as one address without line breaks. The subject is one of three fixed strings. Header-injection attempts are rejected as invalid input (tested).
- **Abuse**: a hidden form field that people never reach (a filled one gets a normal-looking answer and no mail), a per-address limit (default 5 an hour) and an overall limit (60 an hour) kept in memory, and a second limit in nginx. There is deliberately no third-party challenge (Turnstile/reCAPTCHA): it would add a third-party script and a Content-Security-Policy exception for little gain at this volume; revisit if abuse appears.
- **CSRF**: the `Origin` header must be one of `ALLOWED_ORIGINS` and the content type must be JSON, which a cross-site form cannot send; there are no cookies or sessions to ride on.
- **Privacy**: the destination address and SMTP credentials exist only in the environment (`_FILE` supported). The service logs event names (`accepted: removal`, `rejected: rate_limited`, `failed: <ErrorType>`) and nothing else: no message, name, e-mail, address or SMTP error text, and uvicorn's access log is off. Tests assert this. It stores nothing.
- **Startup**: missing or malformed settings stop the service and name the variable.

## Web server (M5, `deploy/web/`)

- **Content-Security-Policy**: `default-src 'self'`, scripts from the site and one inline boot script named by its SHA-256 (written by the build), styles from the site plus inline (the number tokens set a CSS variable), fonts from the site and `data:` (small fonts are inlined), no frames, objects or third parties. `X-Frame-Options: DENY`, `nosniff`, a strict referrer policy, a permissions policy that turns off camera, microphone, location and payment, and HSTS. The headers are repeated in every location (nginx drops inherited ones otherwise). A real-browser check in the smoke test fails on any policy violation or console error.
- **Caching**: shell and manifest revalidate on every use, hashed assets and `/catalog/v<N>/` are immutable, the service worker is never cached, other `/catalog/` paths are 404 and never cached. The app also asks the server for the manifest with caching skipped on every explicit check.
- **Containers**: non-root, read-only root filesystem, all capabilities dropped, `no-new-privileges`, healthchecks; the contact service is not published; the catalog volume is read-only for `web`. Images contain no real catalog data, secrets or source documents (`.dockerignore`).
- **Backups**: checksummed, restore refuses unsafe archive members and keeps what it replaces outside the served folder.

## Checks that run in CI

Contact tests (46), the deployment smoke test against built images, `npm audit` and `pip-audit` on runtime dependencies (on every pull request and weekly), a secret scan, and the web accessibility scans in both themes.

## Open points

- E-mail alerts rely on cron's `MAILTO` and a mail agent on the host; there is no alerting service.
- Rate-limit counts are per process and reset on restart (one worker on purpose).
- Base images are rebuilt by hand ([deployment.md](deployment.md)).
