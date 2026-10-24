#!/usr/bin/env bash
# Runs one catalog job for cron: logs everything, stays silent when it works, and prints the tail
# of the log when it fails, so cron's MAILTO (or any log watcher) sees only real problems.
#   deploy/scripts/cron-job.sh run          (the scheduled pass)
#   deploy/scripts/cron-job.sh audit        (monthly re-hash of the source documents)
#   deploy/scripts/cron-job.sh backup --to /backups --keep 14
# Environment: KANTAHAN_LOG_DIR (default /var/log/kantahan)
set -u
cd "$(dirname "$0")/.."
LOG_DIR="${KANTAHAN_LOG_DIR:-/var/log/kantahan}"
if ! mkdir -p "$LOG_DIR" 2>/dev/null || [ ! -w "$LOG_DIR" ]; then
  # Say so loudly (cron mails this) rather than logging to a predictable shared path.
  echo "kantahan cron: cannot write logs to $LOG_DIR; create it or set KANTAHAN_LOG_DIR" >&2
  exit 1
fi
LOG="$LOG_DIR/ingest-$1.log"
{
  echo "=== $(date -u +%FT%TZ) kantahan-catalog $*"
  docker compose run --rm -T ingest "$@"
  echo "=== exit $?"
} >>"$LOG" 2>&1
STATUS=$(tail -n 1 "$LOG" | sed -n 's/^=== exit \([0-9]*\)$/\1/p')
if [ "${STATUS:-1}" != 0 ]; then
  echo "kantahan-catalog $* failed (exit ${STATUS:-unknown}); last lines of $LOG:"
  tail -n 40 "$LOG"
  exit "${STATUS:-1}"
fi
