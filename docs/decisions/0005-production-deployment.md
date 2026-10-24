# 0005: Production deployment

Status: accepted, 2026-10-24

## Context

The app is static, the catalog is a few static files, and the only server-side behaviour needed at request time is relaying a rights request by e-mail. The owner runs a VPS with a reverse proxy already in place, and wants to be able to pause or remove content quickly.

## Decision

- **Docker Compose with three images**: `web` (nginx, static app and catalog), `contact` (a small FastAPI service) and `ingest` (the catalog job, started on demand by cron, never a daemon). The catalog is a volume written by `ingest` and mounted read-only into `web`.
- **The reverse proxy is yours**: the web container listens on loopback by default; snippets for Caddy, nginx and Traefik are documented, with the one requirement that the proxy appends the visitor's address to `X-Forwarded-For`.
- **Contact abuse protection without a third party**: a honeypot field, per-address and overall rate limits, an Origin check and strict validation. No Turnstile or reCAPTCHA (it would add a third-party script and a policy exception); revisit if abuse appears.
- **A strict Content-Security-Policy** with one inline boot script allowed by hash. The inline script makes the first paint faster and, on a first visit only, starts the manifest download early. Preloading the manifest with a `<link>` was tried and rejected: the browser can answer a later explicit check from the preloaded copy, which could hide a pause.
- **Backups are code, not shell**: `backup` and `restore` are tested commands (SQLite online backup, checksums, safe extraction). Restore is designed around takedowns: it keeps the live server's withdrawals, event log, publication counter and pause, refuses version folders that may hold withdrawn songs, and never replaces a served folder.
- **Alerts through cron**: a wrapper prints only failures so `MAILTO` mails real problems. No alerting service.
- **Image base versions are pinned to major/minor tags and rebuilt by hand**; dependency audits run in CI every week.

## Consequences

Simple to run and to reason about, with no database server and no always-on API beyond the contact relay. Rate-limit counts are per process (one worker) and reset on restart. A person must rebuild images to pick up base-image fixes. Hosting, DNS and the SMTP account are the owner's to provide.
