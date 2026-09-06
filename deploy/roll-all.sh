#!/usr/bin/env bash
# Roll every configured environment, in order, from one cron tick.
#
#   deploy/roll-all.sh
#
# Why this exists rather than one cron line per environment: each line carried
# the same `sleep 15`, so both fired in the same second and raced the single
# global lock in auto-deploy.sh. `flock -n` makes the loser exit rather than
# wait, so every minute was a coin flip and nothing guaranteed fairness — dev
# could go unrolled for an arbitrarily long time while looking configured.
#
# The lock stays global and stays as it is. Two overlapping runs racing the same
# image pull corrupt the containerd content store; that reasoning is right. What
# was wrong was asking two processes to share one lock when one process can do
# both jobs in order.
#
# It is also easier to read at three in the morning than a crontab line
# containing a for-loop, and it can be tested, which a crontab line cannot.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Production first because it matters most. An environment whose env file is
# absent is not configured on this host and is skipped in silence — that is the
# normal state of a host that runs only production.
ENVIRONMENTS=("${@:-prod dev}")
[ "$#" -gt 0 ] || ENVIRONMENTS=(prod dev)

for name in "${ENVIRONMENTS[@]}"; do
  file="deploy/.env.$name"
  [ -f "$file" ] || continue
  if ! /usr/bin/env bash deploy/auto-deploy.sh "$file"; then
    # Stop rather than carry on. If production could not be rolled, the reason
    # is usually the registry or the daemon, and trying the next environment
    # against the same broken thing only fills the log.
    echo "roll-all: $name failed — stopping, the rest will be tried next tick" >&2
    exit 1
  fi
done
