#!/usr/bin/env bash
# Nightly backup of the production database — Wave 20, feature 4.
#
#   deploy/backup.sh            # prod (the only one worth keeping)
#   deploy/backup.sh dev        # the preview, if ever wanted
#
# Two copies, on purpose, because they protect against different losses:
#
#   1. inside the volume, /data/backups/   — survives a bad migration or a
#      deleted row, and is what the app's own restore reads;
#   2. on the host, outside the volume     — survives the volume itself being
#      removed or recreated, which is the likelier way to lose every garden:
#      a renamed compose project, a `docker volume rm`, a cleanup gone wide.
#
# Neither survives losing the machine. The off-host copy is a separate step —
# see deploy/SERVER-SETUP.md, "Backups".
#
# The copy is taken by SQLite's online backup API inside the running container,
# so it is consistent while the app is serving, and it is checked with
# `PRAGMA integrity_check` before it is kept. Run from jan's crontab, which can
# reach docker without sudo.
set -euo pipefail

ENV="${1:-prod}"
CONTAINER="ninanatur-${ENV}-app-1"
HOST_DIR="${NINANATUR_BACKUP_DIR:-$HOME/backups/ninanatur}/${ENV}"
KEEP_ON_HOST="${NINANATUR_BACKUP_KEEP:-30}"

log() { printf '%s [backup:%s] %s\n' "$(date -u +%FT%TZ)" "$ENV" "$*"; }

docker inspect "$CONTAINER" >/dev/null 2>&1 || { log "✖ no container $CONTAINER"; exit 1; }

# 1. Inside the volume: create, verify, rotate. Prints the new file's path last.
made=$(docker exec "$CONTAINER" python -m ninanatur.ops.backup create --dest /data/backups | tail -1)
case "$made" in /data/backups/*.sqlite.gz) ;; *) log "✖ backup did not report a file: $made"; exit 1;; esac
log "in volume: $made"

# 2. Out of the volume, onto the host.
mkdir -p "$HOST_DIR"
docker cp "$CONTAINER:$made" "$HOST_DIR/" >/dev/null
copy="$HOST_DIR/$(basename "$made")"
[ -s "$copy" ] || { log "✖ host copy missing or empty: $copy"; exit 1; }
log "on host:   $copy ($(du -h "$copy" | cut -f1))"

# Rotate the host copies: newest KEEP_ON_HOST stay. Names sort by time.
ls -1 "$HOST_DIR"/*.sqlite.gz 2>/dev/null | sort | head -n "-$KEEP_ON_HOST" | while read -r old; do
  rm -- "$old" && log "rotated:   $(basename "$old")"
done
log "done — $(ls -1 "$HOST_DIR"/*.sqlite.gz | wc -l) copies on host"
