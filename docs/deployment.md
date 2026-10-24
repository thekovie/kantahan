# Deployment

> **Status: implemented and smoke-tested locally with Docker (M5). Nothing is hosted yet: the steps below are what to do on the VPS.** The stack is checked by `deploy/test/smoke.sh` (more than 40 checks against the real images, synthetic data) and runs in CI.

Target: Docker Compose on a VPS behind your existing reverse proxy, which provides HTTPS. Three images, one of them on demand:

```
            reverse proxy (HTTPS, your domain)
                         |
                         v  127.0.0.1:8080
   +---------------- web (nginx) ----------------+       volume catalog-publish
   |  the app (static)   /catalog/ (read-only) <-----------+    ^ written by ingest
   |  /api/  ---> contact (FastAPI) --SMTP--> your mailbox |    |
   +-----------------------------------------------+       ingest (on demand, cron)
                                                          volume catalog-work: database, PDFs
```

| Service | What it is | Always on |
|---|---|---|
| `web` | nginx serving the PWA, the published catalog (read-only) and a proxy for `/api/` | yes |
| `contact` | relays rights and correction requests by e-mail; not reachable from outside | yes |
| `ingest` | the catalog job: discover, fetch, import, publish, audit, backup, rollback, suspend | no (run on demand or from cron) |

All containers run as non-root with a read-only root filesystem, no Linux capabilities and `no-new-privileges`. Only `web` publishes a port, and by default only on the host's loopback.

## Before a real catalog goes public

The owner decided (2026-10-23) not to ask for permission and to credit the source ([legal-and-attribution.md](legal-and-attribution.md)). Before serving a real catalog, check:

- [ ] The Rights and removal page and its form work (send yourself a test message; see "Verify" below).
- [ ] You can pause the catalog in seconds (`suspend`, see "Takedown" below) and have tried it once.
- [ ] A backup and a restore have been done at least once on this server.
- [ ] `ALLOWED_ORIGINS` is your exact public address and `CONTACT_TO` is an address you read.
- [ ] You accept the rights position described in the legal document.

## What you need

- Docker Engine with Compose v2 (`docker compose version`), 3 GB of free disk (about 800 MB of source documents plus the database and catalog), and outbound internet access for the catalog job.
- A domain with HTTPS handled by a reverse proxy (Caddy, Traefik or nginx; examples below).
- An SMTP account that can send mail (a mail provider's relay, or a local relay). Port 587 with STARTTLS is the default.

## First-time setup

```bash
git clone https://github.com/thekovie/kantahan.git && cd kantahan/deploy
cp .env.example .env && chmod 600 .env      # then edit it: see configuration.md
docker compose build
docker compose up -d                         # web and contact
docker compose ps                            # both should become "healthy"
```

Build the first catalog. It downloads about 800 MB politely (one request every few seconds) and takes roughly an hour; it can be interrupted and resumed:

```bash
docker compose run --rm ingest run --manual
docker compose run --rm ingest stats          # what was imported
```

Then open your site. Until the first catalog is published the app says the songs did not load.

## Reverse proxy

The proxy must terminate HTTPS and forward to `web`. It must **append the visitor's address to `X-Forwarded-For`** (every common proxy does by default) so the rate limit counts visitors, not the proxy. Keep `WEB_BIND` on `127.0.0.1` (or a private network): if the web port were reachable directly from the internet, a visitor could spoof that header.

**Caddy**

```
kantahan.example {
    reverse_proxy 127.0.0.1:8080
}
```

**nginx on the host**

```nginx
server {
    listen 443 ssl http2;
    server_name kantahan.example;
    # ssl_certificate ... (certbot)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Traefik**: copy `deploy/compose.traefik.example.yml`, set the host name and your network and certificate resolver names, and start with `docker compose -f docker-compose.yml -f compose.traefik.example.yml up -d`. The web port is then not published at all.

## Verify

```bash
curl -sI https://kantahan.example/ | grep -iE "content-security|strict-transport|x-frame|cache-control"
curl -sI https://kantahan.example/catalog/manifest.json | grep -i cache-control      # no-cache, must-revalidate
curl -s  https://kantahan.example/catalog/manifest.json | head -c 300                # the live catalog
```

Open **Rights and removal**, send a test message, and check that it arrives. If it never arrives: `docker compose logs contact` shows `contact failed: <ErrorType>` (no message text is ever logged); see the troubleshooting page. For a rate-limit check from your own network, send five messages in a row: the sixth must be refused with a message about trying again later. If **everyone** is refused after five messages, your proxy is not forwarding `X-Forwarded-For`.

## Scheduling

The scheduler is the host's cron. `deploy/scripts/cron-job.sh` runs one job, logs it, stays silent on success and prints the tail of the log on failure, so cron's `MAILTO` only mails real problems (the host needs a mail agent such as msmtp for that). `run` decides itself whether a pass is due (every 14 days) and a failed run is tried again the next day.

```cron
MAILTO=you@example.net
15 3 * * *    /srv/kantahan/deploy/scripts/cron-job.sh run
45 3 1 * *    /srv/kantahan/deploy/scripts/cron-job.sh audit
30 2 * * *    /srv/kantahan/deploy/scripts/cron-job.sh backup --to /backups --keep 14
```

`run` exits 1 when something failed or was only partly done (for example a source link that no longer downloads) and 2 when a safety gate refused to publish; both are mailed. `audit` exits 2 when a source file changed behind its link. See [catalog-updates.md](catalog-updates.md).

## Operating it

| Task | Command (from `deploy/`) |
|---|---|
| Update the app | `git pull && docker compose build && docker compose up -d` |
| Run a catalog pass now | `docker compose run --rm ingest run --manual` |
| What is in the database | `docker compose run --rm ingest stats` |
| Publish without fetching | `docker compose run --rm ingest publish` |
| Look at the live version | `curl -s https://kantahan.example/catalog/manifest.json` |
| Roll back a bad version | `docker compose run --rm ingest rollback v7` (temporary: the next publish builds from the database again) |
| Logs | `docker compose logs -f web contact`, and `/var/log/kantahan/ingest-*.log` for cron jobs |
| Disk use | `docker system df -v` (the catalog keeps its newest 5 versions) |

Base images are not updated automatically: rebuild now and then (`docker compose build --pull && docker compose up -d`).

## Takedown: pause, remove, resume

A rights holder asks for something to be removed. Do this in order:

1. **Pause at once** (hides the songs in every app at its next check, usually within minutes of it being opened):
   `docker compose run --rm ingest suspend --notice "The songbook is paused while a request is reviewed."`
2. **Remove the release** (it is left out of every later build, and every older published version that still contains it is deleted from the server):
   `docker compose run --rm ingest withdraw --release "Volume 64"` (add `--release-id N` when a label is not unique)
3. **Check** `curl -s https://kantahan.example/catalog/manifest.json` shows the new version, then
4. **Resume**: `docker compose run --rm ingest resume`.

Phones that already hold the old songs replace them at their next update; until then they are hidden by the pause. `rollback` refuses any version that predates a withdrawal.

## Backup and restore

`backup` writes a folder `kantahan-<time>/` holding a consistent copy of the database (safe while a run is writing), a tar of the published catalog and SHA-256 sums, and prunes to the newest 14. Downloaded PDFs are not included; they can be fetched again. Keep the backup folder (`BACKUP_DIR`, default `deploy/backups`) on another disk or copy it off the server.

```bash
docker compose run --rm ingest backup --to /backups --keep 14
docker compose run --rm ingest restore /backups/kantahan-20261101T023000Z          # explains, changes nothing
docker compose run --rm ingest restore /backups/kantahan-20261101T023000Z --yes
```

Restore checks the sums and the database first, refuses unsafe archive members, keeps what it replaces under `before-restore-<time>/` in the work volume (never in the served folder), and swaps the manifest in last. **A restored database may predate withdrawals made later**: look at them again before publishing, and `suspend` first if in doubt.

**Restore drill** (do it once on a new server, and after big changes): back up, remove the published files, restore, and confirm the site serves the same manifest and that `publish` then says `unchanged`. `deploy/test/smoke.sh` runs this drill on every CI build with synthetic data.

## Security notes

- Secrets live only in `deploy/.env` (mode 600, never committed). The destination address `CONTACT_TO` is in no image, response or log. `SMTP_PASSWORD_FILE` is supported for Docker secrets.
- Everything is self-hosted: the page makes no third-party requests, and the Content-Security-Policy forbids them. See [security.md](security.md) for the full list of controls.
- No public endpoint can change, pause or remove the catalog. Those commands run on the server.
