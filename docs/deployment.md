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

- Docker Engine with Compose v2 (`docker compose version`), at least 5 GB of free disk (see [Disk use](#disk-use); a 60 GB server is far more than enough), and outbound internet access for the catalog job.
- A domain with HTTPS handled by a reverse proxy (Coolify does this for you, see [Deploying with Coolify](#deploying-with-coolify); otherwise Caddy, Traefik or nginx, examples below).
- An SMTP account that can send mail (a mail provider's relay, or a local relay). Port 587 with STARTTLS is the default.

## First-time setup (plain Docker)

Using Coolify? Skip to [Deploying with Coolify](#deploying-with-coolify).

```bash
git clone https://github.com/thekovie/kantahan.git && cd kantahan/deploy
cp .env.example .env && chmod 600 .env      # then edit it: see configuration.md
docker compose build
docker compose up -d                         # web, contact, and the idle catalog job container
docker compose ps                            # web and contact should become "healthy"
```

Build the first catalog. It downloads about 800 MB politely (one request every few seconds) and takes roughly an hour; it can be interrupted and resumed:

```bash
docker compose exec ingest kc run --manual    # `kc` is the short name of the catalog tool inside the job container
docker compose exec ingest kc stats           # what was imported
```

`docker compose run --rm ingest run --manual` does the same in a throwaway container.

Then open your site. Until the first catalog is published the app says the songs did not load.

## Deploying with Coolify

Coolify gives you the proxy, the certificates, the environment screen and scheduled tasks, so nothing outside the repository is needed. The stack is shaped for it: no `.env` file, no published ports, and a catalog job container that stays running for scheduled tasks to use. (This was checked against Coolify's documentation and the compose file is exercised by the smoke test; it has not been deployed on a live Coolify server, so tell me if a screen differs in your version.)

1. **New resource.** Add the Git repository (`thekovie/kantahan`, branch `main`) and choose the **Docker Compose** build pack. Set **Base Directory** to `/deploy` and **Docker Compose Location** to `/docker-compose.yml`. (The compose file builds from `..`, the repository root; with the base directory set to `/deploy` the compose file's folder and the base directory are the same place, so it resolves the same either way.)
2. **Environment variables.** Coolify reads the compose file and lists the variables. These block the deploy until they have a value: `ALLOWED_ORIGINS` (the exact address people open, such as `https://kantahan.example`, no trailing slash), `CONTACT_TO`, `SMTP_HOST` and `SMTP_FROM`. Add `SMTP_USER` and `SMTP_PASSWORD` if your mail relay needs a login, and mark the password as a secret. The rest have defaults ([configuration.md](configuration.md)). Do not set `COMPOSE_FILE` or `WEB_BIND`: they are only for plain Docker.
3. **Domain.** In the resource's **Domains**, for the `web` service enter `https://kantahan.example:8080`. The `:8080` tells Coolify's proxy which container port to send traffic to. Give `contact` and `ingest` no domain. Do not publish ports: Coolify warns that a published port bypasses its proxy.
4. **Deploy.** Coolify uses the images' own health checks (`web` answers `/healthz`, `contact` answers `/api/health`). The visitor's address reaches the web container through Coolify's proxy from a private Docker address, so the form's rate limit counts real visitors. If you put Cloudflare's proxy in front of Coolify, read the proxy layouts under [Reverse proxy](#reverse-proxy).
5. **First catalog.** Open the resource's **Terminal**, choose the `ingest` container and run `kc run --manual`. It downloads about 800 MB politely and takes roughly an hour. If the terminal disconnects, run it again: it skips what it already has. Until it finishes the app says the songs did not load.
6. **Scheduled tasks.** In **Scheduled Tasks** add these, each with **Container name** `ingest` (the compose service name). Coolify runs them inside that container and uses the server's timezone. The default timeout is 300 seconds, too short for a catalog pass, so set the timeouts below.

   | Name | Command | Frequency | Timeout |
   |---|---|---|---|
   | Catalog run | `kc run` | `15 3 * * *` | `36000` |
   | Source audit | `kc audit` | `45 3 1 * *` | `36000` |
   | Backup | `kc backup --to /backups --keep 14` | `30 2 * * *` | `600` |

   The run decides for itself whether it is due (every 14 days) and stops with exit 2 when less than 1 GB of disk is free. Failures show under **Recent executions** (exit 1: an error or a partly done run; exit 2: a safety gate or the disk guard stopped it).
7. **Takedowns and other admin jobs** run from the same Terminal: `kc suspend --notice "..."`, `kc withdraw --release "Volume 64"`, `kc resume` ([Takedown](#takedown-pause-remove-resume)).
8. **Backups** are written to the `catalog-backups` volume, which stays on the server. Copy them off it now and then: find the volume with `docker volume ls | grep catalog-backups`, then `docker run --rm -v <that volume>:/b -v "$PWD":/out alpine tar czf /out/kantahan-backups.tgz -C /b .` and download the file.
9. **Updates.** A push to `main` redeploys (enable automatic deploy or use the webhook). The catalog, database and backups are in volumes, so they survive redeploys. Base images are not refreshed automatically: redeploy without the build cache now and then. Coolify's server settings can also clean unused Docker images and build cache on a schedule; turn that on (the build cache is the one thing that grows without a limit, see [Disk use](#disk-use)).

## Reverse proxy

The proxy must terminate HTTPS and forward to `web`. It must **append the visitor's address to `X-Forwarded-For`** (every common proxy does by default) so the rate limit counts visitors, not the proxy. Keep `WEB_BIND` on `127.0.0.1` (or a private network; it applies to plain Docker only): if the web port were reachable directly from the internet, a visitor could spoof that header.

Supported layouts, and what goes wrong otherwise:

- **The proxy reaches `web` from a private or loopback address** (same host, or a private network): works as described. The web container trusts `X-Forwarded-For` only from private ranges (`10/8`, `172.16/12`, `192.168/16`, loopback, IPv6 unique-local) and takes the right-most address that is not one of those.
- **The proxy is on a public address** (a CDN, or a load balancer on another host): its address is not trusted, so every visitor looks like one address and one bot can use up the form's limit for everyone. Add that proxy's address range as a `set_real_ip_from` line in `deploy/web/nginx.conf` and rebuild.
- **Docker Desktop, or `WEB_BIND=0.0.0.0`:** connections can arrive from the Docker gateway (a private address, so trusted), which lets a visitor forge the header. Use these only on a development machine.

IPv6 visitors are grouped by their /64 network (one person can use any address in it), both by nginx and by the contact service.

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
| Logs | `docker compose logs -f web contact` (rotated: 3 files of 10 MB each per container), and `/var/log/kantahan/ingest-*.log` for cron jobs |
| Disk use | `docker system df -v`, and see [Disk use](#disk-use) below |

Base images are not updated automatically: rebuild now and then (`docker compose build --pull && docker compose up -d`).

## Disk use

Measured on the real catalog (12 machines, 78,141 songs) on 2026-10-24. Nothing here grows without a limit except the Docker build cache, which you clear by hand.

| What | Size | Growth |
|---|---|---|
| Source PDFs (`work/pdfs`) | about 815 MB in 363 files (largest 38 MB) | One file per source link. A run skips files it already has and `fetch --refresh` overwrites in place, so the same document is never stored twice. It grows only when the publisher adds a new link (about 2 MB each). Files for links that later disappear stay until you delete them. |
| Database | about 9 MB | Slow. |
| Published catalog | 3.4 MB per version | The newest 5 versions are kept: about 17 MB. |
| Backups | about 11 MB each (no PDFs) | The newest 14 are kept: about 155 MB. |
| Cron job logs | at most 5 MB per job, plus one rotated copy | Bounded by the wrapper. |
| Container logs | at most 30 MB per container (3 files of 10 MB) | Bounded. |
| Docker images | web 78 MB, contact 225 MB, ingest 293 MB | Replaced on rebuild. |
| Docker build cache | **grows with every rebuild** | Not bounded. After many rebuilds on a development machine it reached 8.5 GB. |
| `before-restore-*` folders in the work volume | a database copy each | One per restore, never removed automatically. Delete them once a restore is confirmed. |

The steady total is about 2 GB, so a 60 GB disk has plenty of room. To keep it that way:

- After you rebuild or update, run `docker builder prune -f` and `docker image prune -f` (or put them in a monthly cron job).
- The scheduled `run` refuses to download anything when less than 1 GB is free on the work volume. It stops with exit 2 (`blocked`), cron mails the message, and nothing is left half-written. Change the floor with `run --min-free-mb N`.
- To get the 815 MB back you can delete `work/pdfs`: they can be downloaded again by `fetch`, and are only needed again for `import --reimport` and for checking a changed file.

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

`backup` writes a folder `kantahan-<time>/` holding a consistent copy of the database (safe while a run is writing), a tar of the published catalog and SHA-256 sums, and prunes to the newest 14. Downloaded PDFs are not included; they can be fetched again. Backups go to the `catalog-backups` Docker volume; copy them off the server now and then (command below).

```bash
docker compose exec ingest kc backup --to /backups --keep 14
docker compose exec ingest kc restore /backups/kantahan-20261101T023000Z          # explains, changes nothing
docker compose exec ingest kc restore /backups/kantahan-20261101T023000Z --yes
# copy the backups off the server (the volume is named after the compose project):
docker run --rm -v kantahan_catalog-backups:/b -v "$PWD":/out alpine tar czf /out/kantahan-backups.tgz -C /b .
```

Restore is built so that it cannot undo a takedown. Before replacing anything it reads the live server's withdrawn releases, event log, publication counter, live manifest and pause, and carries them into the restored database. Then:

- it refuses any version folder at or below the last withdrawal or the live version (they may still contain withdrawn songs), and never replaces a folder that is already being served;
- when something is already live it leaves the live manifest, and its pause, exactly as it is; on a bare server it uses the backup's manifest byte for byte, after re-checking every bundle against its checksum;
- it checks the backup's sums and database, refuses unsafe archive members and archives that are too large, stages everything under the work volume (never in the served folder), and keeps what it replaces in `before-restore-<time>/` there (private, mode 600);
- the restored database is swapped in last, so a failure earlier leaves the old one untouched.

If the current database cannot be read (the usual reason to restore), takedowns made after the backup cannot be carried over, and the command says so. In that case `suspend` first and check recent withdrawals by hand before publishing.

**Restore drill** (do it once on a new server, and after big changes): back up, remove the published files, restore, and confirm the site serves the same manifest and that `publish` then says `unchanged`. `deploy/test/smoke.sh` runs this drill on every CI build with synthetic data, and the unit tests cover the takedown cases (a withdrawal and a pause made after the backup both survive a restore).

## Security notes

- Secrets live only in `deploy/.env` (mode 600, never committed). The destination address `CONTACT_TO` is in no image, response or log. `SMTP_PASSWORD_FILE` is supported for Docker secrets.
- Everything is self-hosted: the page makes no third-party requests, and the Content-Security-Policy forbids them. See [security.md](security.md) for the full list of controls.
- No public endpoint can change, pause or remove the catalog. Those commands run on the server.
