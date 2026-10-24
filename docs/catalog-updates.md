# Catalog updates

> **Status: implemented (M3) and exercised locally; hosting and the cron entry are set up in M5.**

How a new Platinum volume reaches a phone, and how the owner can undo or pause it.

## Overview

```
cron (daily) -> kantahan-catalog run
                  discover -> fetch new links -> import -> publish
                                                             |
                work/publish/  manifest.json   <- swapped last, atomically
                               v1/ v2/ v3/ ... <- immutable bundles, newest few kept
                                                             |
static host  ------------------------------------------------+
                                                             |
phone: open app -> saved catalog shows at once -> (if the last check is over 12 h old)
       fetch manifest -> download changed bundles -> verify SHA-256 -> swap in one transaction
```

## Server side (`catalog/`)

| Command | What it does |
|---|---|
| `run` | The scheduled pass: `discover`, `fetch` (new links only), `import`, `map`, `publish`. Skips itself ("not due") unless the last successful scheduled run is older than `--min-interval-days` (default 14). `--manual` ignores the interval. Holds a lock, so two runs never overlap. One dead download link does not block the others: the run continues, publishes what it has, and exits 1 with outcome `partial`, which does not count as a success, so the next daily run tries again. Exit 0 ok, 1 error or partial, 2 blocked by a safety gate. Each run is recorded in `import_run`. |
| `publish` | Build every model listed in `display.yaml`, verify, and publish a new version. `--keep N` versions stay on disk (default 5; the live one is never pruned). `--allow-drop` lifts the drop gate. |
| `audit` | Download every known document (all machine groups, about 800 MB, so run it monthly at most) again and compare its hash with what was imported. The document host sends no ETag or Last-Modified, so a file replaced behind the same link is only visible this way. Reports `CHANGED` files, imports nothing, exits 2 on drift. Meant to run monthly. To take a changed file: `fetch --refresh`, `import`, then `publish`. |
| `rollback vN` | Point the live manifest at an older version after re-checking that version's hashes. Phones follow because they update to any different version, not only newer ones. **Rollback is temporary**: the next `run` or `publish` builds from the database again and publishes a new version, so to keep something out use `withdraw`, and to stop updates use `suspend`. Refuses versions that predate a withdrawal. Waits for no one: if a `run` or `publish` is in progress it stops with a message. |
| `suspend [--notice TEXT]` / `resume` | Make every app that checks in hide the songs and show the notice (bundles stay in place). Meant for a takedown request while it is being handled. Works even while a long `run` is fetching (it only takes a short lock on the manifest), and a publish that is running, or runs later, keeps the pause. Apps already open notice it at their next check. |
| `withdraw --release LABEL` (or `--release-id N`) | Leave a release out of every later build, publish a catalog without it, and **delete every older version folder**, because those still contain the withdrawn songs (any later publish also removes such folders). Only the models that contained the release may shrink past the drop gate. If publishing is not possible (for example it was the only release), the release stays withdrawn and the command says to `suspend`. Songs already saved on devices are replaced at their next update, or hidden at once by `suspend`. |

All of these use `work/publish/` (or `--out`) and `display.yaml`, which names each model, its family and its colour. A model is published only if it is listed there **and** has mapped releases (see [model-compatibility.md](model-compatibility.md)).

### Safety gates (publish refuses, live catalog unchanged, exit 2)

- More than 5% of a model's numbers conflict (the same number with different titles in two releases). Up to 5% are left out and counted in the manifest as `excluded`; a number with the same title but different artist text keeps the song with the artist withheld.
- A model would lose more than 2% of its songs, or disappear, compared with the live manifest (unless `--allow-drop`).
- A bundle fails the self-check after being written: valid JSON, schema, equal column lengths, digit-only unique numbers, count matches, hash matches the file on disk.
- Nothing is publishable at all.
- The version folder already exists (for example the database was restored from an older backup): nothing is touched.

Publishing the same data twice does nothing (`unchanged`). A failure at any step removes the half-built folder and leaves `manifest.json` as it was.

### Layout of `work/publish/`

```
manifest.json         the live catalog; replaced atomically, always the last step
v<N>/<model>.json     immutable bundles (plain JSON; the web server compresses them)
v<N>/manifest.json    the manifest as published, used by rollback
```

### Manifest (schema 1)

```json
{
  "schema": 1, "version": "v3", "generatedAt": "2026-11-06T03:00:00+00:00",
  "synthetic": false, "suspended": false, "notice": "only when suspended",
  "source": { "label": "Platinum Karaoke song list updates", "url": "https://..." },
  "models": [{
    "slug": "reyna", "name": "Reyna", "family": "Reyna series", "hue": "magenta",
    "file": "v3/reyna.json", "sha256": "<64 hex of the file's exact bytes>", "bytes": 143995,
    "songs": 3186, "coverage": "Volumes 62 to 76"
  }]
}
```

`excluded` (not shown above) is added to a model only when some song numbers were left out because the publisher lists them with different titles; the app then says how many.

### Scheduling

The scheduler is the host's cron. It starts the job daily; the job decides whether a pass is due, so a failed run is retried the next day. Example (set up with the deployment in M5):

```cron
15 3 * * *  cd /srv/kantahan/catalog && .venv/bin/kantahan-catalog run >> /var/log/kantahan-run.log 2>&1
45 3 1 * *  cd /srv/kantahan/catalog && .venv/bin/kantahan-catalog audit >> /var/log/kantahan-audit.log 2>&1
```

Alerts are log lines and exit codes for now (a non-zero exit, `WARNING: n document(s) in quarantine`). E-mail alerts arrive with the M5 mail settings.

## Client side (`apps/web`)

- **On open** the saved catalog is shown immediately. If the last comparison with the server is older than 12 hours (or the catalog is paused) the app fetches the manifest in the background.
- **Same version and state** means nothing to do. **A different version** (newer or a rollback) means: download only the models already saved on this device whose hash changed, check each (SHA-256 of the exact bytes, schema, model name, song count), then write the new manifest and bundles in **one IndexedDB transaction**. Models that left the catalog are removed in the same transaction.
- **Any failure** (offline, server error, corrupt file, full storage) keeps the old catalog and tries again on the next open. "Check for updates" in the catalog note forces the check and says what happened: "Up to date.", "Updated to v3.", "No connection. Your saved songs still work.", or the failure with "Your saved songs were kept."
- The search index is rebuilt and swapped in place: the search box and the open song stay as they were.
- **Paused** (`suspended: true`): the app shows "The songbook is paused" with the notice instead of songs, checks on every open, and brings the songs back when the manifest says so. Saved songs stay on the device but are hidden.
- A model that was never opened is downloaded when first opened, using the saved manifest; if that file is gone (an old version was pruned), the retry button first looks for a newer catalog.
- The service worker does not cache anything under `/catalog`: the manifest always comes from the network (a stale copy could hide a pause or a rollback) and saved songs live only in IndexedDB. Serve `manifest.json` with `Cache-Control: no-cache` and the `v*/` folders as immutable (M5 deployment).
- Overlapping checks (on-open check, button taps, retry) share a single comparison, and only the newest screen request may change what is shown, so a slow load can never overwrite a model chosen afterwards.
- Limits: manifests over 1 MB, bundles over 25 MB or not exactly the announced size, and source links that are not https are refused.
- On a page without SubtleCrypto (plain http, for example a phone testing against a computer on the local network) the app falls back to a built-in SHA-256, so downloads are still checked.

See [security.md](security.md) for the integrity model and [testing.md](testing.md) for how this is tested.
