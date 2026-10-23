# Security

> **Status: crawler limits (M1) and update integrity (M3) are implemented. The contact endpoint, security headers and deployment controls are planned (M5).**

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

## Planned (M5)

Contact endpoint with validation, rate limiting and honeypot, server-side SMTP, no destination address in client code; security headers (CSP, HSTS) and HTTPS at the proxy; dependency audits; a security review of the contact endpoint.
