#!/bin/bash
# Double-click once: publishes the Executive Scorecard every day at 6:47 AM (and right now).
# Undo any time with "Uninstall Auto-Deploy.command".
set -e
PROJECT="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.biggrove.execscorecard.deploy"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
chmod +x "$PROJECT/_deploy/Auto Deploy.command"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/open</string><string>-g</string><string>-a</string><string>Terminal</string>
    <string>$PROJECT/_deploy/Auto Deploy.command</string>
  </array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>47</integer></dict>
  <key>RunAtLoad</key><false/>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Daily auto-deploy is on: every day at 6:47 AM (if the Mac is asleep, it runs when it wakes)."
echo "Publishing now..."
launchctl kickstart "gui/$(id -u)/$LABEL"
echo "A Terminal window will run the deploy. Log: _deploy/auto_deploy.log"
sleep 3
