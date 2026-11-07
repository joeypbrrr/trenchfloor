#!/bin/bash
cd "$(dirname "$0")" || exit 1
stop_one() {
  local name="$1"
  if [[ -f "$name.pid" ]]; then
    local pid
    pid="$(cat "$name.pid" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
      sleep 0.4
      kill -9 -- "-$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$name.pid"
  fi
  if [[ -f "$name.child.pid" ]]; then
    local cpid
    cpid="$(cat "$name.child.pid" 2>/dev/null || true)"
    if [[ -n "${cpid}" ]] && kill -0 "$cpid" 2>/dev/null; then
      kill "$cpid" 2>/dev/null || true
      sleep 0.2
      kill -9 "$cpid" 2>/dev/null || true
    fi
    rm -f "$name.child.pid"
  fi
  echo "stopped $name"
}
stop_one pumpportal
stop_one research
stop_one server
