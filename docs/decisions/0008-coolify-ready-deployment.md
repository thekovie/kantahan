# 0008: A deployment shaped for Coolify

Status: accepted, 2026-10-24. Builds on [0005](0005-production-deployment.md).

## Context

The owner deploys through Coolify. Its Docker Compose build pack checks out the repository, builds the compose file and routes a domain to a service over its own Docker network. Its documentation says to publish no host ports, keeps settings in an Environment Variables screen instead of a `.env` file, and runs Scheduled Tasks as commands inside a *running* container. The first version of the stack assumed a plain Docker host: it needed a `.env` file, published a port on the host, kept the catalog job out of `up` with a compose profile, and used a host folder for backups that needed a manual `chown`.

## Decision

- **No `.env` file.** The contact service's settings are listed under `environment:` in the compose file. Required ones use `${NAME:?message}`, so Coolify shows them as fields and refuses to deploy until they are filled in; the rest have defaults. Plain Docker still reads `.env` for the same substitutions.
- **No published port.** `web` only exposes 8080 on the Docker network. Plain Docker gets a host port from `compose.hostport.yml`, loaded through `COMPOSE_FILE` in `.env.example`; Coolify never reads that file.
- **A catalog job container that idles.** `ingest` is always running (`kc idle`, started with `init: true`) so a scheduled task has a container to run in. A short wrapper, `kc`, fills in the tool's paths: `kc run`, `kc backup --to /backups`. The old `docker compose run --rm ingest run` still works.
- **Backups in a named volume**, which the image creates owned by the job's user, so the manual `chown` is gone.
- **Where Coolify looks.** Coolify runs `docker compose --project-directory <the base directory> -f <base directory + location>`, so relative paths resolve from the base directory. The first version of this record guessed Base Directory `/deploy` and a build context of `..`; the first real deploy (Base Directory `/`) failed with `lstat /artifacts/deploy`. The build context is now `${BUILD_ROOT:-.}`: `.` is the repository root when Coolify runs it (Base Directory `/`, Location `/deploy/docker-compose.yml`), and `.env` sets `BUILD_ROOT=..` for plain Docker run from `deploy/`.
- **Coolify guide** in `docs/deployment.md`: variables, domain with the `:8080` suffix, first catalog, the three scheduled tasks with their timeouts, takedowns from the Terminal, copying backups off the server, updates.

## Consequences

- The smoke test builds an image the way Coolify runs compose (repository root as project directory, no `.env`) and checks all three build contexts, which would have caught the failed deploy. It also renders the compose file with `--env-file /dev/null` (a required setting missing must stop the deploy and be named; the required ones alone must be enough), checks that no host port is published, that the job container stays running, and that `kc` runs jobs in it. Backups are tested on the real default volume.
- One more idle container (a sleeping process, a few MB).
- Not verified: a deploy on a live Coolify server. The behaviour relied on comes from Coolify's documentation (no published ports, domain port suffix, scheduled tasks inside a running container, `${VAR:?}` blocking deploys). If a screen differs, the guide is the place to fix.
