#!/bin/bash
cd "$(dirname "$0")" || exit 1
for name in live_tunnel live; do
  if [[ -f "$name.pid" ]]; then
    pid="$(<"$name.pid")"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      kill -- "-$pid" 2>/dev/null || true
    fi
    rm -f "$name.pid"
  fi
done
