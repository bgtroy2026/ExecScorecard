#!/bin/bash
# Run by the daily scheduled job (launchd opens this in Terminal, which already has access to Documents).
# Rebuilds the numbers and publishes without waiting for a key press; output goes to _deploy/auto_deploy.log.
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/auto_deploy.log"
{ echo; echo "=== Auto deploy $(date '+%Y-%m-%d %H:%M:%S') ==="; } >> "$LOG"
/bin/bash "$DIR/deploy.sh" "Auto-update ExecScorecard $(date '+%Y-%m-%d')" --quiet < /dev/null
RC=$?
tail -n 40 "$DIR/deploy_last.log" >> "$LOG"
echo "exit $RC" >> "$LOG"
exit $RC
