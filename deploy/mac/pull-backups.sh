#!/usr/bin/env bash
# The off-host copy — Wave 20, feature 4, third layer.
#
# Pulls the host's backups (deploy/backup.sh, nightly at 03:17) onto this Mac,
# so a lost server does not take every copy with it. Pulled rather than pushed:
# the server holds no key to the Mac, so a compromised server cannot reach it.
#
# Run by launchd (see install-pull.sh), which catches up a run the Mac slept
# through. Nothing is deleted on the server; here the newest KEEP stay.
set -euo pipefail

HOST="${NINANATUR_HOST:-jan@159.195.148.193}"
KEY="${NINANATUR_KEY:-$HOME/.ssh/id_ed25519}"
DEST="${NINANATUR_MAC_BACKUPS:-$HOME/Backups/ninanatur}"
KEEP="${NINANATUR_MAC_KEEP:-90}"

log() { printf '%s [pull] %s\n' "$(date -u +%FT%TZ)" "$*"; }

for env in prod dev; do
  mkdir -p "$DEST/$env"
  rsync -a -e "ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=20" \
    "$HOST:backups/ninanatur/$env/" "$DEST/$env/"
  newest=$(ls -1 "$DEST/$env"/*.sqlite.gz 2>/dev/null | sort | tail -1 || true)
  if [ -z "$newest" ]; then log "✖ $env: nothing pulled"; exit 1; fi
  gzip -t "$newest" || { log "✖ $env: $(basename "$newest") is not a sound gzip"; exit 1; }
  # macOS head takes no negative count: work out how many are surplus instead.
  count=$(ls -1 "$DEST/$env"/*.sqlite.gz | wc -l | tr -d ' ')
  if [ "$count" -gt "$KEEP" ]; then
    ls -1 "$DEST/$env"/*.sqlite.gz | sort | head -n "$((count - KEEP))" | while read -r old; do rm -- "$old"; done
  fi
  log "$env: newest $(basename "$newest"), $(ls -1 "$DEST/$env"/*.sqlite.gz | wc -l | tr -d ' ') on this Mac"
done
