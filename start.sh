#!/bin/bash
# Start the paper-research loop and the local read-only site.
cd "$(dirname "$0")" || exit 1
mkdir -p logs data/ledger data/cache
start_one() {
  local name="$1"
  local script="$2"
  if [[ -f "$name.pid" ]] && kill -0 "$(cat "$name.pid")" 2>/dev/null; then
    echo "$name already running ($(cat "$name.pid"))"
    return 0
  fi
  setsid bash "$script" </dev/null >>"logs/$name-wrapper.log" 2>&1 &
  echo $! >"$name.pid"
  echo "started $name pid $(cat "$name.pid")"
}
start_one research ./run_research.sh
start_one server ./run_server.sh
if python3 -c 'import json,sys; sys.exit(0 if json.load(open("config.json")).get("pumpportal", {}).get("collector_enabled", False) else 1)'; then
  start_one pumpportal ./run_pumpportal.sh
else
  echo "PumpPortal collector OFF (no launch feed connection started)"
fi
echo "Local site: http://127.0.0.1:8795"
echo "Public site: https://joeypbrrr.github.io/trenchfloor/ (design mockup at /preview/)"
