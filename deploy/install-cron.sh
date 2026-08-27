#!/usr/bin/env bash
# Install (or refresh) NinaNatur's entries in root's crontab.
#
#   sudo deploy/install-cron.sh
#
# Idempotent: existing NinaNatur lines are removed before the current ones are
# appended, so re-running never duplicates. The previous crontab is backed up
# first — this edits the file that also drives battlefuel, funding-tender-tracker
# and 3dmap2, so a mistake here takes three other deploys down with it.
set -uo pipefail

[ "$(id -u)" -eq 0 ] || { echo "✖ run with sudo — these lines belong in root's crontab" >&2; exit 1; }

ROOT=/opt/ninanatur
[ -d "$ROOT" ] || { echo "✖ $ROOT does not exist" >&2; exit 1; }

# The leading sleep staggers this deploy against the others. Each project's
# auto-deploy.sh holds its own lock, which guards only against itself — the
# offsets are what stop every project pulling from GHCR in the same second.
# Taken on this host: :00 battlefuel, :30 funding-tender-tracker, :45 3dmap2.
OFFSET=15
LOG=/var/log/ninanatur-deploy.log

BACKUP="/root/crontab.backup.$(date +%Y%m%d-%H%M%S)"
crontab -l >"$BACKUP" 2>/dev/null || : >"$BACKUP"

{
  grep -v "$ROOT" "$BACKUP" || true
  for env in prod dev; do
    if [ -f "$ROOT/deploy/.env.$env" ]; then
      echo "* * * * * sleep $OFFSET; cd $ROOT && /usr/bin/env bash deploy/auto-deploy.sh deploy/.env.$env >> $LOG 2>&1"
    else
      echo "  ⚠ skipping $env — $ROOT/deploy/.env.$env not found" >&2
    fi
  done
} | crontab -

echo "Backup: $BACKUP"
echo "--- root crontab now ---"
crontab -l
