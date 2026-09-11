#!/usr/bin/env bash
# Poll GHCR and roll out the newest image for one environment. Run from cron,
# through deploy/roll-all.sh:
#   deploy/auto-deploy.sh deploy/.env.prod   # prod (:4000)
#   deploy/auto-deploy.sh deploy/.env.dev    # dev  (:4001)
#
# Wave 20, feature 7. Until 2026-09-11 this pulled the tag, recreated the
# container and pruned dangling images — which, once the tag had moved, meant
# the image it had just replaced: the only one it could have gone back to.
# Nothing waited for the health check. Now:
#
#   - The image the stack runs is kept, tagged :<tag>-previous, before a new one
#     is started. A tagged image survives the prune.
#   - A new image has HEALTH_WAIT_TRIES × HEALTH_WAIT_SLEEP seconds (default
#     30 × 5) to report healthy — time for the compose healthcheck's probes.
#   - One that does not is rolled back to :<tag>-previous and remembered in
#     deploy/.state/<env>.bad, so the next tick does not roll it forward again:
#     production would otherwise flap between a broken build and a working one
#     once a minute. A different build is tried as soon as one appears.
#   - Every roll names the build it made live by digest, in the cron's output
#     and in deploy/.state/deploy.log.
#
# The host must be logged in to GHCR once (docker login ghcr.io) for private
# pulls — otherwise this fails silently every minute.
# Uses the HOST docker (no Watchtower) so there is never a client-version mismatch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${1:?usage: auto-deploy.sh <env-file> (e.g. deploy/.env.prod)}"
[ -f "$ENV_FILE" ] || { echo "✖ no such env-file: $ENV_FILE" >&2; exit 1; }
NAME="$(basename "$ENV_FILE")"
NAME="${NAME#.env.}"
STATE="${NINANATUR_DEPLOY_STATE:-$ROOT/deploy/.state}"
TRIES="${HEALTH_WAIT_TRIES:-30}"
PAUSE="${HEALTH_WAIT_SLEEP:-5}"

# Serialize across all invocations — cron fires this for prod AND dev. Two
# overlapping runs racing the same image pull corrupt the containerd content
# store, so a single global lock makes a slow pull skip the next tick instead of
# racing it.
exec 9>"${NINANATUR_DEPLOY_LOCK:-/tmp/ninanatur-auto-deploy.lock}"
if ! flock -n 9; then
  echo "auto-deploy: another run holds the lock — skipping this tick"
  exit 0
fi

COMPOSE=(docker compose --env-file "$ENV_FILE" -f deploy/compose.app.yml)
mkdir -p "$STATE"

say() {
  local line
  line="$(date -u +%FT%TZ) [$NAME] $*"
  echo "$line"
  echo "$line" >> "$STATE/deploy.log"
}

container() {
  "${COMPOSE[@]}" ps -q app 2>/dev/null || true
}

running_image() {
  local id
  id="$(container)"
  if [ -n "$id" ]; then docker inspect --format '{{.Image}}' "$id"; fi
}

health() {
  local id
  id="$(container)"
  if [ -z "$id" ]; then echo missing; return; fi
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" \
    2>/dev/null || echo missing
}

wait_healthy() {
  local i
  for ((i = 0; i < TRIES; i++)); do
    case "$(health)" in
      healthy) return 0 ;;
      unhealthy) return 1 ;;
    esac
    sleep "$PAUSE"
  done
  return 1
}

IMAGE="$("${COMPOSE[@]}" config --images app | head -n 1)"   # repo:tag, as the env file names it
TAG="${IMAGE##*:}"
PREVIOUS="${IMAGE%:*}:${TAG}-previous"

"${COMPOSE[@]}" pull --quiet app
new="$(docker image inspect --format '{{.Id}}' "$IMAGE")"
current="$(running_image)"
bad="$(cat "$STATE/$NAME.bad" 2>/dev/null || true)"

if [ "$new" = "$bad" ]; then
  # Failed its health check here already. Stay on what runs — and still apply
  # the compose file, which is also how a configuration change reaches a stack.
  IMAGE_TAG="${TAG}-previous" "${COMPOSE[@]}" up -d app
  exit 0
fi

if [ "$new" = "$current" ]; then
  # Nothing new. `up -d` recreates only when the compose file has changed.
  "${COMPOSE[@]}" up -d app
  exit 0
fi

if [ -n "$current" ]; then
  docker tag "$current" "$PREVIOUS"
fi
"${COMPOSE[@]}" up -d app

if wait_healthy; then
  rm -f "$STATE/$NAME.bad"
  say "live: $(docker image inspect --format '{{index .RepoDigests 0}}' "$IMAGE")"
  # Dangling layers only: the image just replaced is tagged :<tag>-previous.
  docker image prune -f >/dev/null 2>&1 || true
  exit 0
fi

echo "$new" > "$STATE/$NAME.bad"
if [ -z "$current" ]; then
  say "✖ $new did not become healthy, and there is nothing to go back to"
  exit 1
fi
say "✖ $new did not become healthy — rolling back to $current"
IMAGE_TAG="${TAG}-previous" "${COMPOSE[@]}" up -d app
wait_healthy || say "✖ the rollback is not healthy either — this host needs a person"
exit 1
