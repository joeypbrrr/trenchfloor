#!/bin/bash
cd "$(dirname "$0")" || exit 1
mkdir -p logs
trap 'kill "$child" 2>/dev/null; exit 0' TERM INT
while true; do
  python3 -u live_server.py >>logs/live.log 2>&1 &
  child=$!
  wait "$child"
  echo "$(date -Is) live server exited; restarting in 3s" >>logs/live.log
  sleep 3
done
