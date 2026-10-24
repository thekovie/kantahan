# The catalog job: discover, fetch, import, publish, backup. Runs on demand, never as a service.
# Build from the repository root: docker build -f deploy/ingest/Dockerfile .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY catalog/pyproject.toml ./
COPY catalog/src ./src
RUN pip install .
COPY catalog/sources.yaml catalog/display.yaml catalog/reviewed.yaml ./
RUN useradd --system --uid 10001 --create-home ingest \
    && mkdir -p /data/work /data/publish /backups \
    && chown -R 10001 /data /backups
USER 10001
VOLUME ["/data/work", "/data/publish", "/backups"]
ENTRYPOINT ["kantahan-catalog", "--work", "/data/work", "--out", "/data/publish", "--sources", "/app/sources.yaml", "--display", "/app/display.yaml", "--reviewed", "/app/reviewed.yaml"]
CMD ["run"]
