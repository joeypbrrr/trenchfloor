#!/bin/bash
cd "$(dirname "$0")" || exit 1
mkdir -p logs
names=(live live_tunnel)
if [[ "${1:-}" == "--local-only" ]]; then names=(live); fi
for name in "${names[@]}"; do
  if [[ -f "$name.pid" ]] && kill -0 "$(<"$name.pid")" 2>/dev/null; then
    echo "$name already running"
  else
    setsid bash "run_${name}.sh" </dev/null >>"logs/$name-wrapper.log" 2>&1 &
    echo $! >"$name.pid"
    echo "Started $name pid $!"
  fi
done
echo "Local live dashboard: http://127.0.0.1:8796"
if [[ "${1:-}" == "--local-only" ]]; then
  echo "Tunnel not started (--local-only)."
else
  echo "Public URL: see logs/live-tunnel-current.log; changes if tunnel restarts."
fi
