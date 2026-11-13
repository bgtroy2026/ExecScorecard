#!/bin/bash
# Double-click to preview the scorecard on this Mac at http://localhost:8010 (Ctrl-C to stop).
cd "$(dirname "$0")/site" || exit 1
( sleep 1; open "http://localhost:8010" ) &
exec python3 -m http.server 8010
