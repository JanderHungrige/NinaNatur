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

# One line, not one per environment. Two lines both carrying the same `sleep`
# fired in the same second and raced auto-deploy.sh's single global lock, and
# `flock -n` makes the loser exit rather than wait — so every minute was a coin
# flip. roll-all.sh does both in order in one process instead.
#
# The line does not name the environments, so adding deploy/.env.dev later needs
# no reinstall: roll-all.sh skips what is not configured.
{
  grep -v "$ROOT" "$BACKUP" || true
  echo "* * * * * sleep $OFFSET; cd $ROOT && /usr/bin/env bash deploy/roll-all.sh >> $LOG 2>&1"
} | crontab -

echo "Backup: $BACKUP"
echo "--- root crontab now ---"
crontab -l
