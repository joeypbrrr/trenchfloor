#!/bin/bash
cd "$(dirname "$0")" || exit 1
mkdir -p logs
binary="${CLOUDFLARED_BIN:-/workspace/bin/cloudflared}"
if [[ ! -x "$binary" ]]; then echo "Install cloudflared to $binary first"; exit 1; fi
trap 'kill "$child" 2>/dev/null; exit 0' TERM INT
while true; do
  if [[ -s logs/live-tunnel-current.log ]]; then cp logs/live-tunnel-current.log logs/live-tunnel-previous.log; fi
  : >logs/live-tunnel-current.log
  "$binary" tunnel --url http://127.0.0.1:8796 --no-autoupdate >logs/live-tunnel-current.log 2>&1 &
  child=$!
  wait "$child"
  echo "$(date -Is) tunnel exited; restarting in 5s (URL will change)" >>logs/live-tunnel.log
  sleep 5
done
