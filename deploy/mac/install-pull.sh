#!/usr/bin/env bash
# Install the daily pull of the server's backups onto this Mac.
#
#   deploy/mac/install-pull.sh        # install or update, then run once
#   launchctl bootout gui/$(id -u)/de.w3rth.ninanatur.pull-backups   # remove
#
# The script is copied out of the repository, so switching branches or moving
# the checkout cannot silently stop the backups. Runs daily at 09:30; launchd
# runs a missed slot when the Mac wakes.
set -euo pipefail

LABEL="de.w3rth.ninanatur.pull-backups"
HOME_DIR="$HOME/Backups/ninanatur"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME_DIR/bin"
install -m 755 "$(dirname "$0")/pull-backups.sh" "$HOME_DIR/bin/pull-backups.sh"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$HOME_DIR/bin/pull-backups.sh</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
  <key>StandardOutPath</key><string>$HOME_DIR/pull.log</string>
  <key>StandardErrorPath</key><string>$HOME_DIR/pull.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart "gui/$(id -u)/$LABEL"
echo "installed $LABEL — log: $HOME_DIR/pull.log"
