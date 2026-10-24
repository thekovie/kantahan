# The web image: the built PWA served by nginx. The catalog is not in the image; it is a volume
# written by the ingest job and mounted read-only at /usr/share/nginx/html/catalog.
# Build from the repository root: docker build -f deploy/web/Dockerfile .
FROM node:22-alpine AS build
WORKDIR /src/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
# The demo catalog and any local real catalog are excluded by .dockerignore.
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY deploy/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/web/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /src/apps/web/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
