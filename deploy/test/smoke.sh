#!/usr/bin/env bash
# Builds the production images, starts the stack with a throwaway SMTP sink, and checks what a
# real deployment must get right: headers, caching, the contact path, container hardening, and
# the backup and restore drill. Needs Docker. Uses synthetic data only. Usage: deploy/test/smoke.sh
set -u  # no pipefail on purpose: `grep -q` closes its pipe early and would be reported as a failure
cd "$(dirname "$0")/.."

PROJECT=kantahan-smoke
BASE=http://localhost:18080
BACKUPS="$(mktemp -d)"
chmod 777 "$BACKUPS" # the job runs as uid 10001 and must be able to write here, as on a real server
export BACKUP_DIR="$BACKUPS"
[ -f .env ] || cp .env.example .env
COMPOSE=(docker compose -p "$PROJECT" -f docker-compose.yml -f test/compose.test.yml)
dc() { "${COMPOSE[@]}" "$@"; }
failures=0
check() { # check "what" command...
  local what="$1"
  shift
  if "$@" >/dev/null 2>&1; then echo "  ok    $what"; else echo "  FAIL  $what"; failures=$((failures + 1)); fi
}
header_of() { curl -sS -o /dev/null -D - "$@" | tr -d '\r'; }
has_header() { header_of "${@:2}" | grep -qiE "$1"; }
status_of() { curl -sS -o /dev/null -w '%{http_code}' "$@"; }
post() { curl -sS -o /dev/null -w '%{http_code}' -X POST "$BASE/api/contact" -H 'Content-Type: application/json' -H "Origin: $1" -d "$2"; }
cleanup() {
  dc down --volumes --remove-orphans >/dev/null 2>&1
  rm -r -f "$BACKUPS"
}
trap cleanup EXIT

sink_has() { dc logs smtp-sink 2>/dev/null | grep -q -- "$1"; }
contact_log_clean() { ! dc logs contact 2>/dev/null | grep -qE 'tester@example|Smoke Tester|00001'; }
not_writable() { ! dc exec -T "$1" sh -c "touch $2" 2>/dev/null; }
runs_as_non_root() { [ "$(dc exec -T "$1" id -u)" != 0 ]; }
no_published_port() { [ -z "$(docker port "$(dc ps -q contact)" 2>/dev/null)" ]; }
destination_hidden() { ! { curl -s "$BASE/"; curl -s "$BASE/rights"; curl -s "$BASE$JS"; } | grep -q owner-private; }
server_version_hidden() { ! curl -sI "$BASE/" | grep -iE '^server: nginx/'; }
manifest_is_seeded() { curl -s "$BASE/catalog/manifest.json" | grep -q '"version": "v1"'; }
backup_has_files() { [ "$(find "$BACKUPS" -type f \( -name catalog.sqlite -o -name publish.tar.gz -o -name checksums.sha256 \) | wc -l)" -eq 3 ]; }
restore_asks() { dc run --rm -T ingest restore "/backups/$NEWEST" >/dev/null 2>&1; [ $? -eq 2 ]; }

echo "== build and start"
cleanup_stack() { dc down --volumes --remove-orphans >/dev/null 2>&1; }
cleanup_stack # a leftover stack would carry old rate-limit counters and volumes
dc build web contact ingest >/dev/null || { echo "build failed"; exit 1; }
dc up -d --wait web contact smtp-sink >/dev/null || { echo "start failed"; dc logs | tail -20; exit 1; }
dc run --rm -T --entrypoint python ingest - < test/seed_catalog.py >/dev/null

echo "== web: headers and caching"
check "home is served" test "$(status_of $BASE/)" = 200
check "CSP forbids third parties" has_header "content-security-policy: default-src 'self'" $BASE/
check "no framing" has_header "x-frame-options: deny" $BASE/
check "nosniff" has_header "x-content-type-options: nosniff" $BASE/
check "HSTS" has_header "strict-transport-security" $BASE/
check "shell is revalidated" has_header "cache-control: no-cache" $BASE/
JS=$(curl -s $BASE/ | grep -oE '/assets/[^"]+\.js' | head -1)
check "hashed assets are immutable" has_header "cache-control: public, max-age=31536000, immutable" "$BASE$JS"
check "hashed assets keep the security headers" has_header "content-security-policy" "$BASE$JS"
check "service worker is never cached" has_header "cache-control: no-cache" $BASE/sw.js
check "catalog manifest is revalidated" has_header "cache-control: no-cache, must-revalidate" $BASE/catalog/manifest.json
check "catalog versions are immutable" has_header "cache-control: public, max-age=31536000, immutable" $BASE/catalog/v1/reyna.json
check "unknown catalog file is a 404" test "$(status_of $BASE/catalog/nope.json)" = 404
check "catalog folder is not listed" test "$(status_of $BASE/catalog/)" = 404
check "app routes fall back to the shell" test "$(status_of $BASE/rights)" = 200
check "the manifest is the seeded catalog" manifest_is_seeded
check "server version is hidden" server_version_hidden

echo "== browser: the strict policy against the real stack"
if [ -d ../apps/web/node_modules/@playwright/test ]; then
  check "the app works in a real browser under the policy" node test/stack-e2e.mjs "$BASE"
  check "that request's mail reached the sink" sink_has 'Subject: \[Kantahan\] Removal request'
else
  echo "  skip  browser checks (run npm ci in apps/web first)"
fi

echo "== contact: through nginx to mail"
OK='{"type":"correction","message":"Song 00001 lists the wrong artist in this smoke test.","email":"tester@example.org","name":"Smoke Tester","reference":"Reyna, 00001","website":""}'
check "a valid request is accepted" test "$(post $BASE "$OK")" = 202
check "the mail reached the sink" sink_has 'Subject: \[Kantahan\] Correction request'
check "the mail went to the private address" sink_has 'To: owner-private@example.net'
check "another origin is refused" test "$(post https://evil.example "$OK")" = 403
check "a filled trap looks accepted" test "$(post $BASE '{"type":"other","message":"A bot filled the hidden field here.","website":"http://spam"}')" = 202
check "invalid input is rejected" test "$(post $BASE '{"type":"x","message":"short"}')" = 422
check "the limit is enforced" test "$(post $BASE "$OK")" = 429
check "the destination address is not exposed" destination_hidden
check "logs hold no message text or address" contact_log_clean

echo "== containers: hardening"
for svc in web contact; do
  check "$svc runs as a non-root user" runs_as_non_root "$svc"
  check "$svc has a read-only root filesystem" not_writable "$svc" /probe
done
check "the contact port is not published on the host" no_published_port
check "the catalog volume is read-only for the web" not_writable web /usr/share/nginx/html/catalog/probe

echo "== backup and restore drill (in containers)"
dc run --rm -T ingest migrate >/dev/null
check "a backup is written" dc run --rm -T ingest backup --to /backups
check "the backup folder has its three files" backup_has_files
NEWEST=$(ls "$BACKUPS" | head -1)
BEFORE=$(curl -s $BASE/catalog/manifest.json | shasum | cut -c1-12)
dc run --rm -T --entrypoint sh ingest -c 'find /data/publish -mindepth 1 -delete' >/dev/null
check "the catalog is really gone" test "$(status_of $BASE/catalog/manifest.json)" = 404
check "restore asks for confirmation" restore_asks
check "restore succeeds with --yes" dc run --rm -T ingest restore "/backups/$NEWEST" --yes
AFTER=$(curl -s $BASE/catalog/manifest.json | shasum | cut -c1-12)
check "the restored catalog is identical" test "$BEFORE" = "$AFTER"

echo
if [ "$failures" -eq 0 ]; then echo "smoke test passed"; else echo "$failures check(s) failed"; fi
exit "$failures"
