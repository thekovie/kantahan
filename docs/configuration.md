# Configuration

> **Status: implemented (M5).** Secrets and addresses come from environment variables only and never appear in the repository, the images, the frontend bundle or any response. `deploy/.env.example` documents every variable; copy it to `deploy/.env` (mode 600, gitignored).

## Contact service

Read by the `contact` container from `deploy/.env`. The service refuses to start when a required setting is missing or malformed, and says which.

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `ALLOWED_ORIGINS` | yes | | The exact public address(es), comma-separated, such as `https://kantahan.example`. Requests from any other origin get 403. `http://localhost:<port>` is accepted for local development only. |
| `CONTACT_TO` | yes | | The single address that receives requests. Never exposed. |
| `SMTP_HOST` | yes | | Mail server. |
| `SMTP_FROM` | yes | | Sender, as `address` or `Name <address>`. |
| `SMTP_PORT` | no | `587` | |
| `SMTP_SECURITY` | no | `starttls` | `starttls`, `ssl` (port 465) or `none` (a local relay only). |
| `SMTP_USER`, `SMTP_PASSWORD` | no | | Login; the password is required when a user is set. `SMTP_PASSWORD_FILE` reads it from a file (Docker secrets). |
| `RATE_PER_IP_HOUR` | no | `5` | Requests per visitor address per hour. |
| `RATE_GLOBAL_HOUR` | no | `60` | Requests per hour for everyone together. |
| `MAX_MESSAGE_CHARS` | no | `2000` | Longest message. |
| `TRUST_PROXY_HEADERS` | no | `false` (`true` in the compose file) | Use `X-Real-IP` for the visitor address. Only the web container can reach the service, and it sets that header itself. |

## Compose

| Variable | Default | Meaning |
|---|---|---|
| `WEB_BIND` | `127.0.0.1:8080` | Where the web container listens on the host. Keep it on loopback or a private network. |
| `BACKUP_DIR` | `./backups` | Host folder mounted at `/backups` in the ingest job. |

## Catalog job

`ingest` runs `kantahan-catalog` with `--work /data/work --out /data/publish` and three files baked into the image from `catalog/`:

| File | Purpose |
|---|---|
| `sources.yaml` | the approved source pages |
| `display.yaml` | which machine groups are published, how each is named and coloured |
| `reviewed.yaml` | documents a person checked and accepted despite a validation rule (blank artists), keyed by file hash |

Changing them means rebuilding the `ingest` image. Command line options and exit codes: [setup-development.md](setup-development.md) and [catalog-updates.md](catalog-updates.md).

## Web app build

`VITE_CATALOG_BASE` (default `/catalog`) is read at build time. The images use the default; change it only if the catalog is served from another path, and rebuild `web`.
