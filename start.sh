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
echo "Local site: http://127.0.0.1:8795"
echo "Public site, once Pages is enabled: https://joeypbrrr.github.io/trenchfloor/floor/"
