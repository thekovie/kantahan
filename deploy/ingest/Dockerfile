# The catalog job: discover, fetch, import, publish, backup. The container idles (`kc idle`) and jobs run in it
# (`kc run`, from Coolify's Scheduled Tasks, `docker compose exec`, or as a one-off `docker compose run`).
# Build from the repository root: docker build -f deploy/ingest/Dockerfile .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY catalog/pyproject.toml ./
COPY catalog/src ./src
RUN pip install .
COPY catalog/sources.yaml catalog/display.yaml catalog/reviewed.yaml ./
COPY --chmod=755 deploy/ingest/kc /usr/local/bin/kc
RUN useradd --system --uid 10001 --create-home ingest \
    && mkdir -p /data/work /data/publish /backups \
    && chown -R 10001 /data /backups
USER 10001
VOLUME ["/data/work", "/data/publish", "/backups"]
ENTRYPOINT ["kc"]
CMD ["run"]
