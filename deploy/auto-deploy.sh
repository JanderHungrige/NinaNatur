#!/usr/bin/env bash
# Poll GHCR and roll out the newest image for one environment. Run from cron
# (see deploy/crontab.example):
#   deploy/auto-deploy.sh deploy/.env.prod   # prod (:4000)
#   deploy/auto-deploy.sh deploy/.env.dev    # dev  (:4001)
#
# The host must be logged in to GHCR once (docker login ghcr.io) for private
# pulls — otherwise this fails silently every minute.
# Uses the HOST docker (no Watchtower) so there is never a client-version mismatch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${1:?usage: auto-deploy.sh <env-file> (e.g. deploy/.env.prod)}"
[ -f "$ENV_FILE" ] || { echo "✖ no such env-file: $ENV_FILE" >&2; exit 1; }

# Serialize across all invocations — cron fires this for prod AND dev. Two
# overlapping runs racing the same image pull corrupt the containerd content
# store, so a single global lock makes a slow pull skip the next tick instead of
# racing it.
exec 9>/tmp/ninanatur-auto-deploy.lock
if ! flock -n 9; then
  echo "auto-deploy: another run holds the lock — skipping this tick"
  exit 0
fi

COMPOSE=(docker compose --env-file "$ENV_FILE" -f deploy/compose.app.yml)

# `up -d` recreates the service only when the digest actually changed, so this is
# a cheap no-op on the ticks where nothing new was pushed.
"${COMPOSE[@]}" pull --quiet app
"${COMPOSE[@]}" up -d app

# Reclaim space from superseded image layers.
docker image prune -f >/dev/null 2>&1 || true
