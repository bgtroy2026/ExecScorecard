#!/bin/bash
# Double-click to turn off the daily Executive Scorecard publish.
LABEL="com.biggrove.execscorecard.deploy"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Daily auto-deploy is off."
sleep 2
